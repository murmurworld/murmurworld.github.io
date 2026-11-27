"""Read signed filings and original earnings releases published by technology companies."""

from copy import deepcopy
from datetime import date, datetime
from gzip import GzipFile
from io import BytesIO
import re
from urllib.parse import unquote, urljoin, urlsplit

from lxml import etree, html
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from issuer_native import METRICS, QUARTERS, amount, financial_table, ti_rows


DIRECTORIES = {
    "LRCX": "https://investor.lamresearch.com/quarterly-results/",
    "SNDK": "https://www.sandisk.com/sitemap.xml",
    "AVGO": "https://www.prnewswire.com/news/broadcom-inc./",
    "PANW": "https://www.prnewswire.com/news/palo-alto-networks%2C-inc./",
}
TECHNOLOGY_HOSTS = {urlsplit(url).hostname for url in DIRECTORIES.values()}
TECHNOLOGY_TICKERS = set(DIRECTORIES)
CIKS = {"LRCX": 707549, "SNDK": 2023554, "AVGO": 1730168, "PANW":1327567}
MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_WORDS = MONTH + r" \d{1,2},\s*\d{4}"
SANDISK = re.compile(
    r"/company/newsroom/press-releases/(\d{4})/(\d{4}-\d{1,2}-\d{1,2})-"
    r"sandisk-reports-fiscal-(first|second|third|fourth)-quarter-(\d{4})-financial-results"
)
SYSTEMS = ("systems", "반도체 제조 장비", "Systems")
SUPPORT = ("support", "고객 지원·기타", "Customer support and other")
MARKETS = {
    "Datacenter": ("datacenter", "데이터센터", "Datacenter"),
    "Edge": ("edge", "엣지", "Edge"),
    "Consumer": ("consumer", "소비자", "Consumer"),
}
BROADCOM = re.compile(
    r"/news-releases/broadcom-inc-announces-(first|second|third|fourth)-quarter-(?:and-)?fiscal-year-"
    r"(\d{4})-financial-results(?:-and-quarterly-dividend)?-\d+\.html"
)
PALO_ALTO = re.compile(r"/news-releases/palo-alto-networks-reports-fiscal-(first|second|third|fourth)-quarter-(?:and-fiscal-year-)?(\d{4})-financial-results-\d+\.html")


def decoded(raw):
    if raw.startswith(b"\x1f\x8b"):
        with GzipFile(fileobj=BytesIO(raw)) as stream:
            raw = stream.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError("Issuer HTML/XML exceeds size limit")
    return raw


def full_date(text):
    return datetime.strptime(re.sub(r",\s*", ", ", text), "%B %d, %Y").date()


def periods(ends, annual):
    output = []
    for end in ends:
        month = end.strftime("%Y.%m")
        output.append(
            {
                "label": month if annual else month + " · 3개월",
                "labelEn": month if annual else month + " · 3 months",
                "end": end.isoformat(),
            }
        )
    return output


def number(cell):
    return amount(cell.removeprefix("$").strip())


def tables_for(ticker, section, ends, source, segment_data, revenue, income):
    annual = section == "annual"
    if ends != sorted(ends) or len(set(ends)) != len(ends) or len(ends) < 2:
        raise ValueError("Invalid financial comparison periods")
    if any(not 350 <= (b - a).days <= 375 for a, b in zip(ends, ends[1:])):
        raise ValueError("Financial periods are not year-over-year comparisons")
    if [sum(values[i] for _, values in segment_data) for i in range(len(ends))] != revenue or income[0][
        1
    ] != revenue:
        raise ValueError("Disclosed revenue categories and GAAP income statement disagree")
    section_id = ticker.lower() + "-"
    interval = ("연간", "Annual") if annual else ("3개월", "Quarterly")
    p = periods(ends, annual)
    label = {
        "LRCX": ("제품·서비스별 매출", "revenue by product and service"),
        "SNDK": ("최종 시장별 매출", "revenue by end market"),
        "AVGO": ("사업부별 매출", "revenue by segment"),
        "PANW": ("제품·구독별 매출", "revenue by offering"),
    }[ticker]
    segment = financial_table(
        section_id + "revenue-" + section,
        (label[0] + " · " + interval[0], interval[1] + " " + label[1]),
        p,
        source,
        segment_data,
    )
    segment.update(
        measure="revenue",
        total=revenue,
        compositionKeys=[key[0] for key, _ in segment_data],
        compositionPeriods=[v["label"] for v in p],
    )
    results = financial_table(
        section_id + "income-" + section,
        ("연결 손익 · " + interval[0], interval[1] + " consolidated income"),
        p,
        source,
        income,
    )
    if ticker == "LRCX":
        for table in (segment, results):
            table.update(unitKo="천 달러", unitEn="USD thousand")
    return dict(source, kind=section), [segment, results]


