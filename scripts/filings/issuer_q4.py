"""Read the XBRL archives offered in issuers' public investor-facing filing directories."""

from copy import deepcopy
from datetime import date, datetime
from io import BytesIO
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile
import re

from playwright.sync_api import Error as BrowserError, sync_playwright
from lxml import etree
from issuer_filings import issuer_tables


DIRECTORIES = {
    "AAPL": "https://investor.apple.com/sec-filings/default.aspx",
    "GOOGL": "https://abc.xyz/investor/sec-filings/default.aspx",
    "NVDA": "https://investor.nvidia.com/financial-info/sec-filings/default.aspx",
    "MU": "https://investors.micron.com/financials/sec-filings/default.aspx",
    "STX": "https://investors.seagate.com/financials/sec-filings/default.aspx",
    "CSCO": "https://investor.cisco.com/financials/sec-filings/default.aspx",
    "ORCL": "https://investor.oracle.com/sec-filings/default.aspx",
    "META": "https://investor.atmeta.com/financials?section=secfilings",
    "APP": "https://investors.applovin.com/financials/sec-filings/default.aspx",
    "IONQ": "https://investors.ionq.com/financials/sec-filings/default.aspx",
    "V": "https://investor.visa.com/SEC-Filings/default.aspx",
    "MA": "https://investor.mastercard.com/financials-and-sec-filings/sec-filings/default.aspx",
    "STT": "https://investors.statestreet.com/filings-and-reports/sec-filings/default.aspx",
    "PG": "https://www.pginvestor.com/financials/sec-filings/default.aspx",
    "COST": "https://investor.costco.com/financials/sec-filings/default.aspx",
    "NFLX": "https://ir.netflix.net/financials/sec-filings/default.aspx",
    "JNJ": "https://www.investor.jnj.com/financials/sec-filings/default.aspx",
    "MRK": "https://www.merck.com/investor-relations/financial-information/sec-filings/",
    "CAT": "https://investors.caterpillar.com/financials/sec-filings/default.aspx",
    "AMZN": "https://ir.aboutamazon.com/sec-filings/default.aspx",
    "BLK": "https://ir.blackrock.com/financials/sec-filings/default.aspx",
    "CRCL": "https://investor.circle.com/financials/sec-filings/default.aspx",
    "QCOM": "https://investor.qualcomm.com/financial-info-sec-filings/sec-filings/default.aspx",
    "DIS": "https://investors.thewaltdisneycompany.com/financials/sec-filings/default.aspx",
}
CDN = "d18rn0p25nwr6d.cloudfront.net"
HOSTS = {urlsplit(u).hostname for u in DIRECTORIES.values()} | {CDN}
DATE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/(?:\d{4}|\d{2})|[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})\b"
)


def filing_date(text):
    for value in DATE.findall(text):
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(value.replace(",", "").replace(".", ""), fmt).date().isoformat()
            except ValueError:
                pass
    return None


FILING_ROWS = r"""({form, archiveCik}) => {
  const results = [];
  for (const zip of document.querySelectorAll('a[href*=".zip" i]')) {
    const file = zip.pathname.match(/^\/CIK-0*(\d+)\/[\da-z-]+\.zip$/i);
    if (!file || Number(file[1]) !== archiveCik) continue;
    const row = zip.closest('tr,.module_item,.ModuleItem,[role="row"],.evergreen-sec-filings-item,.mco-q4-sec-filings-list-block-list-item');
    if (!row) continue;
    // Issuers sometimes append a screen-reader explanation to the form's node.
    const walker = document.createTreeWalker(row, NodeFilter.SHOW_TEXT), parts = [];
    while (walker.nextNode()) parts.push(walker.currentNode.textContent.trim());
    if (!parts.some(s => s.toUpperCase().replace(/^FORM\s+/, '') === form)) continue;
    const links = Array.from(row.querySelectorAll('a[href]'));
    const detail = links.find(a => a.host === location.host && /filingid=\d+/i.test(a.search));
    const original = links.find(a => a.host === zip.host && a.pathname.toLowerCase().endsWith('.html'));
    results.push({content:parts.join(' '),url:zip.href,detail:(detail||original)?.href||''});
  }
  return results;
}"""


