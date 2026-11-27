"""Read a company's own financial disclosures when its regulatory feed is unavailable."""
import re
from calendar import month_name, monthrange
from copy import deepcopy
from datetime import date, datetime
from urllib.parse import urljoin, urlsplit

from lxml import etree, html

NATIVE_HOSTS = {"www.ti.com", "www.microsoft.com"}
NATIVE_TICKERS = {"TXN", "MSFT"}
# texas instruments' public robots.txt -> sitemapindex-standard -> english CMS -> other pages
TI_INDEX = "https://www.ti.com/sitemap-cms-other-en-standard.xml"
QUARTERS = {"first":1, "second":2, "third":3, "fourth":4}
RELEASE = re.compile(
    r"/en-us/about-ti/newsroom/news-releases/(\d{4})/(\d{4}-\d\d-\d\d)-"
    r"ti-reports-(?:(first|second|third|fourth)-quarter|q([1-4]))-(\d{4})"
    r"(?:-and-(\d{4}))?-financial-results(?:-and-shareholder-returns)?$")
AMOUNT = re.compile(r"\(?-?(?:\d+|\d{1,3}(?:,\d{3})+)\)?$")
SEGMENTS = {"Analog:": ("analog","아날로그","Analog"),
            "Embedded Processing:": ("embedded","임베디드 프로세싱","Embedded Processing"),
            "Other:": ("other","기타","Other")}
METRICS = {"Revenue": ("sales","매출","Revenue"), "Gross profit": ("gross","매출총이익","Gross profit"),
           "Operating profit": ("operating","영업이익","Operating profit"), "Net income": ("net","순이익","Net income")}


def ti_listing(data):
    parser=etree.XMLParser(resolve_entities=False,load_dtd=False,no_network=True)
    tree=etree.fromstring(data,parser)
    ns="{http://www.sitemaps.org/schemas/sitemap/0.9}" if tree.tag.startswith("{") else ""
    if tree.tag!=ns+"urlset" or tree.getroottree().docinfo.internalDTD is not None:
        raise ValueError("TI newsroom sitemap format changed")
    result=[]
    for loc in tree.iter(ns+"loc"):
        url=loc.text or ""
        parts=urlsplit(url)
        if parts.scheme!="https" or parts.netloc!="www.ti.com" or parts.query or parts.fragment:continue
        m=RELEASE.fullmatch(parts.path)
        if not m:continue
        path_year, day, ordinal, qnum, year, annual_year=m.groups()
        q=QUARTERS[ordinal] if ordinal else int(qnum)
        if path_year!=day[:4] or (annual_year and (q!=4 or annual_year!=year)):continue
        result.append((int(year),q,date.fromisoformat(day),url))
    if not result:raise ValueError("No public TI earnings release in the official sitemap")
    return result


def ti_rows(table):
    rows=[]
    for tr in table.xpath("./thead/tr|./tbody/tr|./tr"):
        cells=[" ".join(" ".join(td.itertext()).split()) for td in tr.xpath("./td|./th")]
        rows.append([s for s in cells if s and s!="$"])
    return rows


def amount(cell):
    if not AMOUNT.fullmatch(cell) or cell.startswith("(")!=cell.endswith(")") or cell.startswith("(-"):
        raise ValueError("Financial statement has an unrecognized amount")
    return int(cell.replace(",","").replace("(","-").replace(")",""))


def ti_periods(year,q,annual):
    month=3*q
    return [dict(label=f"{y}.{month:02d}",labelEn=f"{y}.{month:02d}",
                 start=date(y,1 if annual else month-2,1).isoformat(),
                 end=date(y,month,monthrange(y,month)[1]).isoformat()) for y in [year-1,year]]


def financial_table(id_,titles,periods,source,rows):
    return dict(id=id_,titleKo=titles[0],titleEn=titles[1],periods=periods,source=source,
                currency="USD",unitKo="백만 달러",unitEn="USD million",measure="financial-results",
                rows=[dict(key=k,ko=ko,en=en,kind="leaf",level=0,parent=None,values=values) for (k,ko,en),values in rows],
                total=None,notes=[],notesEn=[],marks=[],comparableFrom=periods[0]["label"],
                compositionKeys=[],compositionPeriods=[])