def lam_list(raw):
    doc = html.fromstring(decoded(raw))
    output = {}
    months = {"MARCH": 3, "JUNE": 6, "SEPTEMBER": 9, "DECEMBER": 12}
    for item in doc.xpath("//*[@data-year]"):
        year = item.get("data-year")
        title = item.xpath('string(./div[@class="item_name"])').strip().split()
        if not year.isdigit() or len(title) != 2 or title[0] not in months or title[1] != "QUARTER":
            continue
        for anchor in item.xpath(".//a[@href]"):
            form = anchor.text_content().strip().upper()
            if form not in {"FORM 10-K", "FORM 10-Q"}:
                continue
            section = "annual" if form == "FORM 10-K" else "interim"
            key = (int(year), months[title[0]])
            url = urljoin(DIRECTORIES["LRCX"], anchor.get("href"))
            # Some legacy rows are HTML; a newer unrecognized format must not silently select an older PDF.
            if urlsplit(url).scheme != "https" or urlsplit(url).hostname != "investor.lamresearch.com":
                url = None
            if section not in output or key > output[section][0]:
                output[section] = (key, url)
    return output


def lam_dates(header, count):
    dates = re.findall(DATE_WORDS, header)
    if len(dates) == count:
        return [full_date(d) for d in dates]
    day_lines = re.findall(MONTH + r" \d{1,2},", header)
    years = re.findall(r"\b20\d\d\b", header)
    if len(day_lines) != count or len(years) != count:
        raise ValueError("Unrecognized Lam table date columns")
    return [full_date(d + y) for d, y in zip(day_lines, years)]


def lam_row(text, name):
    match = re.search(r"(?im)^\s*" + re.escape(name) + r"(?=\s+\$?\s*\(?\d)\s+([^\n]*)$", text)
    if not match:
        raise ValueError("Lam statement omits " + name)
    return [number(c) for c in match[1].replace("$", " ").split()]


