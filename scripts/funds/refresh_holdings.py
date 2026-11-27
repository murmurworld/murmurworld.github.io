"""Refresh full, dated equity holdings from each ETF's public issuer disclosure."""

import argparse
import json
import math
import os
import re
import ssl
import tempfile
from datetime import date, datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from lxml import etree, html


ROOT = Path(__file__).resolve().parents[2]
VOO = "https://investor.vanguard.com/vmf/api/VOO/portfolio-holding/stock"
VOO_PAGE = "https://investor.vanguard.com/investment-products/etfs/profile/voo#portfolio-composition"
QQQM = "https://dng-api.invesco.com/cache/v1/accounts/en_US/shareclasses/46138G649/holdings/fund?idType=cusip&productType=ETF"
QQQM_PAGE = "https://www.invesco.com/us/en/financial-products/etfs/invesco-nasdaq-100-etf.html"
SCHD = "https://www.schwabassetmanagement.com/allholdings/schd"
HOSTS = {urlsplit(url).hostname for url in (VOO, QQQM, SCHD)}
MINIMUM_EQUITIES = {"VOO": 400, "QQQM": 75, "SCHD": 75}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def safe_url(url):
    dest = urlsplit(url)
    require(dest.scheme == "https" and dest.hostname in HOSTS and not dest.username
            and not dest.password and dest.port in (None, 443), "Unexpected ETF holdings host")


class IssuerRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def make_reader():
    context = ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(cafile=certifi.where())
    except ImportError:
        pass
    opener = build_opener(IssuerRedirects(), HTTPSHandler(context=context))

    def fetch(url):
        safe_url(url)
        request = Request(url, headers={"User-Agent": "Murmurworld fund holdings (https://github.com/murmurworld/murmurworld.github.io)",
                                        "Accept-Encoding": "identity"})
        with opener.open(request, timeout=35) as response:
            body = response.read(8_000_001)
        require(0 < len(body) <= 8_000_000, "Empty or oversized disclosure")
        return body
    return fetch


def number(value):
    result = float(value)
    require(math.isfinite(result), "Non-finite holding amount")
    return result


def stock(symbol, name, weight):
    symbol = str(symbol or "").strip().upper().replace(" ", ".")
    require(re.fullmatch(r"[A-Z0-9]+([./-][A-Z0-9]+)*", symbol) and name, "Missing equity identity")
    weight = number(weight)
    require(0 <= weight < 100, "Invalid equity weight")
    return {"ticker": symbol, "name": unescape(name).strip(), "weight": weight}


def complete_fund(ticker, as_of, source, data_source, reported_count, holdings):
    require(date.fromisoformat(as_of).isoformat() == as_of, "Invalid portfolio date")
    require(len(holdings) == len({x["ticker"] for x in holdings}), "Duplicate equity ticker")
    require(MINIMUM_EQUITIES[ticker] <= len(holdings) <= reported_count, "Incomplete equity disclosure")
    require(90 <= sum(x["weight"] for x in holdings) <= 102, "Equity weights do not cover the portfolio")
    require(all(left["weight"] >= right["weight"] for left, right in zip(holdings, holdings[1:])),
            "Equity ranking is not ordered")
    return {"ticker": ticker, "asOf": as_of, "source": source, "holdings": holdings,
            "coverage": {"complete": True, "disclosedPositions": reported_count,
                         "equityPositions": len(holdings), "sourceUrl": data_source}}


