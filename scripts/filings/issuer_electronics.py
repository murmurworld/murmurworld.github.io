"""Publisher-verified ADI end markets and Palantir government/commercial customer segments."""

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import re
from urllib.parse import urljoin, urlsplit
from zipfile import BadZipFile

from lxml import etree, html
from playwright.sync_api import Error as BrowserError, sync_playwright

from issuer_filings import issuer_tables
from issuer_multiperiod import insist
from issuer_native import financial_table, ti_rows
from issuer_q4 import CDN, open_archive
from issuer_technology import decoded, number, periods


ADI = "https://www.prnewswire.com/news/analog-devices%2C-inc./"
PLTR = "https://investors.palantir.com/financials/sec-filings"
ELECTRONICS_HOSTS = {"www.prnewswire.com", "investors.palantir.com", CDN}
CIKS = {"ADI": 6281, "PLTR": 1321655}
ELECTRONICS_TICKERS = set(CIKS)
ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}
ADI_TITLE = re.compile(
    r"Analog Devices Reports (?:Record )?(?:Fiscal )?(First|Second|Third|Fourth) Quarter"
    r"( and Fiscal(?: Year)?)? (20\d\d) Financial Results",
    re.I,
)
ADI_PATH = re.compile(
    r"/news-releases/analog-devices-reports-(?:record-)?(?:fiscal-)?"
    r"(first|second|third|fourth)-quarter(?:-and-fiscal(?:-year)?)?-(20\d\d)-financial-results-\d+\.html"
)
ADI_MARKETS = {
    "Industrial": "산업용",
    "Automotive": "자동차용",
    "Communications": "통신용",
    "Consumer": "소비자용",
}
ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError, etree.Error, BadZipFile, BrowserError)


def adi_entries(fetch):
    entries = []
    url = ADI
    for page in range(1, 5):
        doc = html.fromstring(decoded(fetch(url)))
        for anchor in doc.xpath("//a[@href]"):
            dest = urljoin(ADI, anchor.get("href"))
            u = urlsplit(dest)
            m = ADI_PATH.fullmatch(u.path)
            if u.scheme != "https" or u.netloc != "www.prnewswire.com" or u.query or u.fragment or not m:
                continue
            txt = " ".join(anchor.text_content().split())
            stamp = re.match(r"([A-Z][a-z]{2} \d{1,2}, \d{4}),", txt)
            if stamp:
                day = datetime.strptime(stamp[1], "%b %d, %Y").date()
                if day <= date.today():
                    entries.append((int(m[2]), ORDINAL[m[1]], day, dest))
        if entries and any(e[1] == 4 for e in entries):
            break
        next_url = ADI + f"?page={page+1}&pagesize=25"
        if not any(urljoin(ADI, a) == next_url for a in doc.xpath("//a/@href")):
            break
        url = next_url
    insist(entries, "ADI published no dated earnings release")
    return {"annual": max((e for e in entries if e[1] == 4), default=None), "interim": max(entries)}


def report_day(label):
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(label.replace(".", ""), fmt).date()
        except ValueError:
            pass
    raise ValueError("Unrecognized ADI financial statement date")