def ti_statement(data,entry,section):
    year,q,published,url=entry
    doc=html.fromstring(data)
    title=" ".join(doc.xpath("string(//h1)").lower().split())
    ordinal=next(k for k,v in QUARTERS.items() if v==q)
    pattern=rf"ti reports (?:{ordinal} quarter|q{q}) {year}(?: and {year})? financial results(?: and shareholder returns)?"
    if not re.fullmatch(pattern,title) or doc.xpath('//meta[@property="article:published_time"]/@content')!=[published.isoformat()]:
        raise ValueError("TI title, fiscal period or release date mismatch")
    annual=section=="annual"
    if annual and q!=4:raise ValueError("A year-end statement is required")
    periods=ti_periods(year,q,annual)
    end=periods[-1]["end"]
    if not end<published.isoformat():raise ValueError("TI release predates fiscal period end")
    source=dict(label="TI 연간 실적 발표" if annual else "TI 분기 실적 발표",
                labelEn="TI annual earnings release" if annual else "TI quarterly earnings release",
                periodEnd=end,published=published.isoformat(),url=url)
    day=month_name[3*q]+" "+str(monthrange(year,3*q)[1])+","
    headings=["Consolidated Statements of Income","For Three Months Ended "+day]
    if q==4:headings.append("For Years Ended "+day)
    years=[str(year),str(year-1)]
    columns=years*(2 if q==4 else 1)
    segment_head=["(In millions)",*(years if annual else ["Q"+str(q)+" "+y for y in years]),"Change"]
    earnings={}
    segment={}
    grid=[ti_rows(t) for t in doc.xpath("//table")]
    for rows in grid:
        for i,row in enumerate(rows):
            if row!=headings:continue
            if (i==0 or ["TEXAS INSTRUMENTS INCORPORATED AND SUBSIDIARIES"] not in rows[:i] or
                    rows[i+1:i+2]!=[["(In millions, except per-share amounts)",*columns]]):
                raise ValueError("TI income statement identity or unit mismatch")
            for cells in rows[i+2:]:
                if not cells or cells[0] not in METRICS:continue
                if len(cells)!=len(columns)+1:raise ValueError("TI income statement column mismatch")
                offset=3 if annual else 1
                vals=[amount(cells[offset+1]),amount(cells[offset])]
                if cells[0] in earnings and earnings[cells[0]]!=vals:raise ValueError("Conflicting TI statement rows")
                earnings[cells[0]]=vals
        if not rows or rows[0]!=segment_head:continue
        active=None
        for cells in rows[1:]:
            if len(cells)==1 and cells[0].endswith(":"):
                active=cells[0]
            if cells and cells[0]=="Revenue" and active:
                if active not in SEGMENTS or active in segment or len(cells)!=4:
                    raise ValueError("TI business segment layout changed")
                segment[active]=[amount(cells[2]),amount(cells[1])]
    if earnings.keys()!=METRICS.keys() or segment.keys()!=SEGMENTS.keys():
        raise ValueError("Incomplete TI earnings or segment statements")
    if [sum(v[n] for v in segment.values()) for n in (0,1)]!=earnings["Revenue"]:
        raise ValueError("TI segment and consolidated revenue do not reconcile")
    interval=("연간","Annual") if annual else ("3개월","Quarterly")
    ops=financial_table("ti-income-"+section,("연결 손익 · "+interval[0],interval[1]+" consolidated income"),
                 periods,source,[(label,earnings[k]) for k,label in METRICS.items()])
    sales=financial_table("ti-segments-"+section,("사업별 매출 · "+interval[0],interval[1]+" revenue by business"),
                   periods,source,[(label,segment[k]) for k,label in SEGMENTS.items()])
    sales.update(measure="revenue",total=earnings["Revenue"],compositionKeys=[x[0] for x in SEGMENTS.values()],
                 compositionPeriods=[p["label"] for p in periods])
    return dict(source,kind=section),[sales,ops]