def vanguard(fetch):
    url = VOO
    start = 1
    rows = []
    as_of, size = None, None
    while True:
        page = json.loads(fetch(url))
        if start == 1:
            as_of, size = page["asOfDate"], page["size"]
            require(isinstance(size, int) and 400 <= size < 2500, "Invalid VOO security count")
        require(page["asOfDate"] == as_of and page["size"] == size, "VOO dates or totals differ across pages")
        part = page["fund"]["entity"]
        require(part and all(x["asOfDate"] == as_of and x["type"] == "portfolioHolding" and x["cusip"] for x in part),
                "VOO holdings mix dates or omit identifiers")
        rows.extend(part)
        require(len(rows) <= size, "Too many VOO rows")
        if not page.get("next"):
            break
        next_link = urlsplit(page["next"]["href"])
        query = parse_qs(next_link.query, strict_parsing=True)
        start = len(rows) + 1
        require(next_link.hostname == "api.vanguard.com" and next_link.path.endswith("/fund/VOO/portfolio-holding/stock")
                and set(query) == {"start", "count"} and query["start"] == [str(start)]
                and len(query["count"]) == 1 and 1 <= int(query["count"][0]) <= 1000 and start <= size,
                "Invalid VOO continuation")
        url = VOO + "?" + urlencode({"start": start, "count": int(query["count"][0])})
    require(len(rows) == size == len({r["cusip"] for r in rows}), "Incomplete or duplicated VOO pages")
    rows.sort(key=lambda r: (-number(r["percentWeight"]), -number(r["marketValue"])))
    return complete_fund("VOO", as_of[:10], VOO_PAGE, VOO, size,
                         [stock(r["ticker"], r["longName"], r["percentWeight"]) for r in rows])


def invesco(fetch):
    page = json.loads(fetch(QQQM))
    require(page["cusip"] == "46138G649", "Wrong Invesco share class")
    rows = page["holdings"]
    require(len(rows) == page["totalNumberOfHoldings"], "Incomplete QQQM holdings")
    equity = {"COM", "ADR", "DRNY"}
    other = {"CURR", "IFUT", "MMT", "CURRCOL", "UCURR", "SYN"}
    require(all(r["securityTypeCode"] in equity | other for r in rows), "Unclassified QQQM instrument type")
    equities = [r for r in rows if r["securityTypeCode"] in equity]
    require(all(r["cusip"] for r in equities) and len(equities) == len({r["cusip"] for r in equities}),
            "QQQM equity identifiers missing or duplicated")
    equities.sort(key=lambda r: (-number(r["percentageOfTotalNetAssets"]), -number(r["marketValueBase"])))
    return complete_fund("QQQM", page["effectiveBusinessDate"], QQQM_PAGE, QQQM, len(rows),
                         [stock(r["ticker"], r["issuerName"], r["percentageOfTotalNetAssets"]) for r in equities])


def text(node):
    return " ".join(" ".join(node.itertext()).split())


def schwab(fetch):
    page_no = 0
    securities = []
    as_of, total = None, None
    headers = ["Fund Name", "CUSIP", "Symbol", "Quantity", "% of Assets", "Market Value"]
    while True:
        url = SCHD if not page_no else f"{SCHD}?page={page_no}"
        doc = html.fromstring(fetch(url))
        require(any("Schwab U.S. Dividend Equity ETF (SCHD)" in text(h) for h in doc.xpath("//h1")),
                "Wrong Schwab fund")
        counts = re.search(r"As of\s+(\d\d?/\d\d?/\d{2,4})\s+Displaying\s+([\d,]+)\s*[-–]\s*([\d,]+)\s+of\s+([\d,]+)", text(doc))
        require(counts, "Missing SCHD dated holdings range")
        stamp, first, last, count = counts.groups()
        start, end, count = (int(x.replace(",", "")) for x in (first, last, count))
        day = datetime.strptime(stamp, "%m/%d/%Y" if len(stamp.split("/")[-1]) == 4 else "%m/%d/%y").date().isoformat()
        if not page_no:
            as_of, total = day, count
        require(day == as_of and count == total and 75 <= total <= 500 and start == len(securities) + 1
                and start <= end <= total, "Inconsistent or incomplete SCHD pagination")
        tables = [table for table in doc.xpath("//table")
                  if [text(c) for c in table.xpath(".//tr[th][1]/th")] == headers]
        require(len(tables) == 1, "SCHD table headings changed")
        part = [[text(cell) for cell in row.xpath("./td")] for row in tables[0].xpath(".//tr[td]")]
        require(len(part) == end - start + 1 and all(len(row) == len(headers) for row in part),
                "Incomplete SCHD page")
        securities.extend(part)
        if len(securities) == total:
            break
        page_no += 1
        require(any(urljoin(url, href) == f"{SCHD}?page={page_no}" for href in doc.xpath("//a/@href")),
                "Missing SCHD next page")
    require(all(r[1] for r in securities) and len(securities) == len({r[1] for r in securities}),
            "Missing or duplicated SCHD security")
    holdings = []
    for name, cusip, ticker, _, share, _ in securities:
        if (ticker == "GVMXX" or re.search(r"\b(?:E-?MINI|FUTURE[S]?|E-CBOT)\b", name, re.I)
                or name.upper() in {"US DOLLAR", "U.S. DOLLAR", "CASH", "CASH & EQUIVALENTS"}):
            continue
        require(re.fullmatch(r"[A-Z0-9]{9}", cusip) and not re.search(r"\b(?:COLLATERAL|TREASURY BILL|MONEY MARKET)\b", name, re.I)
                and re.fullmatch(r"\d+(?:\.\d+)?%", share), "Unclassified SCHD holding")
        holdings.append(stock(ticker, name, share[:-1]))
    holdings.sort(key=lambda row: -row["weight"])
    return complete_fund("SCHD", as_of, SCHD, SCHD, total, holdings)


