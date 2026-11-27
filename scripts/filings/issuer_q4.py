"""Read the XBRL archives offered in issuers' public investor-facing filing directories."""

from copy import deepcopy
from datetime import date, datetime
from io import BytesIO
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile
import re
import time

from playwright.sync_api import Error as BrowserError, sync_playwright
from lxml import etree
from issuer_filings import issuer_tables
from issuer_multiperiod import META_CDN, fourth_quarter, merck_annual, meta_quarter, pdf_pages
from pypdf.errors import PdfReadError


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
HOSTS = {urlsplit(u).hostname for u in DIRECTORIES.values()} | {CDN, META_CDN}
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
    group = {"10-K": "annual", "10-Q": "quarterly", "8-K": "current"}[form]
    for select in page.locator("select:visible").all():
        options = select.locator("option").evaluate_all(
            "opts=>opts.map(o=>({label:o.label.trim(),value:o.value}))"
        )
        for option in options:
            if option["label"].lower() in {
                group,
                group + " filings",
                group + " reports",
                group + " report",
                form.lower(),
            }:
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


def meta_latest(page, fetch):
    rows = page.locator(".Quarter").evaluate_all(
        """nodes=>nodes.map(node=>({
      year:node.querySelector('.year')?.textContent.trim(), q:node.querySelector('.title')?.textContent.trim(),
      link:[...node.querySelectorAll('a[href]')].find(a=>a.textContent.trim()==='Earnings Release')?.href
    }))"""
    )
    entries = {
        (int(r["year"]), int(r["q"][0]), r.get("link") or "")
        for r in rows
        if re.fullmatch(r"20\d\d", r.get("year") or "") and re.fullmatch(r"[1-4]Q", r.get("q") or "")
    }
    if not entries:
        raise ValueError("Meta quarterly archive is empty")
    year, q, url = max(entries)
    p = urlsplit(url)
    if (
        p.scheme != "https"
        or p.hostname != META_CDN
        or not re.fullmatch(r"/399680738/files/[^?#]+\.pdf", p.path, re.I)
    ):
        raise ValueError("Meta did not publish a directly identifiable latest quarterly statement")
    return meta_quarter(pdf_pages(fetch(url)), year, q, url)


CURRENT_REPORTS = r"""()=>Array.from(document.querySelectorAll('a[href]')).flatMap(a=>{
  if(!/\.pdf$/i.test(a.pathname)) return [];
  const row=a.closest('tr,.module_item,.ModuleItem,[role="row"],.evergreen-sec-filings-item');
  if(!row)return [];
  const nodes=document.createTreeWalker(row,NodeFilter.SHOW_TEXT), parts=[];
  while(nodes.nextNode())parts.push(nodes.currentNode.textContent.trim());
  if(!parts.some(s=>s.toUpperCase().replace(/^FORM\s+/,'')==='8-K'))return [];
  return [{url:a.href,date:parts.join(' ')}];
})"""


def year_end_release(page, ticker, cik, annual, fetch):
    select_financials(page, "8-K")
    expected = date.fromisoformat(annual["periodEnd"])
    until = annual["filed"]
    eligible = []

    def scan():
        for row in page.evaluate(CURRENT_REPORTS):
            filed = filing_date(row["date"])
            url = urlsplit(row["url"])
            if (
                filed
                and annual["periodEnd"] < filed <= until
                and url.scheme == "https"
                and url.hostname == CDN
                and re.fullmatch(rf"/CIK-0*{cik}/[\da-f-]+\.pdf", url.path, re.I)
            ):
                eligible.append((filed, row["url"]))

    # A prior filter may still have other 8-K rows while the new list loads.
    # Wait for the expected fiscal year instead of accepting those stale rows.
    deadline = time.monotonic() + 7
    while not eligible:
        scan()
        if eligible or time.monotonic() >= deadline:
            break
        page.wait_for_timeout(250)
    for filed, url in sorted(set(eligible), reverse=True)[:8]:
        try:
            return fourth_quarter(ticker, pdf_pages(fetch(url)), filed, url, expected)
        except (ValueError, PdfReadError):
            continue
    raise ValueError("No current 8-K earnings exhibit for the verified fiscal year end")


def add_period_releases(page, report, output, latest, warnings, cik, fetch):
    ticker = report["ticker"]
    if ticker not in {"COST", "MU", "META", "MRK"}:
        return
    by_kind = {src["kind"]: src for src in latest}
    section = "annual" if ticker == "MRK" else "interim"
    if ticker in {"COST", "MU"}:
        annual = by_kind.get("annual")
        if not annual or by_kind.get("interim", {}).get("periodEnd", "") >= annual["periodEnd"]:
            return
    elif section in by_kind:
        return
    try:
        if ticker == "MRK" and cik == 310158:
            source, tables = merck_annual(fetch)
        elif ticker == "META" and cik == 1326801:
            source, tables = meta_latest(page, fetch)
        elif (ticker, cik) in {("COST", 909832), ("MU", 723125)}:
            source, tables = year_end_release(page, ticker, cik, annual, fetch)
        else:
            raise ValueError("Unexpected earnings-release CIK")
        last = max((p.get("end") or "" for t in output[section] for p in t["periods"]), default="")
        if source["periodEnd"] < last:
            raise ValueError("Issuer release predates stored reporting period")
        ids = {t["id"] for t in tables}
        output[section] = tables + [t for t in output[section] if t["id"] not in ids]
        latest[:] = [s for s in latest if s["kind"] != section] + [source]
        warnings[:] = [w for w in warnings if not w.startswith(section + "-unavailable")]
    except (
        BrowserError,
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        etree.Error,
        PdfReadError,
    ) as error:
        if not any(w.startswith(section + "-unavailable") for w in warnings):
            warnings.append(f"{section}-release-unavailable ({str(error).splitlines()[0][:140]})")


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
                add_period_releases(page,report,output,latest,warnings,cik,fetch)
            finally:
                browser.close()
    except BrowserError as error:
        raise ValueError("Issuer filing directory did not load") from error
    if not latest:
        raise ValueError("; ".join(warnings))
    return output, {"latest": latest, "warnings": warnings}