MSFT_INDEX = "https://www.microsoft.com/en-us/investor/default"
MSFT_PATH = re.compile(r"/en-us/investor/earnings/fy-(\d{4})-q([1-4])/press-release-webcast/?", re.I)
MSFT_DATELINE = re.compile(
    r"REDMOND, Wash\.\s*[—–-]\s*([A-Za-z]+ \d{1,2}, \d{4})\s*[—–-]\s*"
    r"Microsoft Corp\. today announced the following results for the quarter ended ([A-Za-z]+ \d{1,2}, \d{4})\b")
MSFT_CAPTIONS = {
    "MICROSOFT CORPORATION INCOME STATEMENTS (In millions, except per share amounts) (Unaudited)": "income",
    "SEGMENT RESULTS (In millions) (Unaudited)": "segments",
    "PRODUCT AND SERVICE OFFERINGS REVENUE (In millions) (Unaudited)": "products",
}
MSFT_METRICS = {"Total revenue": METRICS["Revenue"], "Gross margin": METRICS["Gross profit"],
                "Operating income": METRICS["Operating profit"], "Net income": METRICS["Net income"]}
MSFT_NAMES = {
    "Agents and Infra": "에이전트·인프라", "Devices and Consumer": "기기·소비자",
    "Productivity and Business Processes": "생산성·비즈니스 프로세스", "Intelligent Cloud": "인텔리전트 클라우드",
    "More Personal Computing": "퍼스널 컴퓨팅", "Azure": "Azure", "Microsoft 365 cloud": "Microsoft 365 클라우드",
    "Productivity and server licensing": "생산성·서버 라이선스", "Search and advertising": "검색·광고",
    "XBOX": "Xbox", "Industry solutions": "산업별 솔루션", "Windows OEM and devices": "Windows OEM·기기",
    "Frontier and support services": "프런티어·지원 서비스",
}


def microsoft_listing(data):
    """Read the featured quarter, then verify the latest completed FY on the same IR archive."""
    doc = html.fromstring(data)
    entries = {}
    for a in doc.xpath("//a[@href]"):
        url = urljoin(MSFT_INDEX, a.get("href"))
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != "www.microsoft.com" or parts.query or parts.fragment:
            continue
        match = MSFT_PATH.fullmatch(parts.path)
        if match:
            year, quarter = map(int, match.groups())
            entries[year, quarter] = url
    if not entries:
        raise ValueError("Microsoft IR has no quarterly earnings release link")
    year, quarter = max(entries)
    latest = entries[year, quarter]
    annual = (year if quarter == 4 else year - 1, 4)
    year_end = entries.get(annual) or MSFT_PATH.sub(
        f"/en-us/Investor/earnings/FY-{annual[0]}-Q4/press-release-webcast", urlsplit(latest).path)
    return {"annual": (*annual, urljoin(MSFT_INDEX, year_end)), "interim": (year, quarter, latest)}


def microsoft_rows(table):
    rows = [row for row in ti_rows(table) if row]
    caption = " ".join(table.xpath("string(./caption)").split())
    if caption:
        return MSFT_CAPTIONS.get(caption), rows
    # Earlier releases encode the same caption as separate rows in the table.
    for count in (2,3):
        prefix = rows[:count]
        if all(len(row) == 1 for row in prefix):
            kind = MSFT_CAPTIONS.get(" ".join(row[0] for row in prefix))
            if kind:
                return kind, rows[count:]
    return None, rows


