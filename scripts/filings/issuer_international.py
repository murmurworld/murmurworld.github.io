"""First-party financial statements from TSMC and Toyota."""

from calendar import month_name, monthrange
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import re
from urllib.parse import unquote, urljoin, urlsplit

from lxml import html

INTERNATIONAL_HOSTS = {"investor.tsmc.com", "global.toyota", "openapi.twse.com.tw"}
INTERNATIONAL_TICKERS = {"TSM", "TM"}
TSMC_ARCHIVE = "https://investor.tsmc.com/english/financial-reports"
TOYOTA_INDEX = "https://global.toyota/en/ir/financial-results/"
TWSE_INCOME = "https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci"
QUARTERS = {"First Quarter": 1, "Six Months": 2, "Nine Months": 3, None: 4}
PLATFORMS = {
    "High Performance Computing": ("hpc", "고성능 컴퓨팅"),
    "Smartphone": ("smartphone", "스마트폰"),
    "Internet of Things": ("iot", "사물인터넷"),
    "Automotive": ("automotive", "차량용"),
    "Digital Consumer Electronics": ("dce", "디지털 가전"),
    "Others": ("others", "기타"),
}
PRODUCTS = {"Wafer": ("wafer", "웨이퍼"), "Others": ("others", "기타")}
HEADINGS = {"Platform": ("플랫폼별 연결 매출", "Consolidated revenue by platform"),
            "Resolution": ("공정별 웨이퍼 매출", "Wafer revenue by process node"),
            "Product": ("제품별 연결 매출", "Consolidated revenue by product")}
NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+|-)"
NODE = r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:-nanometer| micron)(?:-\d+(?:\.\d+)? micron| and above)?"


def tsm_listing(body):
    doc = html.fromstring(body)
    headings = doc.xpath("//h2[normalize-space(.)='Consolidated Financial Statements']")
    if len(headings) != 1:
        raise ValueError("TSMC consolidated-statements directory changed")
    releases = {}
    for link in headings[0].getparent().xpath(".//div[contains(concat(' ',normalize-space(@class),' '),' consolidated-list-wrapper ')]/a[@href]"):
        label = " ".join(link.text_content().split())
        match = re.fullmatch(r"(\d{4})(?: (First Quarter|Six Months|Nine Months))?", label)
        if not match or int(match[1]) < 2022:
            continue
        url = urljoin(TSMC_ARCHIVE, link.get("href"))
        address = urlsplit(url)
        if address.scheme != "https" or address.netloc != "investor.tsmc.com" or address.query or address.fragment:
            raise ValueError("Unexpected TSMC statement link")
        year, quarter = int(match[1]), QUARTERS[match[2]]
        path = unquote(address.path)
        if not re.fullmatch(rf"/sites/ir/financial-report/{year}/[^/]*", path) or "unconsolidated" in path.lower():
            raise ValueError("TSMC statement is outside the consolidated archive")
        if not path.lower().endswith(".pdf"):
            raise ValueError("Unsupported TSMC statement format")
        if (year, quarter) in releases and releases[year, quarter] != url:
            raise ValueError("Ambiguous TSMC statement for the same period")
        releases[year, quarter] = url
    if not releases:
        raise ValueError("No consolidated financial statement in TSMC's directory")
    return releases


def lines_from_pdf(body, stop_label="Wafer revenue $"):
    from pypdf import PdfReader
    from pypdf.constants import UserAccessPermissions
    from pypdf.errors import PyPdfError

    if not body.startswith(b"%PDF-") or len(body) > 25_000_000:
        raise ValueError("Invalid financial PDF")
    try:
        pdf = PdfReader(BytesIO(body))
        # Some public Toyota PDFs permit text extraction while restricting modifications.
        if pdf.is_encrypted and not (pdf.user_access_permissions and pdf.user_access_permissions & UserAccessPermissions.EXTRACT):
            raise ValueError("Document does not permit text extraction")
        if not 1 <= len(pdf.pages) <= 250:
            raise ValueError("Unsupported financial PDF")
        lines = []
        for page in pdf.pages:
            page_lines = [" ".join(line.split()) for line in page.extract_text(extraction_mode="layout").splitlines()]
            lines.extend(line for line in page_lines if line)
            if stop_label and any(line.startswith(stop_label) for line in page_lines):
                break
        return lines
    except (PyPdfError, IndexError, KeyError, UnicodeError) as exc:
        raise ValueError("Unreadable financial statement") from exc


