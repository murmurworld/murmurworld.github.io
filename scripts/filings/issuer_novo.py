"""Read reported sales from Novo Nordisk's own quarterly financial workbooks."""

import calendar
import re
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from urllib.parse import unquote, urljoin, urlsplit
from zipfile import BadZipFile, ZipFile

from lxml import html
from openpyxl import load_workbook

from issuer_native import financial_table

HOST = "www.novonordisk.com"
INDEX = "https://" + HOST + "/investors/financial-results.html"
DATE = r"\b(\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) 20\d\d)\b"
INCOME_ROWS = {
    "Net sales": "순매출",
    "Gross profit": "매출총이익",
    "Operating profit": "영업이익",
    "NET PROFIT": "순이익",
}
PRODUCTS = {
    "wegovy": "위고비",
    "wegovy injectable": "위고비 주사제",
    "wegovy pill": "위고비 정제",
    "saxenda": "삭센다",
    "ozempic": "오젬픽 주사제",
    "victoza": "빅토자",
    "rybelsus": "리벨서스",
    "ozempic pill / rybelsus": "오젬픽 정제·리벨서스",
    "total insulin": "인슐린 제품 합계",
}


def discover(raw):
    tree = html.fromstring(raw)
    candidates = {}
    for link in tree.xpath("//a[@href]"):
        label = " ".join(link.text_content().lower().split())
        if "financial workbook" not in label or "xlsx" not in label:
            continue
        address = urlsplit(urljoin(INDEX, link.get("href")))
        name = unquote(address.path).rsplit("/", 1)[-1]
        match = re.search(r"\bQ([1-4])[- _]+(20\d{2})\b", name, re.I)
        if (
            not match
            or not name.lower().endswith(".xlsx")
            or address.hostname != HOST
            or address.scheme != "https"
            or not address.path.startswith("/content/dam/nncorp/")
        ):
            continue
        year, quarter = int(match[2]), int(match[1])
        end = period_end(year, quarter)
        # Find the nearest dated results heading above this workbook, rather than a webcast date.
        previous = link.xpath("preceding::p[not(.//a)][position()<=5]")
        for element in reversed(previous):
            words = " ".join(element.text_content().split())
            hit = re.search(DATE, words)
            if not hit:
                continue
            published = datetime.strptime(hit[1], "%d %B %Y").date()
            if not 0 < (published - end).days <= 95 or published > date.today():
                break
            value = published, address.geturl()
            if (year, quarter) in candidates and candidates[year, quarter] != value:
                raise ValueError("Conflicting dates or files in Novo Nordisk's results directory")
            candidates[year, quarter] = value
            break
    return candidates


def period_end(year, quarter):
    month = quarter * 3
    return date(year, month, calendar.monthrange(year, month)[1])


def million(cell):
    # Some Excel editions store DKK millions, others store whole kroner with
    # two scaling commas in the display format. Both show the same printed unit.
    fmt = cell.number_format.split(";")[0].strip()
    scale = re.fullmatch(r"(?:\*\s*)?#,##0(,,)?", fmt)
    if not scale or not isinstance(cell.value, (float, int)) or isinstance(cell.value, bool):
        raise ValueError("Unrecognised DKK display format or missing financial figure")
    number = Decimal(str(cell.value)) / (1_000_000 if scale[1] else 1)
    if number != number.to_integral_value():
        raise ValueError("Expected a whole number of DKK millions")
    return int(number)


def table(identifier, titles, periods, source, rows, total=None):
    item = financial_table("novo-" + identifier, titles, periods, source, rows)
    item.update(currency="DKK", unitEn="DKK million", unitKo="백만 덴마크 크로네")
    if total is not None:
        item.update(
            measure="revenue",
            total=total,
            compositionKeys=[k[0] for k, _ in rows],
            compositionPeriods=[p["label"] for p in periods],
        )
    return item