def lam_statement(raw, entry, section):
    (year, month), url = entry
    annual = section == "annual"
    form = "10-K" if annual else "10-Q"
    file_dates = re.findall(r"\b20\d\d-\d\d-\d\d\b|\d{2}_\d{2}_20\d\d", unquote(urlsplit(url).path))
    if len(file_dates) != 1 or not re.search(r"\.pdf(?:_\.pdf)?$", urlsplit(url).path, re.I):
        raise ValueError("Lam filing archive lacks a dated PDF")
    token = file_dates[0]
    filed = datetime.strptime(token, "%m_%d_%Y" if "_" in token else "%Y-%m-%d").date()
    pdf = PdfReader(BytesIO(raw))
    if len(pdf.pages) > 240:
        raise ValueError("Unexpected Lam filing length")
    cover = " ".join(pdf.pages[0].extract_text().split())
    phrase = "fiscal year" if annual else "quarterly period"
    period = re.search("For the " + phrase + " ended (" + DATE_WORDS + ")", cover, re.I)
    if (
        "LAM RESEARCH CORPORATION" not in cover
        or not re.search(r"FORM\s*" + form + r"\b", cover)
        or not period
    ):
        raise ValueError("Lam issuer, form or reporting period mismatch")
    end = full_date(period[1])
    if (end.year, end.month) != (year, month) or not end < filed <= date.today():
        raise ValueError("Lam filing date mismatch")
    pages = [
        "\n".join(
            " ".join(line.split())
            for line in p.extract_text(extraction_mode="layout").splitlines()
            if line.strip()
        )
        for p in pdf.pages
    ]
    signed = re.compile(r"SIGNATURES\nPursuant to the requirements[\s\S]{0,500}?Date: (" + DATE_WORDS + ")")
    if not any(m and full_date(m[1]) == filed for m in (signed.search(p) for p in pages)):
        raise ValueError("Lam issuer signature and filing archive date disagree")
    stmt = re.compile(
        r"(?:CONDENSED )?CONSOLIDATED STATEMENTS OF OPERATIONS\n\(in thousands, except per share data\)"
        r"[\s\S]{1,450}?\nRevenue\s+[\d$]"
    )
    statement = next((p for p in pages if stmt.search(p)), None)
    if not statement:
        raise ValueError("Lam signed consolidated GAAP table unavailable")
    names = ("Revenue", "Gross margin", "Operating income", "Net income")
    values = [lam_row(statement, name) for name in names]
    count = len(values[0])
    header = statement[stmt.search(statement).start() :].split("\nRevenue", 1)[0]
    if ("Year Ended" if annual else "Three Months Ended") not in header:
        raise ValueError("Lam income period scope changed")
    stamps = lam_dates(header, count)
    take = 3 if annual else 2
    if len(stamps) < take or stamps[0] != end:
        raise ValueError("Lam GAAP reporting period disagrees with cover")
    order = list(reversed(range(take)))
    ends = [stamps[i] for i in order]
    if any(len(v) != count for v in values):
        raise ValueError("Incomplete Lam income row")
    income = [(label, [v[i] for i in order]) for label, v in zip(METRICS.values(), values)]
    segment = None
    for page in pages:
        for match in re.finditer(r"(?im)^Systems revenue (?=\$?\s*\d)", page):
            before = page[: match.start()].splitlines()[-7:]
            heading = "\n".join(before)
            marker = "Year Ended" if annual else "Three Months Ended"
            if marker not in heading or "(in thousands)" not in heading:
                continue
            chunk = page[match.start() :].split("\n", 3)[:3]
            if len(chunk) != 3 or not chunk[2].startswith("$"):
                continue
            system = lam_row(chunk[0], "Systems revenue")
            dates = lam_dates(heading.split(marker, 1)[1], len(system))
            if len(dates) < take or [dates[i] for i in order] != ends:
                continue
            support = lam_row(chunk[1], "Customer support-related revenue and other")
            totals = [number(c) for c in chunk[2].replace("$", " ").split()]
            if len(support) != len(system) or len(totals) != len(system):
                raise ValueError("Lam equipment and support columns disagree")
            segment = [
                (label, [row[i] for i in order]) for label, row in ((SYSTEMS, system), (SUPPORT, support))
            ]
            if [totals[i] for i in order] != income[0][1]:
                raise ValueError("Lam note total and GAAP revenue disagree")
            break
        if segment:
            break
    if not segment:
        raise ValueError("No matching Lam revenue note")
    source = dict(
        label="램리서치 " + form + " 원문",
        labelEn="Lam Research Form " + form,
        url=url,
        periodEnd=end.isoformat(),
        filed=filed.isoformat(),
    )
    return tables_for("LRCX", section, ends, source, segment, income[0][1], income)


def sandisk_list(raw):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    root = etree.fromstring(decoded(raw), parser)
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if root.tag != ns + "urlset" or root.getroottree().docinfo.internalDTD is not None:
        raise ValueError("Invalid Sandisk sitemap")
    items = []
    for e in root.iter(ns + "loc"):
        url = e.text or ""
        parts = urlsplit(url)
        match = SANDISK.fullmatch(parts.path)
        if (
            not match
            or parts.scheme != "https"
            or parts.netloc != "www.sandisk.com"
            or parts.query
            or parts.fragment
        ):
            continue
        path_year, day, q, fy = match.groups()
        published = datetime.strptime(day, "%Y-%m-%d").date()
        if int(path_year) == published.year and published <= date.today():
            items.append((int(fy), QUARTERS[q], published, url))
    return {
        section: max((i for i in items if section == "interim" or i[1] == 4), default=None)
        for section in ("annual", "interim")
    }