def amounts(text, count):
    cells = text.replace("$", "").split()
    if len(cells) != count or not all(re.fullmatch(NUMBER, cell) for cell in cells):
        raise ValueError("Unexpected TSMC amount or column count")
    return [0 if cell == "-" else int(cell.replace(",", "")) for cell in cells]


def tsm_headings(year, q):
    month = 3 * q
    day = f"{month_name[month]} {monthrange(year, month)[1]}"
    durations = {1: ["Three Months"], 2: ["Three Months", "Six Months"],
                 3: ["Three Months", "Nine Months"], 4: ["Years"]}[q]
    headings = " ".join(label + " Ended " + day for label in durations)
    return headings, f"{year} {year-1}" + (f" {year} {year-1}" if len(durations) == 2 else "")


def table_block(lines, name, year, q):
    head, years = tsm_headings(year, q)
    positions = [i for i, line in enumerate(lines) if line == name + " " + years and i and lines[i-1] == head]
    if len(positions) != 1:
        raise ValueError(f"Missing or ambiguous TSMC {name} accounting periods")
    i = positions[0] + 1
    count = len(years.split())
    rows = {}
    named_rows = {"Platform": PLATFORMS, "Product": PRODUCTS}.get(name)
    for line in lines[i:i+35]:
        if named_rows is not None and line.startswith("$"):
            total = amounts(line, count)
            break
        if name == "Resolution" and line.startswith("Wafer revenue "):
            total = amounts(line[len("Wafer revenue "):], count)
            break
        if named_rows is not None:
            label = next((part for part in named_rows if line.startswith(part + " ")), None)
        else:
            match = re.match(rf"({NODE}) ", line)
            label = match[1] if match else None
        if not label or label in rows:
            raise ValueError("Unknown or duplicate TSMC row in " + name)
        rows[label] = amounts(line[len(label):], count)
    else:
        raise ValueError("No total for TSMC " + name)
    if (named_rows is not None and set(rows) != set(named_rows)) or not rows:
        raise ValueError("Incomplete TSMC breakdown")
    if any(sum(v[j] for v in rows.values()) != total[j] or total[j] <= 0 for j in range(count)):
        raise ValueError("TSMC breakdown and original printed total disagree")
    return rows, total


def make_table(name, raw, year, q, months, offset, source):
    month = 3*q
    periods = []
    for y in (year-1, year):
        start = date(y, month-months+1, 1)
        end = date(y, month, monthrange(y, month)[1])
        periods.append(dict(label=f"{y}.{month:02d}", labelEn=f"{y}.{month:02d}",
                            start=start.isoformat(), end=end.isoformat()))
    named_rows = {"Platform": PLATFORMS, "Product": PRODUCTS}.get(name)
    rows = []
    def millions(values):
        # All note amounts are in thousands of NT dollars; reverse issuer order to chronological.
        return [values[offset+1]/1000, values[offset]/1000]
    for label, values in raw[0].items():
        if named_rows is not None:
            key, ko = named_rows[label]
        else:
            key = "node-" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            ko = label.replace("-nanometer", "nm").replace(" micron", "μm").replace(" and above", " 이상")
        rows.append(dict(key=key, ko=ko, en=label, level=0, kind="leaf", parent=None, values=millions(values)))
    scope_ko, scope_en = HEADINGS[name]
    duration_ko, duration_en = ("연간","Full year") if months == 12 else (f"{months}개월", f"{months} months")
    return dict(id=f"tsmc-tw-{name.lower()}-{months}m", titleKo=f"{scope_ko} · {duration_ko}",
                titleEn=f"{scope_en} · {duration_en}", currency="TWD", unitKo="백만 대만달러", unitEn="TWD million",
                measure="revenue", periods=periods, rows=rows, total=millions(raw[1]), source=source,
                notes=["대만 연결재무제표 기준. 웨이퍼 매출은 연결 매출의 일부입니다."],
                notesEn=["Taiwan-basis consolidated statements. Wafer revenue is part of consolidated revenue."],
                marks=[], comparableFrom=periods[0]["label"], compositionKeys=[r["key"] for r in rows],
                compositionPeriods=[p["label"] for p in periods])