def reported_products(book, scope, header, periods, source, net_sales):
    suffix = "Q" if scope == "quarter" else "YTD"
    # The 2026 workbooks explicitly reconcile adjusted to reported sales. Only
    # the column headed "reported sales" corresponds to the IFRS income statement.
    reconciled = "Sales IFRS reconciliation - " + suffix
    if reconciled not in book and scope == "quarter" and "Sales IFRS reconciliation" in book:
        reconciled = "Sales IFRS reconciliation"
    if reconciled in book:
        rows = list(book[reconciled].iter_rows(max_row=80, max_col=5))
        if " ".join(str(rows[2][2].value).lower().split()) != header.lower() + " reported sales":
            raise ValueError("Missing reported product sales for the stated period")
        col = 2
    else:
        rows = list(book["Sales - " + suffix].iter_rows(max_row=85, max_col=5))
        if (
            rows[1][0].value != header + " sales split per area"
            or rows[3][0].value != "DKK million"
            or rows[3][3].value != "Total"
        ):
            raise ValueError("Unknown product sales period or unit")
        col = 3
    figures = []
    total = None
    for row in rows:
        names = [cell.value for cell in row[:col] if isinstance(cell.value, str)]
        if not names:
            continue
        name = " ".join(names[-1].strip().lstrip("- ").replace("®", "").split())
        if name.lower() == "total sales":
            total = million(row[col])
        if name.lower() in PRODUCTS:
            figures.append(((name.lower(), PRODUCTS[name.lower()], name), [million(row[col])]))
    if total != net_sales or len(figures) < 5 or len({r[0][0] for r in figures}) != len(figures):
        raise ValueError("Product sheet does not reconcile to reported IFRS net sales")
    item = table(
        "products-" + scope, ("주요 제품 매출", "Selected product sales"), [periods[-1]], source, figures
    )
    item["measure"] = "revenue"
    item["notes"] = [
        "전 세계 공시 매출입니다. 위고비의 주사제와 정제는 회사가 따로 공개한 기간부터 구분했습니다."
    ]
    item["notesEn"] = [
        "Worldwide reported sales. Injectable and oral Wegovy are separated when the company reports them individually."
    ]
    return item


def fourth_quarter(book, year, source):
    rows = list(book["Quarterly numbers"].iter_rows(max_row=38, max_col=12))
    if (
        "DKK million" not in str(rows[1][0].value)
        or [str(rows[3][col].value) for col in (6, 1)] != [str(year - 1), str(year)]
        or any(rows[4][col].value != "Q4" for col in (6, 1))
    ):
        raise ValueError("Unrecognised fourth-quarter income heading")
    labels = {
        "Net sales": "순매출",
        "Gross profit": "매출총이익",
        "Operating profit (EBIT)": "영업이익",
        "Net profit": "순이익",
    }
    figures = [
        ((row[0].value.lower(), labels[row[0].value], row[0].value), [million(row[6]), million(row[1])])
        for row in rows
        if row[0].value in labels
    ]
    if len(figures) != len(labels) or figures[0][0][0] != "net sales":
        raise ValueError("Incomplete fourth-quarter income statement")
    periods = [
        dict(
            start=f"{y}-10-01",
            end=f"{y}-12-31",
            label=f"{y}-12-31 종료 3개월",
            labelEn=f"3 months to {y}-12-31",
        )
        for y in (year - 1, year)
    ]
    income = table("income-quarter", ("연결 손익", "Consolidated income"), periods, source, figures)
    products = reported_products(book, "quarter", f"Q4 {year}", periods, source, figures[0][1][-1])
    return [income, products]