PROVIDERS = {"VOO": vanguard, "QQQM": invesco, "SCHD": schwab}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=path.name + ".", delete=False) as out:
        temp = Path(out.name)
        try:
            json.dump(data, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write("\n")
        except BaseException:
            out.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def archive(directory, packet):
    path = directory / packet["ticker"] / (packet["asOf"] + ".json")
    if path.is_file():
        require(json.loads(path.read_text(encoding="utf-8")) == packet, "Archived snapshot mismatch")
    else:
        write_json(path, packet)


def refresh(destination, fetch, today, providers=PROVIDERS):
    previous = json.loads(destination.read_text(encoding="utf-8"))
    require([p["ticker"] for p in previous] == list(PROVIDERS), "Missing holdings baseline")
    archive_dir = destination.with_name("etf-holdings-history")
    reports = []
    summary = []
    for old in previous:
        ticker = old["ticker"]
        coverage = old["coverage"]
        require(coverage["complete"] is True and coverage["equityPositions"] == len(old["holdings"]),
                "Unverified holdings baseline")
        archive(archive_dir, old)
        packet = old
        try:
            candidate = providers[ticker](fetch)
            age = (today - date.fromisoformat(candidate["asOf"])).days
            require(0 <= age <= 62, "Issuer snapshot is stale or future-dated")
            require(candidate["asOf"] >= old["asOf"], "Issuer snapshot predates stored snapshot")
            if candidate["asOf"] == old["asOf"]:
                require(candidate["holdings"] == old["holdings"], "Same-date revision requires review")
                status = "verified"
            else:
                archive(archive_dir, candidate)
                packet = candidate
                status = "updated"
        except (ValueError, KeyError, IndexError, TypeError, URLError, OSError, etree.ParserError) as error:
            status = f"retained ({str(error).splitlines()[0][:160]})"
        reports.append(packet)
        summary.append(f"{ticker}: {status} · {packet['asOf']} · {len(packet['holdings'])} equity positions")
    if reports != previous:
        write_json(destination, reports)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "public/data/etf-holdings.json")
    args = parser.parse_args()
    summary = refresh(args.data, make_reader(), datetime.now(timezone.utc).date())
    for line in summary:
        print(line)
        if os.environ.get("GITHUB_ACTIONS") and ": retained" in line:
            print(f"::warning::{line}")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write("### ETF holdings\n\n" + "\n".join("- " + line for line in summary) + "\n")


if __name__ == "__main__":
    main()