def tsm_statement(lines, year, q, url):
    text = " ".join(lines)
    if ("Taiwan Semiconductor Manufacturing Company Limited and Subsidiaries" not in text or
        "Amounts in Thousands of New Taiwan Dollars, Unless Specified Otherwise" not in text or
        "Disaggregation of revenue from contracts with customers" not in text):
        raise ValueError("TSMC identity, consolidated note or TWD unit not verified")
    auth = re.search(r"approved and authorized for issuance by the Board of Directors on "
                     r"([A-Z][a-z]+) (\d{1,2})\s*,\s*(\d{4})", text)
    if not auth:
        raise ValueError("No TSMC board authorization date")
    authorized = datetime.strptime(" ".join(auth.groups()), "%B %d %Y").date()
    fiscal_end = date(year, 3*q, monthrange(year, 3*q)[1])
    if not 0 < (authorized-fiscal_end).days <= 185 or authorized > date.today():
        raise ValueError("Invalid TSMC authorization date")
    platform = table_block(lines, "Platform", year, q)
    wafer = table_block(lines, "Resolution", year, q)
    product = table_block(lines, "Product", year, q)
    statement_lines = [line for line in lines if re.match(r"NET REVENUE \(Notes? [\d, and]+\) ", line)]
    if len(statement_lines) != 1:
        raise ValueError("No unambiguous TSMC consolidated net-revenue line")
    pairs = re.fullmatch(r"(?:\s*\$\s*([\d,]+) 100){1,4}", statement_lines[0].split(")", 1)[1])
    actual = [int(v.replace(",", "")) for v in re.findall(r"\$\s*([\d,]+)\s+100", statement_lines[0])]
    if not pairs or actual != platform[1] or actual != product[1] or wafer[1] != product[0]["Wafer"]:
        raise ValueError("TSMC consolidated and wafer revenue scopes cannot be reconciled")
    source = dict(label="TSMC 연결재무제표", labelEn="TSMC consolidated financial statements",
                  authorized=authorized.isoformat(), periodEnd=fiscal_end.isoformat(), url=url)
    # In a half-/nine-month report the right-hand pair is cumulative and the left-hand pair quarterly.
    spans = [(3*q, 2), (3, 0)] if q in (2,3) else [(3*q, 0)]
    tables = [make_table(name, raw, year, q, months, offset, source) for months, offset in spans
              for name, raw in (("Platform", platform), ("Resolution", wafer), ("Product", product))]
    return source, tables


def toyota_listing(body):
    doc = html.fromstring(body)
    releases = {}
    for anchor in doc.xpath("//a[normalize-space(.)='Financial Summary']"):
        heading = anchor.xpath("ancestor::ul[1]/preceding-sibling::*[1][self::h3]")
        if not heading:
            continue
        title = " ".join(heading[0].text_content().split())
        m = re.fullmatch(r"FY(\d{4})(?: ([123])Q)? Financial Results \(([A-Z][a-z]+ \d+, \d{4})\)",title)
        if not m or int(m[1]) < 2023:
            continue
        fy, q, published = int(m[1]), int(m[2] or 4), datetime.strptime(m[3],"%B %d, %Y").date()
        url = urljoin(TOYOTA_INDEX, anchor.get("href"))
        if url != f"https://global.toyota/pages/global_toyota/ir/financial-results/{fy}_{q}q_summary_en.pdf":
            raise ValueError("Unexpected Toyota report link")
        if (fy, q) in releases and releases[fy,q] != (url, published):
            raise ValueError("Two different Toyota financial summaries for the same period")
        releases[fy,q] = (url, published)
    return releases, doc