def adi_statement(raw, entry, section):
    year, q, day, url = entry
    doc = html.fromstring(decoded(raw), parser=html.HTMLParser(encoding="utf-8"))
    title = ADI_TITLE.fullmatch(" ".join(doc.xpath("string(//h1)").split()))
    insist(
        title
        and ORDINAL[title[1].lower()] == q
        and int(title[3]) == year
        and bool(title[2]) == (q == 4)
        and doc.xpath(
            "//a[@href=$path and normalize-space(.)='Analog Devices, Inc.']", path=urlsplit(ADI).path
        )
        and doc.xpath('//link[@rel="canonical"]/@href') == [url],
        "ADI company, release or fiscal title mismatch",
    )
    dates = doc.xpath("//meta[@name='date']/@content")
    insist(len(dates) == 1 and datetime.fromisoformat(dates[0]).date() == day, "ADI release date mismatch")
    tables = [[r for r in ti_rows(t) if r] for t in doc.xpath("//table")]
    income_header = [
        "ANALOG DEVICES, INC. CONSOLIDATED STATEMENTS OF INCOME (Unaudited) (In thousands, except per share amounts)"
    ]
    income = [t for t in tables if t and t[0] == income_header]
    months = {1: "Three", 2: "Six", 3: "Nine", 4: "Twelve"}
    heads = ["Three Months Ended"] + ([months[q] + " Months Ended"] if q > 1 else [])
    insist(len(income) == 1 and income[0][1] == heads, "ADI GAAP statement columns or units changed")
    cols = income[0][2]
    bounds = [report_day(v) for v in cols]
    insist(
        len(bounds) == 2 * len(heads)
        and bounds == bounds[:2] * len(heads)
        and 350 <= (bounds[0] - bounds[1]).days <= 375
        and bounds[0] < day,
        "ADI financial periods inconsistent",
    )
    # Fiscal Q1 can end in January or early February. Q4 ends near late October.
    insist(
        bounds[0].year == year and bounds[0].month in {1: [1, 2], 2: [4, 5], 3: [7, 8], 4: [10, 11]}[q],
        "ADI fiscal calendar mismatch",
    )
    grids = [
        t for t in tables if t and t[0] == ["Three Months Ended"] and any(r[0] == "Industrial" for r in t)
    ]
    insist(len(grids) == 1, "ADI end-market detail missing")
    grid = grids[0]
    headings = [(i, r[0]) for i, r in enumerate(grid) if len(r) == 1 and r[0].endswith("Months Ended")]
    insist([r for _, r in headings] == heads, "ADI end-market periods changed")
    source = {
        "url": url,
        "periodEnd": bounds[0].isoformat(),
        "published": day.isoformat(),
        "label": "ADI 실적 발표",
        "labelEn": "ADI earnings release",
    }
    annual = section == "annual"
    insist(not annual or q == 4, "ADI annual figures require Q4")
    blocks = [1] if annual else ([0, 1] if q in {2, 3} else [0])
    result = []
    for block in blocks:
        i = headings[block][0]
        part = grid[i : headings[block + 1][0] if block + 1 < len(headings) else len(grid)]
        insist([report_day(v) for v in part[1]] == bounds[:2], "ADI market and GAAP dates differ")
        normalize = lambda s: re.sub(r"[\s*1]", "", s.lower())
        insist(
            [normalize(v) for v in part[2]] == ["revenue", "%ofrevenue", "y/y%", "revenue", "%ofrevenue"],
            "ADI market amount and percentage columns changed",
        )
        values = {}
        for row in part[3:]:
            if row[0] not in {*ADI_MARKETS, "Total revenue"}:
                continue
            insist(
                len(row) == 6 and row[0] not in values and all("%" in row[j] for j in [2, 3, 5]),
                "ADI market data changed",
            )
            values[row[0]] = [number(row[4]), number(row[1])]
        insist(set(values) == {*ADI_MARKETS, "Total revenue"}, "Missing ADI end market")
        fiscal = [bounds[1], bounds[0]]
        period_list = periods(fiscal, annual)
        interval = (
            ("연간", "Annual", "annual")
            if annual
            else (
                (f"{q*3}개월 누계", f"{months[q]} months", "ytd")
                if block
                else ("3개월", "Quarterly", "quarter")
            )
        )
        if block and not annual:
            for obj, end in zip(period_list, fiscal):
                obj.update(
                    label=end.strftime("%Y.%m") + " · " + interval[0],
                    labelEn=end.strftime("%Y.%m") + " · " + interval[1],
                )
        metrics = []
        for key, ko, en, name in [
            ("sales", "매출", "Revenue", "Revenue"),
            ("gross", "매출총이익", "Gross profit", "Gross margin"),
            ("op", "영업이익", "Operating income", "Operating income"),
            ("net", "순이익", "Net income", "Net income"),
        ]:
            rows = [r for r in income[0][3:] if r[0] == name]
            insist(
                len(rows) == 1 and len(rows[0]) == 1 + len(bounds), "Incomplete or duplicate ADI GAAP measure"
            )
            metrics.append(((key, ko, en), [number(rows[0][2 + 2 * block]), number(rows[0][1 + 2 * block])]))
        total = values["Total revenue"]
        insist(
            total == metrics[0][1] == [sum(values[n][i] for n in ADI_MARKETS) for i in range(2)],
            "ADI total and end-market revenue do not reconcile",
        )
        markets = financial_table(
            "adi-end-markets-" + interval[2],
            ("최종 시장별 매출 · " + interval[0], interval[1] + " revenue by end market"),
            period_list,
            source,
            [((key.lower(), korean, key), values[key]) for key, korean in ADI_MARKETS.items()],
        )
        markets.update(
            measure="revenue",
            total=total,
            compositionKeys=[k.lower() for k in ADI_MARKETS],
            compositionPeriods=[v["label"] for v in period_list],
        )
        profit = financial_table(
            "adi-gaap-" + interval[2],
            ("연결 손익 · " + interval[0], interval[1] + " consolidated GAAP results"),
            period_list,
            source,
            metrics,
        )
        for t in [markets, profit]:
            t.update(unitKo="천 달러", unitEn="USD thousand")
        result.extend([markets, profit])
    return {**source, "kind": section}, result


