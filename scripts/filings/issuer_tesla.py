"""Read Tesla's investor-linked SEC quarterly filing and preserve the earlier tables."""

from calendar import monthrange
from copy import deepcopy
from datetime import datetime
import re
from urllib.parse import urlsplit

from lxml import html

from issuer_filings import issuer_tables
from public_company_sec import REVENUES, iso


HOST = "ir.tesla.com"
INDEX = "https://" + HOST + "/"
CIK = 1318605
DOCUMENT = re.compile(r"/Archives/edgar/data/1318605/(\d{18})/tsla-(\d{8})\.htm")
REVENUE_KEYS = {f"{taxonomy}:{tag}" for taxonomy, tag, *_ in REVENUES}


def discover(raw):
    """Select the newest original Tesla 10-Q linked from its quarterly results."""
    links = set()
    for link in html.fromstring(raw).xpath("//tr//a[normalize-space(.)='10-Q']/@href"):
        parts = urlsplit(link)
        match = DOCUMENT.fullmatch(parts.path)
        if parts.scheme != "https" or parts.netloc != "www.sec.gov" or parts.query or parts.fragment or not match:
            continue
        digits, key = match.groups()
        try:
            period = datetime.strptime(key, "%Y%m%d").date()
        except ValueError:
            continue
        if period.month in (3, 6, 9) and period.day == monthrange(period.year, period.month)[1]:
            links.add((period, digits, link))
    if not links:
        raise ValueError("Tesla IR has no direct quarterly SEC filing")
    newest = max(link[0] for link in links)
    candidates = [link for link in links if link[0] == newest]
    if len(candidates) != 1:
        raise ValueError("Tesla IR links conflicting filings for one quarter")
    return candidates[0]


def filing_date(raw, period):
    doc = html.fromstring(raw)
    values = {
        label: [
            " ".join(node.text_content().split())
            for node in doc.xpath(
                "//div[@class='infoHead' and normalize-space(.)=$label]/following-sibling::div[1]", label=label
            )
        ]
        for label in ("Filing Date", "Period of Report")
    }
    dates = values["Filing Date"]
    filed = iso(dates[0]) if len(dates) == 1 else None
    if values["Period of Report"] != [period.isoformat()] or not filed or filed < period:
        raise ValueError("Tesla SEC filing date or reporting period is missing or inconsistent")
    return filed.isoformat()


def refresh_tesla(report, cik, fetch):
    if report["ticker"] != "TSLA" or cik != CIK:
        raise ValueError("Unexpected Tesla issuer identity")
    period, digits, url = discover(fetch(INDEX))
    accession = f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"
    index_url = f"{url.rsplit('/', 1)[0]}/{accession}-index.htm"
    filed = filing_date(fetch(index_url), period)
    packet = deepcopy(report)
    source, tables = issuer_tables(packet, cik, "interim", "10-Q", filed, accession, url, fetch(url))
    required = {"sec-consolidated-quarter"}
    cumulative = {6: "half", 9: "nine-months"}.get(period.month)
    if cumulative:
        required.add(f"sec-consolidated-{cumulative}")
    available = {
        table["id"]
        for table in tables
        if table["source"]["url"] == url
        and len(table["periods"]) == 2
        and any(row["key"] in REVENUE_KEYS and None not in row["values"] for row in table["rows"])
    }
    if source["periodEnd"] != period.isoformat() or not required <= available:
        raise ValueError("Tesla SEC filing has no complete comparable quarter and cumulative revenue")
    packet["interim"] = tables
    return packet, {"latest": [source], "warnings": []}