def toyota_directory(fetch):
    releases, page = toyota_listing(fetch(TOYOTA_INDEX))
    archives = []
    for a in page.xpath("//a[@href]"):
        url = urljoin(TOYOTA_INDEX, a.get("href"))
        if not re.fullmatch(re.escape(TOYOTA_INDEX) + r"archives/\d+\.html",url):
            continue
        years = re.findall(r"FY(\d{4})", a.text_content())
        if len(years) == 2:
            archives.append((int(years[-1]),url))
    # The newest fiscal year lives on the main page, the prior full year moves to a linked archive.
    if not any(q == 4 for _,q in releases) and archives:
        archived, _ = toyota_listing(fetch(max(archives)[1]))
        for key, entry in archived.items():
            releases.setdefault(key, entry)
    if not releases:
        raise ValueError("Toyota financial results directory changed")
    return releases


def yen_cells(text, n):
    nums = text.split()
    if len(nums) != n:
        raise ValueError("Unexpected Toyota column count")
    result = []
    for num in nums:
        if num in {"－","—","–","-"}:
            result.append(0)
            continue
        if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+|\((?:\d+|\d{1,3}(?:,\d{3})+)\))",num):
            raise ValueError("Invalid yen amount in Toyota statement")
        result.append(-int(num[1:-1].replace(",","")) if num[0]=="(" else int(num.replace(",","")))
    return result