def filing_entries(raw, form):
    doc = html.fromstring(raw)
    valid = []
    for row in doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," file-container ")]'):
        forms = row.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," file-type ")]')
        if [" ".join(e.text_content().split()) for e in forms] != [form]:
            continue
        stamps = row.xpath('.//*[contains(@class,"date")]/text()')
        if len(stamps) != 1:
            continue
        fdate = datetime.strptime(stamps[0].replace(" ", ""), "%m/%d/%y").date()
        if fdate > date.today():
            continue
        links = {}
        for kind, suffix in (("XBRL", "zip"), ("XBRL_HTML", "html")):
            ls = row.xpath(".//a[normalize-space(.)=$k]/@href", k=kind)
            if len(ls) != 1:
                continue
            u = urlsplit(ls[0])
            if (
                u.netloc == CDN
                and u.scheme == "https"
                and not u.query
                and not u.fragment
                and re.fullmatch(r"/CIK-0*1321655/[a-f0-9-]+\." + suffix, u.path, re.I)
            ):
                links[kind] = ls[0]
        if len(links) == 2:
            valid.append((fdate.isoformat(), links["XBRL_HTML"], links["XBRL"]))
    return max(valid, default=None)


def pltr_directory():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(
                user_agent="Murmurworld public filings (https://github.com/murmurworld/murmurworld.github.io)"
            )
            response = page.goto(PLTR, wait_until="domcontentloaded", timeout=25000)
            insist(response and response.ok, "Palantir's IR directory is unavailable")
            selectors = page.locator("main select")
            selectors.nth(1).wait_for(state="visible", timeout=14000)
            years = sorted(
                [
                    v
                    for v in selectors.first.locator("option").all_text_contents()
                    if re.fullmatch(r"20\d\d", v)
                ],
                reverse=True,
            )[:2]
            insist(
                years and selectors.nth(1).locator("option[value='10-Q']").count() == 1,
                "Palantir filing filters changed",
            )
            entries = {}
            for section, form in [("annual", "10-K"), ("interim", "10-Q")]:
                for year in years:
                    selectors.first.select_option(label=year)
                    selectors.nth(1).select_option(value=form)
                    try:
                        page.wait_for_function(
                            """({f,y})=>[...document.querySelectorAll('.file-container')].some(r=>
                          r.querySelector('.file-type')?.textContent.trim()===f &&
                          r.querySelector('[class*=date]')?.textContent.trim().endsWith(y.slice(-2)))""",
                            arg={"f": form, "y": year},
                            timeout=6500,
                        )
                    except BrowserError:
                        continue
                    entry = filing_entries(page.content(), form)
                    if entry and entry[0][:4] == year:
                        entries[section] = entry
                        break
            return entries
        finally:
            browser.close()