def sandisk_statement(raw, entry, section):
    fy, q, published, url = entry
    doc = html.fromstring(decoded(raw), parser=html.HTMLParser(encoding="utf-8"))
    title = " ".join(doc.xpath("string(//h1)").split())
    ordinal = next(n for n, v in QUARTERS.items() if v == q).title()
    if title != f"Sandisk Reports Fiscal {ordinal} Quarter {fy} Financial Results":
        raise ValueError("Sandisk issuer or fiscal title mismatch")
    text = " ".join(doc.xpath("string(//body)").split())
    date_line = re.search(r"Milpitas, (?:California|Calif\.)\s*[-–—]\s*(" + DATE_WORDS + ")", text, re.I)
    if not date_line or full_date(date_line[1]) != published:
        raise ValueError("Sandisk publication date differs from its sitemap")
    annual = section == "annual"
    if annual and q != 4:
        raise ValueError("Sandisk annual income requires a fiscal year-end release")
    metrics = {
        "Revenue, net": "Revenue",
        "Gross profit": "Gross profit",
        "Operating income": "Operating profit",
        "Net income": "Net income",
    }
    income = None
    segment = None
    tail = f"Q{q} {fy-1}"
    for table in doc.xpath("//table"):
        rows = [r for r in ti_rows(table) if r]
        if len(rows) < 4:
            continue
        caption = " ".join(table.xpath("string(./caption)").split())
        if len(rows[2]) >= 3 and rows[2][0] == "Revenue, net" and rows[0][0] == "Three Months Ended":
            if "Consolidated Statements of Operations" not in caption or "in millions" not in caption.lower():
                raise ValueError("Sandisk GAAP statement identity or unit mismatch")
            if annual and rows[0] != ["Three Months Ended", "Year Ended"]:
                raise ValueError("Sandisk year-end column unavailable")
            offset = 2 if annual else 0
            if len(rows[1]) % 2 != 0 or len(rows[1]) < offset + 2:
                raise ValueError("Sandisk statement period count changed")
            ends = [full_date(rows[1][i]) for i in (offset + 1, offset)]
            parsed = {}
            for row in rows[2:]:
                key = metrics.get(row[0].removesuffix(" (loss)"))
                if key:
                    if len(row) != len(rows[1]) + 1 or key in parsed:
                        raise ValueError("Duplicate or incomplete Sandisk GAAP row")
                    parsed[key] = [number(row[i]) for i in (offset + 2, offset + 1)]
            if parsed.keys() != METRICS.keys():
                raise ValueError("Incomplete Sandisk GAAP income statement")
            if income is not None:
                raise ValueError("Ambiguous Sandisk statement")
            income = [(label, parsed[key]) for key, label in METRICS.items()]
        head = rows[0]
        year_head = ["Revenue", str(fy), str(fy - 1), "Y/Y"]
        quarter_head = ["Revenue", f"Q{q} {fy}", f"Q{q-1 or 4} {fy if q>1 else fy-1}", "Q/Q", tail, "Y/Y"]
        if head != (year_head if annual else quarter_head):
            continue
        if "($ in millions)" not in caption:
            raise ValueError("Unrecognized Sandisk revenue unit")
        if any(len(r) != len(head) for r in rows[1:]):
            raise ValueError("Incomplete Sandisk market row")
        if {r[0] for r in rows[1:]} != set(MARKETS) | {"Total Revenue"} or len(rows[1:]) != len(MARKETS) + 1:
            raise ValueError("Sandisk market classification changed")
        values = {r[0]: [number(r[2 if annual else 4]), number(r[1])] for r in rows[1:]}
        segment = [(label, values[k]) for k, label in MARKETS.items()]
        total = values["Total Revenue"]
    if not segment or not income:
        raise ValueError("Missing Sandisk GAAP or end-market disclosure")
    end = ends[-1]
    if not 0 < (published - end).days < 110 or end.year != (fy - 1 if q in {1, 2} and end.month >= 9 else fy):
        raise ValueError("Sandisk table period outside release fiscal year")
    source = dict(
        label="샌디스크 연간 실적 발표" if annual else "샌디스크 분기 실적 발표",
        labelEn="Sandisk annual earnings release" if annual else "Sandisk quarterly earnings release",
        url=url,
        periodEnd=end.isoformat(),
        published=published.isoformat(),
    )
    return tables_for("SNDK", section, ends, source, segment, total, income)