def toyota_statement(lines, fy, q, url, published):
    month = 3 if q == 4 else 3*q+3
    y = fy if q == 4 else fy-1
    cutoff = date(y,month,monthrange(y,month)[1])
    day = month_name[month] + " " + str(cutoff.day)
    start = date(fy-1,4,1)
    report_title = ("", " First Quarter", " Semi-Annual", " Third Quarter", "")[q]
    cover = " ".join(lines[:24])
    release_day = f"{month_name[published.month]} {published.day}, {published.year}"
    if not all(t in cover for t in ["TOYOTA MOTOR CORPORATION", "Code number : 7203", "IFRS",
        f"FY{fy}{report_title} Consolidated Financial Results", f"April 1, {start.year} through {day}, {y}",
        release_day+" Company name : Toyota Motor Corporation"]):
        raise ValueError("Toyota issuer, reporting period, accounting basis or publication date mismatch")
    if not cutoff < published <= date.today() or (published-cutoff).days > 120:
        raise ValueError("Invalid Toyota results publication date")
    duration = {1:"first quarter",2:"first half",3:"first nine months",4:"year"}[q]
    header = "Automotive services All other Amount Consolidated"
    positions = [i for i,line in enumerate(lines) if line == header]
    if len(positions) != 2:
        raise ValueError("Toyota reportable segment layout changed")
    sales, operating = [], []
    for col,i in enumerate(positions):
        actual_y = y-1+col
        caption = (("As of and for the year ended " if q==4 else f"For the {duration} ended ") +
                   f"{day}, {actual_y}" + ("" if q==4 else ":"))
        if lines[i-5:i] != [caption, "Yen in millions", "Inter-segment", "Elimination/", "Financial Unallocated"]:
            raise ValueError("Toyota segment columns or fiscal years changed")
        group = lines[i+1:i+10]
        ext = next((s for s in group if s.startswith("Revenues from external customers ")),None)
        op = next((s for s in group if re.match(r"Operating income(?: \(loss\))? [\d(]",s)),None)
        if not ext or not op:
            raise ValueError("Missing Toyota external sales or segment operating income")
        rev = yen_cells(ext.removeprefix("Revenues from external customers "),5)
        inc = yen_cells(re.sub(r"^Operating income(?: \(loss\))? ","",op),5)
        if rev[3] != 0 or min(rev) < 0 or abs(sum(rev[:4])-rev[4])>2 or abs(sum(inc[:4])-inc[4])>2:
            raise ValueError("Toyota printed totals and reported segments do not reconcile")
        sales.append(rev)
        operating.append(inc)
    captions = [i for i,l in enumerate(lines) if l.endswith("Sales revenues by location of external customers")]
    if len(captions)!=1:
        raise ValueError("No Toyota customer-geography table")
    idx = captions[0]
    geo_heading = ("For the years ended " if q==4 else f"For the {duration} ended ") + day + ","
    if lines[idx+1:idx+4] != ["Yen in millions", geo_heading, f"{y-1} {y}"]:
        raise ValueError("Toyota customer geography period changed")
    geo = []
    region_names = [("japan","일본","Japan"),("north-america","북미","North America"),("europe","유럽","Europe"),
                    ("asia","아시아","Asia"),("other","기타","Other"),("total","합계","Total")]
    for n, (_,_,name) in enumerate(region_names):
        line=lines[idx+4+n]
        if not line.startswith(name+" "):
            raise ValueError("Unexpected Toyota customer region")
        geo.append(yen_cells(line[len(name):],2))
    totals=[a[-1] for a in sales]
    op_totals=[a[-1] for a in operating]
    def printed(prefix, values):
        return prefix+" "+" ".join(f"{v:,}" if v>=0 else f"({-v:,})" for v in values) in lines
    if (totals!=geo[-1] or any(abs(sum(row[j] for row in geo[:-1])-t)>3 for j,t in enumerate(totals))
        or not printed("Total sales revenues",totals) or not printed("Operating income", op_totals)):
        raise ValueError("Toyota disaggregated data do not match the consolidated income statement")
    periods=[dict(label=f"FY{fy-1+i} · {q*3}개월",labelEn=f"FY{fy-1+i} · {q*3} months",
                  start=date(fy-2+i,4,1).isoformat(),end=date(y-1+i,month,cutoff.day).isoformat()) for i in (0,1)]
    src=dict(label="도요타 연결 실적 발표",labelEn="Toyota consolidated financial results",url=url,
             periodEnd=cutoff.isoformat(),published=published.isoformat())
    seg_names=[("auto","자동차","Automotive"),("finance","금융 서비스","Financial services"),("other","기타","All other")]
    def table(key,ko,en,names,rows,totals,revenue=True):
        return dict(id=f"toyota-ir-{key}-{q*3}m",titleKo=ko,titleEn=en,currency="JPY",unitKo="백만 엔",unitEn="JPY million",
                    measure="revenue" if revenue else "operating-income",periods=periods,source=src,
                    rows=[dict(key=k,ko=kr,en=eng,values=values,level=0,
                               kind="adjustment" if k=="adjustment" else "leaf",parent=None)
                          for (k,kr,eng),values in zip(names,rows)],total=totals,marks=[],
                    notes=["일부 항목의 합과 공시 합계에는 백만 엔 단위 반올림 차이가 있습니다."],
                    notesEn=["Components and reported totals may differ by rounding to millions of yen."],
                    comparableFrom=periods[0]["label"],compositionKeys=[k for k,_,_ in names] if revenue else [],
                    compositionPeriods=[p["label"] for p in periods] if revenue else [])
    return src,[
        table("segments","사업별 외부 고객 매출","External revenue by business",seg_names,
              [list(v) for v in zip(*sales)][:3],totals),
        table("geography","고객 소재지별 매출","Revenue by customer location",region_names[:-1],geo[:-1],totals),
        table("operating","사업별 영업이익 및 조정","Operating income by business and reconciliation",
              seg_names+[("adjustment","부문 간 제거·미배분","Eliminations and unallocated amounts")],
              [list(v) for v in zip(*operating)][:4],op_totals,False)]