def pltr_market_tables(raw, tables, source):
    """Only issuer-wide operating-segment contexts; never add geography or contract-type dimensions."""
    doc = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True))
    ns = {"x": "http://www.xbrl.org/2003/instance", "d": "http://xbrl.org/2006/xbrldi"}
    units = set()
    for u in doc.xpath("./x:unit", namespaces=ns):
        if len(u) != 1 or u[0].tag != "{" + ns["x"] + "}measure":
            continue
        prefix, _, currency = (u[0].text or "").partition(":")
        if currency == "USD" and u[0].nsmap.get(prefix) == "http://www.xbrl.org/2003/iso4217":
            units.add(u.get("id"))
    contexts = {}
    member_names = {
        "pltr:GovernmentOperatingSegmentMember": "government",
        "pltr:CommercialMember": "commercial",
    }
    for c in doc.xpath("./x:context", namespaces=ns):
        if c.xpath("string(./x:entity/x:identifier)", namespaces=ns).lstrip("0") != "1321655" or c.xpath(
            ".//d:typedMember", namespaces=ns
        ):
            continue
        axes = c.xpath(".//d:explicitMember", namespaces=ns)
        pairs = {m.get("dimension"): m.text for m in axes}
        if len(axes) != 2 or pairs.get("srt:ConsolidationItemsAxis") != "us-gaap:OperatingSegmentsMember":
            continue
        name = member_names.get(pairs.get("us-gaap:StatementBusinessSegmentsAxis"))
        if not name:
            continue
        start = c.xpath("string(./x:period/x:startDate)", namespaces=ns)
        end = c.xpath("string(./x:period/x:endDate)", namespaces=ns)
        if start and end:
            contexts[c.get("id")] = (name, start, end)
    figures = {}
    for fact in doc.xpath('./*[local-name()="RevenueFromContractWithCustomerExcludingAssessedTax"]'):
        key = contexts.get(fact.get("contextRef"))
        if (
            not key
            or fact.get("unitRef") not in units
            or not re.fullmatch(
                r"https?://(?:fasb.org|xbrl.us)/us-gaap/[^/]+", etree.QName(fact).namespace or ""
            )
        ):
            continue
        if not re.fullmatch(r"-?\d+(?:\.\d+)?", fact.text or ""):
            continue
        figures.setdefault(key, set()).add(Decimal(fact.text) / Decimal(1_000_000))
    answer = []
    for t in tables:
        if not t["id"].startswith("sec-consolidated-") or t["source"]["url"] != source["url"]:
            continue
        consolidated = next(
            (
                r
                for r in t["rows"]
                if r["key"] == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
            ),
            None,
        )
        if not consolidated or len(t["periods"]) < 2:
            continue
        market = []
        for key, ko, en in [
            ("government", "정부 고객", "Government"),
            ("commercial", "민간 고객", "Commercial"),
        ]:
            values = [figures.get((key, p["start"], p["end"]), set()) for p in t["periods"]]
            if any(len(v) != 1 for v in values):
                break
            market.append(((key, ko, en), [float(next(iter(v))) for v in values]))
        if len(market) != 2:
            continue
        actual = [Decimal(str(i)) if i is not None else None for i in consolidated["values"]]
        insist(
            all(
                Decimal(str(a)) + Decimal(str(b)) == c for a, b, c in zip(market[0][1], market[1][1], actual)
            ),
            "Palantir segment revenue does not match its consolidated statement",
        )
        interval = t["id"].removeprefix("sec-consolidated-")
        ko, en = {
            "annual": ("연간", "Annual"),
            "quarter": ("분기", "Quarterly"),
            "half": ("6개월 누계", "Six-month"),
            "nine-months": ("9개월 누계", "Nine-month"),
        }[interval]
        result = financial_table(
            "pltr-customer-segments-" + interval,
            ("정부·민간 고객 매출 · " + ko, en + " government and commercial revenue"),
            t["periods"],
            t["source"],
            market,
        )
        result.update(
            measure="revenue",
            total=consolidated["values"],
            compositionKeys=["government", "commercial"],
            compositionPeriods=[p["label"] for p in t["periods"]],
        )
        answer.append(result)
    return answer


def refresh_electronics(report, cik, fetch):
    ticker = report["ticker"]
    insist(CIKS.get(ticker) == int(cik), "Unexpected issuer CIK")
    entries = adi_entries(fetch) if ticker == "ADI" else pltr_directory()
    result = deepcopy(report)
    latest = []
    warnings = []
    cache = {}
    for section, form in [("annual", "10-K"), ("interim", "10-Q")]:
        try:
            entry = entries.get(section)
            insist(entry, "Missing issuer publication for this period")
            if ticker == "ADI":
                url = entry[-1]
                if url not in cache:
                    cache[url] = fetch(url)
                source, tables = adi_statement(cache[url], entry, section)
            else:
                filed, cite, file_url = entry
                raw = open_archive(fetch, file_url)
                source, verified = issuer_tables(report, cik, section, form, filed, "", cite, raw)
                new = [t for t in verified if t["source"]["url"] == cite and t["id"].startswith("sec-")]
                market = pltr_market_tables(raw, new, source)
                if not market:
                    warnings.append(section + "-segment-unavailable")
                tables = market + new
            end = source["periodEnd"]
            previous = report[section]
            insist(
                end >= max((p.get("end") or "" for t in previous for p in t["periods"]), default=""),
                "Issuer statement predates verified reporting periods",
            )
            verify_date = source.get("filed") or source["published"]
            insist(
                not any(
                    t["source"].get("periodEnd") == end
                    and (t["source"].get("filed") or t["source"].get("published") or "") > verify_date
                    for t in previous
                ),
                "Issuer statement predates same-period revision",
            )
            ids = {t["id"] for t in tables}
            result[section] = tables + [t for t in previous if t["id"] not in ids]
            latest.append(source)
        except ERRORS as exc:
            warnings.append(section + "-unavailable (" + str(exc).splitlines()[0][:140] + ")")
    if not latest:
        raise ValueError("; ".join(warnings))
    return result, {"latest": latest, "warnings": warnings}