def wire_list(raw, ticker):
    doc = html.fromstring(decoded(raw))
    items = []
    for anchor in doc.xpath("//a[@href]"):
        url = urljoin(DIRECTORIES[ticker], anchor.get("href"))
        parts = urlsplit(url)
        match = (BROADCOM if ticker=="AVGO" else PALO_ALTO).fullmatch(parts.path)
        if (
            not match
            or parts.scheme != "https"
            or parts.netloc != "www.prnewswire.com"
            or parts.query
            or parts.fragment
        ):
            continue
        listing_date = re.match(r"([A-Za-z]{3} \d{1,2}, \d{4})", anchor.text_content().strip())
        if not listing_date:
            continue
        day = datetime.strptime(listing_date[1], "%b %d, %Y").date()
        if day <= date.today():
            items.append((int(match[2]), QUARTERS[match[1]], day, url))
    return {
        section: max((i for i in items if section == "interim" or i[1] == 4), default=None)
        for section in ("annual", "interim")
    }


def wire_release(raw,ticker,entry):
    fy, q, published, url = entry
    doc = html.fromstring(decoded(raw), parser=html.HTMLParser(encoding="utf-8"))
    ordinal = next(n for n, v in QUARTERS.items() if v == q).title()
    if ticker=="AVGO":
        title = (
        f"Broadcom Inc. Announces {ordinal} Quarter "
        + ("and " if q == 4 else "")
        + f"Fiscal Year {fy} Financial Results"
        )
        titles=(title,title+" and Quarterly Dividend")
        author="Broadcom Inc."
    else:
        titles=(f"Palo Alto Networks Reports Fiscal {ordinal} Quarter "+("and Fiscal Year " if q==4 else "")+f"{fy} Financial Results",)
        author="Palo Alto Networks, Inc."
    actual = " ".join(doc.xpath("string(//h1)").split())
    publisher = doc.xpath("//a[@href=$path and normalize-space(.)=$author]",path=urlsplit(DIRECTORIES[ticker]).path,author=author)
    dateline = doc.xpath("//meta[@name='date']/@content")
    if (
        actual not in titles
        or not publisher
        or len(dateline) != 1
        or datetime.fromisoformat(dateline[0]).date() != published
    ):
        raise ValueError("Issuer release identity, fiscal title or publication date mismatch")
    return doc