def microsoft_numeric_rows(rows, end, quarter, section):
    suffix = " Ended " + end.strftime("%B") + " " + str(end.day) + ","
    quarter_heading = "Three Months" + suffix
    periods = {2: "Six Months", 3: "Nine Months", 4: "Twelve Months"}
    expected_headings = [[quarter_heading]]
    if quarter in periods:
        expected_headings.append([quarter_heading, periods[quarter] + suffix])
    if len(rows) < 3 or rows[0] not in expected_headings:
        raise ValueError("Unrecognized Microsoft financial statement period")
    pairs = len(rows[0])
    if rows[1] != [str(end.year), str(end.year - 1)] * pairs:
        raise ValueError("Microsoft comparison years do not match the release")
    if section in {"annual","ytd"} and (pairs != 2 or (section == "annual" and quarter != 4)):
        raise ValueError("Microsoft requested cumulative columns unavailable")
    offset = 1 if section == "interim" else 3

    def values(row):
        if len(row) != 1 + pairs * 2:
            raise ValueError("Microsoft statement columns changed")
        return [amount(row[i].removeprefix("$").strip()) for i in (offset + 1, offset)]

    return rows[2:], values


def microsoft_statement(data, entry, section):
    fy, quarter, url = entry
    doc = html.fromstring(data)
    title = " ".join(doc.xpath("string(//title)").split())
    if title != f"FY{fy%100:02d} Q{quarter} - Press Releases - Investor Relations - Microsoft":
        raise ValueError("Microsoft issuer or fiscal quarter mismatch")
    dates = {m.groups() for p in doc.xpath("//p")
             if (m := MSFT_DATELINE.match(" ".join(p.text_content().split())))}
    if len(dates) != 1:
        raise ValueError("Missing or conflicting Microsoft release dateline")
    published, end = (datetime.strptime(s, "%B %d, %Y").date() for s in dates.pop())
    month = (9, 12, 3, 6)[quarter - 1]
    year = fy - (1 if quarter <= 2 else 0)
    if end != date(year, month, monthrange(year, month)[1]) or published <= end:
        raise ValueError("Microsoft release date conflicts with the fiscal calendar")
    annual = section == "annual"
    ytd = section == "ytd"
    if annual and quarter != 4:
        raise ValueError("An annual Microsoft release requires the fiscal fourth quarter")
    periods = []
    for y in (year - 1, year):
        label = f"{y}.{month:02d}"
        fiscal_start = date(y-1 if month <= 6 else y, 7, 1)
        periods.append(dict(label=label, labelEn=label,
                            start=(fiscal_start if annual or ytd else date(y,month-2,1)).isoformat(),
                            end=date(y, month, monthrange(y, month)[1]).isoformat()))
    interval = ("3개월","Quarterly")
    if annual:
        interval = ("연간","Annual")
    elif ytd:
        interval = (f"{3*quarter}개월 누적",f"{3*quarter}-month cumulative")
    source = dict(label="Microsoft 연간 실적 발표" if annual else "Microsoft 분기 실적 발표",
                  labelEn="Microsoft annual earnings release" if annual else "Microsoft quarterly earnings release",
                  url=url, published=published.isoformat(), periodEnd=end.isoformat())
    tables = {}
    for table in doc.xpath("//table"):
        kind, raw_rows = microsoft_rows(table)
        if not kind:
            continue
        if kind in tables:
            raise ValueError("Duplicate Microsoft financial statement")
        if ytd and kind == "products" and raw_rows and len(raw_rows[0]) == 1:
            continue  # Some product schedules disclose only the three-month interval.
        rows, values = microsoft_numeric_rows(raw_rows, end, quarter, section)
        if kind == "income":
            metrics = {row[0]: values(row) for row in rows if row[0] in MSFT_METRICS}
            if metrics.keys() != MSFT_METRICS.keys():
                raise ValueError("Incomplete Microsoft GAAP statement")
            tables[kind] = financial_table("msft-income-"+section, ("연결 손익 · "+interval[0],
                interval[1]+" consolidated income"), periods, source,
                [(definition, metrics[name]) for name, definition in MSFT_METRICS.items()])
            continue
        names = []
        total = None
        if kind == "segments":
            for i, row in enumerate(rows):
                if row[0] != "Revenue":
                    continue
                if i == 0 or len(rows[i-1]) != 1:
                    raise ValueError("Microsoft segment revenue label missing")
                name = rows[i-1][0]
                if name == "Total":
                    total = values(row)
                else:
                    names.append((name, values(row)))
        else:
            for row in rows:
                if row[0] == "Total revenue":
                    total = values(row)
                    break
                names.append((row[0], values(row)))
        if len(names) < 2 or len({n for n, _ in names}) != len(names):
            raise ValueError("Incomplete Microsoft revenue breakdown")
        if [sum(v[i] for _,v in names) for i in (0,1)] != total:
            raise ValueError("Microsoft revenue rows do not reconcile")
        definitions = [((re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-"),
                         MSFT_NAMES.get(name, name), name), v) for name,v in names]
        titles = ("사업별 매출", "revenue by business") if kind == "segments" else ("제품·서비스별 매출", "revenue by product and service")
        parsed = financial_table(f"msft-{kind}-{section}",(titles[0]+" · "+interval[0], interval[1]+" "+titles[1]),
                                 periods, source, definitions)
        parsed.update(measure="revenue",total=total,compositionKeys=[d[0] for d,_ in definitions],
                      compositionPeriods=[p["label"] for p in periods])
        if any("recast" in row[0].lower() for row in rows):
            parsed["notes"] = ["비교 기간도 이번 발표의 사업 분류에 맞춰 다시 작성됐습니다."]
            parsed["notesEn"] = ["Microsoft recast the comparative figures to match this release’s business categories."]
        tables[kind] = parsed
    if not {"segments","income"} <= tables.keys():
        raise ValueError("Microsoft income or segment statements absent")
    revenue = tables["income"]["rows"][0]["values"]
    if any(t["total"] != revenue for k,t in tables.items() if k != "income"):
        raise ValueError("Microsoft revenue breakdown and GAAP total disagree")
    ordered = [tables[k] for k in ("segments","products","income") if k in tables]
    if section == "interim" and quarter in (2,3):
        # The GAAP table headers must expressly identify the 6/9-month columns.
        has_ytd = any(kind == "income" and len(rows[0]) == 2 for kind,rows in
                      (microsoft_rows(t) for t in doc.xpath("//table")) if rows)
        if has_ytd:
            ordered.extend(microsoft_statement(data,entry,"ytd")[1])
    return dict(source,kind=section),ordered