def refresh_documents(report, cik, fetch_bytes):
    ticker = report["ticker"]
    if (ticker,int(cik)) not in {("TSM",1046179),("TM",1094517)}:
        raise ValueError("Unsupported international issuer")
    toyota = ticker=="TM"
    entries = toyota_directory(fetch_bytes) if toyota else tsm_listing(fetch_bytes(TSMC_ARCHIVE))
    prefix = "toyota-ir-" if toyota else "tsmc-tw-"
    output = deepcopy(report)
    latest, warnings = [], []
    for kind in ("annual", "interim"):
        try:
            candidates = [p for p in entries if (p[1] == 4) == (kind == "annual")]
            if not candidates:
                raise ValueError("No matching consolidated statement")
            year, q = max(candidates)
            if toyota:
                url, published = entries[year,q]
                source,tables = toyota_statement(lines_from_pdf(fetch_bytes(url), None), year,q,url,published)
            else:
                url = entries[year,q]
                source,tables = tsm_statement(lines_from_pdf(fetch_bytes(url)), year,q,url)
            old = output[kind]
            end = source["periodEnd"]
            if any(p.get("end","") > end for t in old for p in t["periods"]):
                raise ValueError("Issuer directory lags an existing statement")
            key = "published" if toyota else "authorized"
            if any(t["source"].get("periodEnd") == end and t["source"].get(key,"") > source[key] for t in old):
                raise ValueError("A later revision is already stored")
            # Retain prior filings, especially the international IFRS 20-F, alongside Taiwan-basis statements.
            # A refresh replaces only this feed's last set of comparable pairs in the same frequency.
            kept = [t for t in old if not t["id"].startswith(prefix)]
            for t in kept:
                if t["source"].get("url")==url and t["source"].get("periodEnd")==end:
                    t["source"]=source
            filed = [t for t in kept if t["source"].get("filed") and t["periods"][-1].get("end") == end]
            output[kind] = filed + tables + [t for t in kept if t not in filed]
            latest.append(dict(source, kind=kind))
        except ImportError as exc:
            raise RuntimeError("Issuer statement extraction requires pypdf") from exc
        except (IndexError, OSError, ValueError) as exc:
            warnings.append(f"{kind}-unavailable ({exc})")
    if not latest:
        raise ValueError("; ".join(warnings))
    return output, {"latest": latest, "warnings": warnings}