def listing(page, form, host, archive_cik):
    candidates = page.evaluate(FILING_ROWS, {"form": form, "archiveCik": archive_cik})
    found = []
    for item in candidates:
        filed = filing_date(item["content"])
        file_url = urlsplit(item["url"])
        if (
            not filed
            or filed > date.today().isoformat()
            or file_url.scheme != "https"
            or file_url.hostname != CDN
        ):
            continue
        if not re.fullmatch(rf"/CIK-0*{archive_cik}/[a-zA-Z0-9-]+\.zip", file_url.path, re.I):
            continue
        detail = urlsplit(item["detail"])
        direct_html = detail.hostname == CDN and re.fullmatch(
            rf"/CIK-0*{archive_cik}/[a-zA-Z0-9-]+\.html", detail.path, re.I
        )
        cite = (
            item["detail"]
            if (detail.hostname == host or direct_html) and detail.scheme == "https"
            else item["url"]
        )
        found.append((filed, cite, item["url"]))
    return max(found, default=None)


def select_financials(page, form):
    group = "annual" if form == "10-K" else "quarterly"
    for select in page.locator("select:visible").all():
        options = select.locator("option").evaluate_all(
            "opts=>opts.map(o=>({label:o.label.trim(),value:o.value}))"
        )
        for option in options:
            if option["label"].lower() in {group, group + " filings", group + " reports", form.lower()}:
                select.select_option(value=option["value"], timeout=3500)
                for ancestor in ("ancestor::*[contains(@class,'filter')][1]", "ancestor::form[1]"):
                    controls = (
                        select.locator("xpath=" + ancestor)
                        .locator("button.sec-button:visible,button:visible")
                        .filter(has_text=re.compile(r"^\s*(Submit|Apply)\s*$", re.I))
                    )
                    if controls.count() == 1:
                        controls.click(timeout=3500)
                        break
                return


def open_archive(fetch, url):
    with ZipFile(BytesIO(fetch(url))) as z:
        extracted = [
            i for i in z.infolist() if re.fullmatch(r"(?:[^/]+/)*[^/]+_(?:htm|html)\.xml", i.filename, re.I)
        ]
        if len(extracted) != 1 or extracted[0].file_size > 55_000_000:
            raise ValueError("The issuer did not supply a single primary XBRL statement")
        return z.read(extracted[0])


def refresh_q4(report, cik, fetch):
    directory = DIRECTORIES[report["ticker"]]
    host = urlsplit(directory).hostname
    # Merck's own filing directory uses its legacy distribution folder. Always
    # check the reporting entity's actual CIK inside each XBRL instance below.
    archive_cik = 64978 if report["ticker"] == "MRK" else cik
    output = deepcopy(report)
    latest, warnings = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(
                    user_agent="Murmurworld public filings (https://github.com/murmurworld/murmurworld.github.io)"
                )
                page.goto(directory, wait_until="domcontentloaded", timeout=22000)
                page.locator("a[href*='FilingId' i], a[href$='.zip' i]").first.wait_for(
                    state="attached", timeout=10000
                )
                for section, form in (("annual", "10-K"), ("interim", "10-Q")):
                    try:
                        entry = listing(page, form, host, archive_cik)
                        if not entry:
                            select_financials(page, form)
                            page.wait_for_function(
                                "args=>(" + FILING_ROWS + ")(args).length>0",
                                arg={"form": form, "archiveCik": archive_cik},
                                timeout=8500,
                            )
                            entry = listing(page, form, host, archive_cik)
                        if not entry:
                            raise ValueError("Missing " + form + " XBRL download")
                        filed, cite, url = entry
                        src, output[section] = issuer_tables(
                            report, cik, section, form, filed, "", cite, open_archive(fetch, url)
                        )
                        latest.append(src)
                    except (BrowserError, OSError, ValueError, KeyError, BadZipFile, etree.Error) as error:
                        warnings.append(f"{section}-unavailable ({str(error).splitlines()[0][:140]})")
            finally:
                browser.close()
    except BrowserError as error:
        raise ValueError("Issuer filing directory did not load") from error
    if not latest:
        raise ValueError("; ".join(warnings))
    return output, {"latest": latest, "warnings": warnings}