def broadcom_statement(raw, entry, section):
    fy,q,published,url=entry
    doc=wire_release(raw,"AVGO",entry)
    annual = section == "annual"
    tag = "FY" if annual else "Q" + str(q)
    summary_header = [
        "(Dollars in millions)",
        tag + " " + str(fy)[-2:],
        tag + " " + str(fy - 1)[-2:],
        "Change",
    ]
    income = None
    segment = None
    grids = [[r for r in ti_rows(t) if r] for t in doc.xpath("//table")]
    for rows in grids:
        if len(rows) < 6:
            continue
        if rows[:3] != [
            ["BROADCOM INC."],
            ["CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS - UNAUDITED"],
            ["(IN MILLIONS, EXCEPT PER SHARE DATA)"],
        ]:
            continue
        if rows[3][0] != "Fiscal Quarter Ended" or (
            annual and (q != 4 or rows[3][-1] != "Fiscal Year Ended")
        ):
            raise ValueError("Broadcom GAAP reporting scope changed")
        if len(rows[4]) != len(rows[5]) or len(rows[4]) not in {3, 5}:
            raise ValueError("Unexpected Broadcom statement headers")
        stamps = [full_date(d + y) for d, y in zip(rows[4], rows[5])]
        if stamps[0].year != fy or not 0 < (published - stamps[0]).days < 100:
            raise ValueError("Broadcom release conflicts with period end")
        order = (4, 3) if annual else (2, 0)
        ends = [stamps[i] for i in order]
        names = {
            "Net revenue": "Revenue",
            "Gross margin": "Gross profit",
            "Operating income": "Operating profit",
            "Net income": "Net income",
        }
        metrics = {}
        for row in rows[6:]:
            key = names.get(row[0])
            if not key:
                continue
            if len(row) != len(stamps) + 1 or key in metrics:
                raise ValueError("Broadcom GAAP statement columns disagree")
            metrics[key] = [number(row[i + 1]) for i in order]
        if metrics.keys() != METRICS.keys() or income:
            raise ValueError("Incomplete or duplicated Broadcom income statement")
        income = [(label, metrics[key]) for key, label in METRICS.items()]
    # Strip detached percent symbols. The remaining four fields are current $
    # and %, prior $ and %, followed by growth in the individual segment rows.
    names = {
        "Semiconductor solutions": ("semis", "반도체 솔루션", "Semiconductor solutions"),
        "Infrastructure software": ("software", "인프라 소프트웨어", "Infrastructure software"),
    }
    for rows in grids:
        if rows[:2] != [["Net revenue by segment"], summary_header]:
            continue
        if [r[0] for r in rows[2:]] != [*names, "Total net revenue"] or segment:
            raise ValueError("Unexpected Broadcom segment classification")
        values = {}
        for row in rows[2:]:
            nums = [v for v in row[1:] if v != "%"]
            if len(nums) != (4 if row[0] == "Total net revenue" else 5):
                raise ValueError("Unexpected Broadcom segment columns")
            if any(not 0 <= number(nums[i]) <= 100 for i in [1, 3]):
                raise ValueError("Invalid Broadcom revenue share")
            values[row[0]] = [number(nums[2]), number(nums[0])]
        total = values["Total net revenue"]
        segment = [(label, values[name]) for name, label in names.items()]
    if not income or not segment:
        raise ValueError("Broadcom release omits GAAP income or segment table")
    source = dict(
        label="브로드컴 실적 발표 · PR Newswire",
        labelEn="Broadcom earnings release via PR Newswire",
        url=url,
        periodEnd=ends[-1].isoformat(),
        published=published.isoformat(),
    )
    return tables_for("AVGO", section, ends, source, segment, total, income)