def read_workbook(raw, year, quarter, published, url, section):
    if not raw.startswith(b"PK") or len(raw) > 8_000_000:
        raise ValueError("Invalid issuer workbook")
    with ZipFile(BytesIO(raw)) as archive:
        if sum(item.file_size for item in archive.infolist()) > 30_000_000:
            raise ValueError("Issuer workbook exceeds supported size")
    book = load_workbook(BytesIO(raw), read_only=True, data_only=True, keep_links=False)
    try:
        end = period_end(year, quarter)
        source = dict(
            label="노보 노디스크 재무 워크북",
            labelEn="Novo Nordisk financial workbook",
            published=published.isoformat(),
            periodEnd=end.isoformat(),
            url=url,
        )
        if section == "interim" and quarter == 4:
            return source, fourth_quarter(book, year, source)
        rows = list(book["IS & OCI"].iter_rows(max_row=60, max_col=12))
        headings = rows[2]
        if headings[0].value != "DKK million":
            raise ValueError("Missing DKK millions unit")
        net_rows = {}
        segment_rows = []
        in_segments = False
        for row in rows:
            name = str(row[0].value or "").strip()
            if name == "Segment operating profit:":
                in_segments = False
            if in_segments and name:
                segment_rows.append((re.sub(r"\d+$", "", name).strip(), row))
            if name == "Segment sales:":
                in_segments = True
            if name in INCOME_ROWS:
                net_rows[name] = row
        if set(net_rows) != set(INCOME_ROWS) or len(segment_rows) != 2:
            raise ValueError("Missing sales, income or segment breakdown")
        columns = {str(c.value): j for j, c in enumerate(headings) if c.value is not None}
        scopes = (
            [("annual", "{y}", 1)]
            if quarter == 4
            else [("quarter", "Q" + str(quarter) + " {y}", end.month - 2)]
        )
        if quarter in [2, 3]:
            scopes.append(("ytd", ("H1" if quarter == 2 else "9M") + " {y}", 1))
        built = []
        for scope, pattern, start_month in scopes:
            labels = [pattern.format(y=y) for y in (year - 1, year)]
            if any(label not in columns for label in labels):
                # Older interim workbooks sometimes print only YTD; process exactly what is present.
                if scope == "quarter" and quarter in (2, 3):
                    continue
                raise ValueError("No comparable figures for this period")
            ids = [columns[label] for label in labels]
            periods = []
            for y in (year - 1, year):
                finish = period_end(y, quarter).isoformat()
                n = end.month - start_month + 1
                periods.append(
                    dict(
                        start=date(y, start_month, 1).isoformat(),
                        end=finish,
                        label=f"{finish} 종료 {n}개월",
                        labelEn=f"{n} months to {finish}",
                    )
                )
            pair = lambda row: [million(row[i]) for i in ids]
            sales = pair(net_rows["Net sales"])
            segments = []
            for name, row in segment_rows:
                if name in ("Obesity and Diabetes", "Obesity and Diabetes care"):
                    ko = "비만·당뇨병 치료"
                elif name in ("Rare disease", "Blood & endocrine disorders"):
                    ko = "희귀질환" if name == "Rare disease" else "혈액·내분비 질환"
                else:
                    raise ValueError("Unknown Novo Nordisk operating segment")
                segments.append(((name.lower(), ko, name), pair(row)))
            if [sum(cols) for cols in zip(*(values for _, values in segments))] != sales:
                raise ValueError("Reported operating segments do not reconcile")
            built.append(
                table(
                    "segments-" + scope,
                    ("치료 사업별 매출", "Revenue by therapy business"),
                    periods,
                    source,
                    segments,
                    sales,
                )
            )
            built.append(reported_products(book, scope, labels[-1], periods, source, sales[-1]))
            built.append(
                table(
                    "income-" + scope,
                    ("연결 손익", "Consolidated income"),
                    periods,
                    source,
                    [
                        ((name.lower(), ko, name.title() if name.isupper() else name), pair(net_rows[name]))
                        for name, ko in INCOME_ROWS.items()
                    ],
                )
            )
        return source, built
    finally:
        book.close()


def refresh_novo(report, cik, fetch):
    if report["ticker"] != "NVO" or cik != 353278:
        raise ValueError("Unexpected Novo Nordisk issuer identity")
    entries = discover(fetch(INDEX))
    output = deepcopy(report)
    latest, warnings = [], []
    for section in ("annual", "interim"):
        try:
            key = max(k for k in entries if section == "interim" or k[1] == 4)
            published, url = entries[key]
            source, tables = read_workbook(fetch(url), *key, published, url, section)
            previous = report[section]
            if any(p["end"] > source["periodEnd"] for t in previous for p in t["periods"]):
                raise ValueError("A more recent statement is already available")
            output[section] = tables + [t for t in previous if not t["id"].startswith("novo-")]
            latest.append({**source, "kind": section})
        except (KeyError, ValueError, OSError, IndexError, BadZipFile) as e:
            warnings.append(f"{section}-unavailable ({e})")
    if not latest:
        raise ValueError("; ".join(warnings))
    return output, {"latest": latest, "warnings": warnings}