def refresh_native(report,cik,fetch):
    if report["ticker"]=="TXN" and int(cik)==97476:
        listed=ti_listing(fetch(TI_INDEX))
        entries={section:max((r for r in listed if section=="interim" or r[1]==4),default=None)
                 for section in ("annual","interim")}
        read_statement=ti_statement
        owned_prefix="ti-"
    elif report["ticker"]=="MSFT" and int(cik)==789019:
        entries=microsoft_listing(fetch(MSFT_INDEX))
        read_statement=microsoft_statement
        owned_prefix="msft-"
    else:
        raise ValueError("Unsupported issuer-native company")
    output=deepcopy(report)
    latest,warnings,cache=[],[],{}
    for section in ("annual","interim"):
        try:
            entry=entries[section]
            if not entry:raise ValueError("No issuer reporting period found")
            url=entry[-1]
            if url not in cache:cache[url]=fetch(url)
            source,tables=read_statement(cache[url],entry,section)
            last=max((p["end"] for t in report[section] for p in t["periods"] if p.get("end")),default="")
            if source["periodEnd"]<last:raise ValueError("Issuer lags the published fiscal period")
            if any(t["source"].get("periodEnd")==source["periodEnd"] and
                   (t["source"].get("published") or "")>source["published"] for t in report[section]):
                raise ValueError("Issuer page lags a later release for the same period")
            # Drop this provider's older optional schedules when the new quarter omits them.
            prior=[t for t in report[section] if not t["id"].startswith(owned_prefix)]
            # A release can supplement regulatory data, including audited numbers, for the same period.
            matching=[t for t in prior if t["source"].get("filed") and
                      any(p.get("end")==source["periodEnd"] for p in t["periods"])]
            remaining=[t for t in prior if t not in matching]
            output[section]=matching+tables+remaining
            latest.append(source)
        except (OSError,ValueError,etree.Error) as exc:
            warnings.append(section+"-unavailable ("+str(exc)+")")
    if not latest:raise ValueError("; ".join(warnings))
    return output,{"latest":latest,"warnings":warnings}