def palo_alto_statement(raw,entry,section):
    fy,q,published,url=entry
    doc=wire_release(raw,"PANW",entry)
    annual=section=="annual"
    period_phrase={2:"Six Months Ended",3:"Nine Months Ended",4:"Year Ended"}
    expected_headings=[["Three Months Ended"]]
    if q in period_phrase:expected_headings.append(["Three Months Ended",period_phrase[q]])
    header=[["Palo Alto Networks, Inc."],["Preliminary Condensed Consolidated Statements of Operations"],
            ["(In millions, except per share data)"],["(Unaudited)"]]
    statements=[[r for r in ti_rows(t) if r] for t in doc.xpath("//table")]
    statements=[rows for rows in statements if rows[:4]==header]
    if len(statements)!=1:raise ValueError("Palo Alto GAAP income statement identity or unit changed")
    rows=statements[0]
    if rows[4] not in expected_headings or annual and (q!=4 or rows[4][-1]!="Year Ended"):
        raise ValueError("Palo Alto reporting scope changed")
    dates,years=rows[5:7]
    if len(dates)!=len(rows[4]) or len(years)!=len(dates)*2:raise ValueError("Unexpected Palo Alto fiscal date columns")
    offset=2 if annual else 0
    ends=[full_date(dates[offset//2]+years[offset+i]) for i in (1,0)]
    end=ends[-1]
    fiscal_month=(10,1,4,7)[q-1]
    if end.month!=fiscal_month or end.year!=fy-(1 if q==1 else 0) or not 0<(published-end).days<100:
        raise ValueError("Palo Alto statement dates disagree with release")
    if [r[0] for r in rows[7:12]]!=["Revenue:","Product","Subscription and support","Total revenue","Cost of revenue:"]:
        raise ValueError("Palo Alto revenue classification changed")
    def values(row):
        if len(row)!=len(years)+1:raise ValueError("Palo Alto financial columns changed")
        return [number(row[offset+i]) for i in (2,1)]
    segment=[(("products","제품","Product"),values(rows[8])),
             (("subscription","구독·지원","Subscription and support"),values(rows[9]))]
    names={"Total revenue":"Revenue","Total gross profit":"Gross profit","Operating income":"Operating profit","Net income":"Net income"}
    metrics={}
    for r in rows[7:]:
        key=names.get(r[0].removesuffix(" (loss)"))
        if key:
            if key in metrics:raise ValueError("Duplicate Palo Alto GAAP item")
            metrics[key]=values(r)
    if metrics.keys()!=METRICS.keys():raise ValueError("Incomplete Palo Alto GAAP income statement")
    income=[(label,metrics[key]) for key,label in METRICS.items()]
    source=dict(label="팔로알토네트웍스 잠정 실적 발표 · PR Newswire",labelEn="Palo Alto Networks preliminary earnings release via PR Newswire",
                url=url,periodEnd=end.isoformat(),published=published.isoformat())
    return tables_for("PANW",section,ends,source,segment,metrics["Revenue"],income)


def refresh_technology(report, cik, fetch):
    ticker = report["ticker"]
    if CIKS.get(ticker) != int(cik):
        raise ValueError("Unknown technology issuer CIK")
    raw=fetch(DIRECTORIES[ticker])
    if ticker in {"AVGO","PANW"}:entries=wire_list(raw,ticker)
    else:entries=(lam_list if ticker=="LRCX" else sandisk_list)(raw)
    statement={"LRCX":lam_statement,"SNDK":sandisk_statement,"AVGO":broadcom_statement,"PANW":palo_alto_statement}[ticker]
    result = deepcopy(report)
    latest, warnings = [], []
    cache = {}
    for section in ("annual", "interim"):
        try:
            entry = entries.get(section)
            if not entry or not entry[-1]:
                raise ValueError("Issuer archive has no supported latest statement")
            url = entry[-1]
            if url not in cache:
                cache[url] = fetch(url)
            source, tables = statement(cache[url], entry, section)
            end = source["periodEnd"]
            owned = {t["id"] for t in tables}
            prior = [t for t in report[section] if t["id"] not in owned]
            published_end = max(
                (p["end"] for t in report[section] for p in t["periods"] if p.get("end")), default=""
            )
            if end < published_end:
                raise ValueError("Issuer archive lags the existing report")
            dated = source.get("filed") or source["published"]
            if any(
                t["id"] in owned
                and t["source"].get("periodEnd") == end
                and (t["source"].get("filed") or t["source"].get("published") or "") > dated
                for t in report[section]
            ):
                raise ValueError("Issuer archive predates a previously verified disclosure")
            same = [
                t
                for t in prior
                if t["source"].get("filed") and any(p.get("end") == end for p in t["periods"])
            ]
            result[section] = (
                tables + prior if source.get("filed") else same + tables + [t for t in prior if t not in same]
            )
            latest.append(source)
        except (ValueError, IndexError, KeyError, TypeError, OSError, etree.Error, PdfReadError) as exc:
            warnings.append(section + "-unavailable (" + str(exc) + ")")
    if not latest:
        raise ValueError("; ".join(warnings))
    return result, {"latest": latest, "warnings": warnings}