def twse_tsm_income(report, body):
    records = json.loads(body.decode("utf-8-sig"))
    if not isinstance(records, list) or not all(isinstance(r,dict) for r in records):
        raise ValueError("Unknown TWSE listed-company dataset format")
    records = [r for r in records if r.get("公司代號")=="2330"]
    if len(records)!=1 or records[0].get("公司名稱") not in {"台積電","台灣積體電路製造股份有限公司"}:
        raise ValueError("No unambiguous TSMC entry in the TWSE dataset")
    r=records[0]
    declared = r.get("出表日期","")
    if (not re.fullmatch(r"\d{7}",declared) or not re.fullmatch(r"\d{3}",r.get("年度","")) or
        not re.fullmatch(r"[1-4]",r.get("季別",""))):
        raise ValueError("Invalid TWSE reporting period")
    # Republic of China calendar. 出表日期 dates the exchange's dataset, not the issuer's filing.
    as_of=date(int(declared[:3])+1911,int(declared[3:5]),int(declared[5:]))
    year, q=int(r["年度"])+1911,int(r["季別"])
    end=date(year,q*3,monthrange(year,q*3)[1])
    if not end<as_of<=datetime.now(timezone(timedelta(hours=8))).date():
        raise ValueError("TWSE snapshot does not postdate its fiscal period")
    keys=[
        ("營業收入","sales","매출","Revenue"),("營業毛利（毛損）","gross","매출총이익","Gross profit"),
        ("營業利益（損失）","operating","영업이익","Operating income"),("稅前淨利（淨損）","pretax","법인세 차감 전 이익","Profit before tax"),
        ("本期淨利（淨損）","net","연결 순이익","Consolidated net income"),
        ("淨利（淨損）歸屬於母公司業主","parent-net","지배기업 소유주 귀속 순이익","Net income attributable to owners of the parent")]
    def amount(key):
        raw=r.get(key,"")
        if not isinstance(raw,str) or not re.fullmatch(r"-?\d+(?:\.\d{1,2})?",raw):
            raise ValueError("Missing TWSE income line "+key)
        return Decimal(raw)
    if (amount("營業收入")-amount("營業成本")!=amount("營業毛利（毛損）") or
        amount("稅前淨利（淨損）")-amount("所得稅費用（利益）")!=amount("繼續營業單位本期淨利（淨損）")):
        raise ValueError("TWSE income statement does not reconcile")
    kind="annual" if q==4 else "interim"
    cutoff=end.isoformat()
    if any(p.get("end","")>cutoff for t in report[kind] for p in t["periods"]):
        raise ValueError("TWSE dataset is older than published results")
    source=dict(label="대만증권거래소 상장사 연결 손익",labelEn="TWSE listed-company income statements",
                datasetAsOf=as_of.isoformat(),periodEnd=cutoff,url=TWSE_INCOME)
    per=dict(label=f"{year}년 {3*q}개월",labelEn=f"{year} · {3*q} months",start=date(year,1,1).isoformat(),end=cutoff)
    table_id=f"twse-tsm-income-{cutoff}"
    old=report[kind]
    if any(t["id"]==table_id and t["source"].get("datasetAsOf","")>source["datasetAsOf"] for t in old):
        raise ValueError("An updated TWSE dataset is already stored")
    table=dict(id=table_id,titleKo="연결 손익 · "+str(3*q)+"개월",titleEn="Consolidated income · "+str(3*q)+" months",
               currency="TWD",unitKo="백만 대만달러",unitEn="TWD million",measure="financial-results",periods=[per],
               rows=[dict(key=k,ko=ko,en=en,level=0,kind="leaf",parent=None,values=[float(amount(c)/1000)])
                     for c,k,ko,en in keys],total=None,marks=[],comparableFrom=per["label"],
               notes=["대만증권거래소의 일반 상장기업 누적 손익 자료에서 회사 코드 2330을 조회했습니다."],
               notesEn=["Year-to-date figures for issuer 2330 in the Taiwan Stock Exchange's industrial-company dataset."],
               compositionKeys=[],compositionPeriods=[],source=source)
    out=deepcopy(report)
    kept=[t for t in out[kind] if t["id"]!=table_id]
    current=[t for t in kept if t["periods"][-1].get("end")==cutoff]
    out[kind]=current+[table]+[t for t in kept if t not in current]
    return out,dict(source,kind=kind)


def refresh_international(report, cik, fetch_bytes):
    if report["ticker"]!="TSM" or int(cik)!=1046179:
        return refresh_documents(report,cik,fetch_bytes)
    try:
        current,status=refresh_documents(report,cik,fetch_bytes)
    except (OSError,ValueError) as exc:
        current,status=deepcopy(report),{"latest":[],"warnings":[f"TSMC issuer PDFs unavailable ({exc})"]}
    if len(status["latest"])==2:
        return current,status
    try:
        updated,exchange=twse_tsm_income(current,fetch_bytes(TWSE_INCOME))
        kind=exchange["kind"]
        if any(s["kind"]==kind for s in status["latest"]):
            return current,status
        status["latest"].append(exchange)
        other="interim" if kind=="annual" else "annual"
        if not any(s["kind"]==other for s in status["latest"]):
            status["warnings"].append(other+"-unavailable (TWSE open data carries only the latest fiscal period)")
        return updated,status
    except (OSError,ValueError) as exc:
        status["warnings"].append(f"TWSE income data unavailable ({exc})")
    if not status["latest"]:
        raise ValueError("; ".join(status["warnings"]))
    return current,status
