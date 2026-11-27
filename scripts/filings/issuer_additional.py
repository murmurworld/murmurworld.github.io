"""GAAP results published in US issuers' own earnings archives."""

from calendar import monthrange
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
import json
import re
from urllib.parse import urljoin, urlsplit
from urllib.error import HTTPError
from zipfile import BadZipFile, ZipFile

from lxml import etree, html

from issuer_international import lines_from_pdf

COP_INDEX = "https://www.conocophillips.com/investor-relations/investor-presentations/earnings-archive/"
HD_INDEX = "https://ir.homedepot.com/financial-reports/quarterly-earnings"
JPM_INDEX = "https://www.jpmorganchase.com/services/json/v1/investor-relations/quarterly-earnings.json"
ADDITIONAL_HOSTS = {
    "www.conocophillips.com",
    "static.conocophillips.com",
    "ir.homedepot.com",
    "www.jpmorganchase.com",
}
ADDITIONAL_TICKERS = {"COP", "HD", "JPM"}
ORDINAL = ["First", "Second", "Third", "Fourth"]
QUARTER_COLUMNS = ["1st Qtr", "2nd Qtr", "3rd Qtr", "4th Qtr"]
SHEET = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
OFFICE_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
COP_SEGMENTS = {
    "Alaska": "알래스카",
    "Lower 48": "미국 본토 48개 주",
    "Canada": "캐나다",
    "Europe, Middle East and North Africa": "유럽·중동·북아프리카",
    "Asia Pacific": "아시아태평양",
    "Corporate and Other": "본사·기타",
}
COP_INCOME = {
    "Sales and other operating revenues": "매출 및 기타 영업수익",
    "Equity in earnings of affiliates": "관계기업 지분법이익",
    "Gain (loss) on dispositions": "자산처분손익",
    "Other income": "기타수익",
}


def single(values, description):
    if len(values) != 1:
        raise ValueError("Missing or ambiguous " + description)
    return values[0]


def cop_directory(raw):
    doc = html.fromstring(raw)
    releases = {}
    for tr in doc.xpath("//tr"):
        cells = tr.xpath("./td")
        if len(cells) < 5:
            continue
        match = re.fullmatch(
            r"(First|Second|Third|Fourth)-Quarter (20\d\d)", cells[0].text_content().strip()
        )
        if not match or int(match[2]) < 2023:
            continue
        year, q = int(match[2]), ORDINAL.index(match[1]) + 1

        def document(cell, suffix):
            urls = [s for s in cell.xpath(".//a/@href") if s.lower().endswith(suffix)]
            # Recent archives include spreadsheets; historical rows may carry PDFs only.
            if not urls:
                return None
            url = single(urls, "ConocoPhillips " + suffix + " attachment")
            address = urlsplit(url)
            if (
                address.scheme != "https"
                or address.netloc != "static.conocophillips.com"
                or not address.path.startswith("/files/resources/")
                or address.query
                or address.fragment
            ):
                raise ValueError("Unexpected ConocoPhillips attachment location")
            return url

        refs = (document(cells[1], ".pdf"), document(cells[4], ".xlsx"), document(cells[4], ".pdf"))
        if (year, q) in releases:
            raise ValueError("Duplicate corporate earnings period")
        releases[year, q] = refs
    return releases


def sheet_cells(raw, sheet_name, max_rows):
    """Read stored values only. Never execute worksheet formulas or resolve external links."""
    try:
        with ZipFile(BytesIO(raw)) as z:

            def xml(part):
                if z.getinfo(part).file_size > 20_000_000:
                    raise ValueError("Financial worksheet too large")
                return etree.fromstring(
                    z.read(part), etree.XMLParser(resolve_entities=False, no_network=True)
                )

            sheets = xml("xl/workbook.xml").findall(".//" + SHEET + "sheet")
            sheet = single([s for s in sheets if s.get("name") == sheet_name], "financial worksheet")
            rel_id = sheet.get(OFFICE_REL + "id")
            rels = xml("xl/_rels/workbook.xml.rels")
            rel = single([r for r in rels if r.get("Id") == rel_id], "financial worksheet reference")
            target = rel.get("Target", "")
            if rel.get("TargetMode") == "External" or not re.fullmatch(
                r"(?:/xl/)?worksheets/sheet\d+\.xml", target
            ):
                raise ValueError("Unrecognised financial worksheet path")
            strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                strings = [
                    "".join(s.itertext()).strip() for s in xml("xl/sharedStrings.xml").findall(SHEET + "si")
                ]
            result = []
            for row in xml(target[1:] if target.startswith("/") else "xl/" + target).iter(SHEET + "row"):
                if int(row.get("r")) > max_rows:
                    break
                values = {}
                for cell in row.findall(SHEET + "c"):
                    value = cell.findtext(SHEET + "v")
                    cell_type = cell.get("t", "n")
                    if cell_type == "inlineStr":
                        value = "".join(cell.itertext()).strip()
                    elif value is None:
                        continue
                    elif cell_type == "s":
                        value = strings[int(value)]
                    elif cell_type == "n":
                        number = Decimal(value)
                        if not number.is_finite():
                            raise ValueError("Nonfinite financial value")
                        value = number
                    else:
                        continue
                    column = re.fullmatch(r"([A-Z]+)\d+", cell.get("r", ""))[1]
                    values[column] = value
                result.append(values)
            return result
    except (BadZipFile, KeyError, IndexError, TypeError, InvalidOperation, etree.XMLSyntaxError) as exc:
        raise ValueError("Unreadable issuer workbook") from exc


def row_key(label):
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def result_table(identifier, title_ko, title_en, measure, labels, rows, periods, total, source, notes):
    records = [
        dict(key=row_key(label), ko=ko, en=label, values=rows[label], parent=None, level=0, kind="leaf")
        for label, ko in labels.items()
    ]
    return dict(
        id=identifier,
        titleKo=title_ko,
        titleEn=title_en,
        measure=measure,
        currency="USD",
        unitKo="백만 달러",
        unitEn="USD million",
        periods=periods,
        rows=records,
        total=total,
        source=source,
        comparableFrom=periods[0]["label"],
        marks=[],
        compositionKeys=[],
        compositionPeriods=[],
        notes=[notes[0]],
        notesEn=[notes[1]],
    )


def cop_financials(sheet, year, q, source):
    descriptor = f"{ORDINAL[q-1]}-Quarter {year} Detailed Supplemental Information"
    if not any(descriptor in row.values() for row in sheet[:6]):
        raise ValueError("Wrong ConocoPhillips supplement period")

    def section(title, unit, last):
        i = single([n for n, r in enumerate(sheet) if r.get("B") == title], "GAAP section " + title)
        if (
            i < 3
            or sheet[i - 1].get("B") != unit
            or sheet[i - 3].get("D") != year - 1
            or sheet[i - 3].get("J") != year
        ):
            raise ValueError("Wrong fiscal year or USD unit for " + title)
        expected = QUARTER_COLUMNS + ["Full Year"] + QUARTER_COLUMNS + ["Full Year" if q == 4 else "YTD"]
        if [sheet[i - 2].get(c) for c in "DEFGHJKLMN"] != expected:
            raise ValueError("Unknown columns in " + title)
        result = {}
        for row in sheet[i + 1 :]:
            label = str(row.get("B", "")).strip()
            if not label:
                continue
            if label in result:
                raise ValueError("Ambiguous GAAP line in " + title)
            result[label] = row
            if label == last:
                return result
        raise ValueError("No total for " + title)

    income = section(
        "CONSOLIDATED INCOME STATEMENT", "$ Millions, Except as Indicated", "Net income (loss)"
    )
    segments = section("EARNINGS BY SEGMENT", "$ Millions", "Consolidated")
    if set(segments) != set(COP_SEGMENTS) | {"Consolidated"}:
        raise ValueError("Unrecognised GAAP operating segment")
    modes = (
        [("annual", [("H", year - 1), ("N", year)], 1)]
        if q == 4
        else [("quarter", [("DEFG"[q - 1], year - 1), ("JKLM"[q - 1], year)], 3 * q - 2)]
    )
    if 1 < q < 4:
        modes.append(("ytd", [("N", year)], 1))
    tables = []
    for mode, columns, start_month in modes:

        def vector(rows, label):
            cells = [rows.get(label, {}).get(column) for column, _ in columns]
            if any(not isinstance(v, Decimal) or v != v.to_integral_value() for v in cells):
                raise ValueError("Missing or non-integer GAAP amount for " + label)
            return [int(v) for v in cells]

        earnings = {label: vector(segments, label) for label in COP_SEGMENTS}
        revenues = {label: vector(income, label) for label in COP_INCOME}
        total = vector(income, "Total revenues and other income")
        net = vector(income, "Net income (loss)")
        tax = vector(income, "Income tax provision (benefit)")
        pretax = vector(income, "Income (loss) before income taxes")
        costs = vector(income, "Total costs and expenses")
        if (
            vector(segments, "Consolidated") != net
            or [sum(v) for v in zip(*earnings.values())] != net
            or [sum(v) for v in zip(*revenues.values())] != total
            or [a - b for a, b in zip(total, costs)] != pretax
            or [a - b for a, b in zip(pretax, tax)] != net
        ):
            raise ValueError("ConocoPhillips original GAAP totals do not reconcile")
        periods = []
        for _, y in columns:
            end = date(y, 3 * q, monthrange(y, 3 * q)[1]).isoformat()
            periods.append(
                dict(start=date(y, start_month, 1).isoformat(), end=end, label=end[:7], labelEn=end[:7])
            )
        tk, te = {
            "annual": ("연간", "Full year"),
            "quarter": ("분기", "Quarter"),
            "ytd": ("연초 이후 누적", "Year to date"),
        }[mode]
        tables.extend(
            (
                result_table(
                    "cop-ir-segment-" + mode,
                    "사업부문별 순이익 · " + tk,
                    "Net earnings by segment · " + te,
                    "net-income",
                    COP_SEGMENTS,
                    earnings,
                    periods,
                    net,
                    source,
                    (
                        "각 지역의 세후이익과 본사·기타의 합계입니다.",
                        "Regional after-tax earnings and Corporate and Other reconcile to consolidated net income.",
                    ),
                ),
                result_table(
                    "cop-ir-income-" + mode,
                    "매출과 기타수익 · " + tk,
                    "Revenues and other income · " + te,
                    "financial-results",
                    COP_INCOME,
                    revenues,
                    periods,
                    total,
                    source,
                    (
                        "매출 외에 관계기업 이익, 자산처분손익, 기타수익이 포함됩니다.",
                        "Total includes operating revenues, equity earnings, gains or losses on dispositions, and other income.",
                    ),
                ),
            )
        )
    return tables


def cop_publication_date(release):
    matches = re.findall(
        r"(?:news release\s+|houston\s*[–—-]+\s*)([a-z]+)\.? (\d{1,2}), (20\d\d)", release.lower()
    )
    dates = {
        datetime.strptime(" ".join([month[:3], day, year]), "%b %d %Y").date()
        for month, day, year in matches
    }
    return single(sorted(dates), "ConocoPhillips release publication date")


def cop_statement(refs, year, q, fetch):
    release_url, xlsx_url, supplement_url = refs
    if not all(refs):
        raise ValueError("Issuer has not posted all original documents for this period")
    release = " ".join(lines_from_pdf(fetch(release_url), "HOUSTON")[:45]).lower()
    token = f"{ORDINAL[q-1].lower()}-quarter {year}"
    if not all(s in release for s in ("conocophillips (nyse: cop)", token, "news release")):
        raise ValueError("ConocoPhillips identity or release quarter mismatch")
    published = cop_publication_date(release)
    end = date(year, q * 3, monthrange(year, q * 3)[1])
    if not end < published <= date.today() or (published - end).days > 125:
        raise ValueError("ConocoPhillips publication date outside reporting window")
    source = dict(
        label="코노코필립스 분기 실적 보충자료",
        labelEn="ConocoPhillips detailed earnings supplement",
        url=supplement_url,
        periodEnd=end.isoformat(),
        published=published.isoformat(),
        dataUrl=xlsx_url,
        releaseUrl=release_url,
    )
    sheet = sheet_cells(fetch(xlsx_url), "Display (Values)", 240)
    return source, cop_financials(sheet, year, q, source)


HD_PRODUCTS = {
    "Building Materials": "건축자재",
    "Décor": "인테리어·가전",
    "Hardlines": "공구·정원용품 등",
    "Other net sales": "기타 사업 매출",
}
HD_ROWS = {
    "Net sales": "순매출",
    "Gross profit": "매출총이익",
    "Operating income": "영업이익",
    "Earnings before provision for income taxes": "법인세비용 차감 전 이익",
    "Net earnings": "순이익",
}
MONTH_DAY = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}"
)


def hd_directory(fetch):
    entries = {}

    def scan(raw):
        doc = html.fromstring(raw)
        for tr in doc.xpath("//tr"):
            cells = tr.xpath("./td")
            if len(cells) < 3 or not re.fullmatch(r"Q[1-4]", cells[0].text_content().strip()):
                continue
            q = int(cells[0].text_content().strip()[1])
            releases = [urljoin(HD_INDEX, h) for h in cells[1].xpath(".//a/@href")]
            if not releases:
                continue
            release = single(releases, "Home Depot earnings release")
            m = re.fullmatch(
                r"https://ir\.homedepot\.com/~/media/Files/H/HomeDepot-IR/press-release/q([1-4])-(20\d\d)-earnings-release\.pdf",
                release,
                re.I,
            )
            if not m or int(m[1]) != q:
                raise ValueError("Unrecognised Home Depot press release")
            yr = int(m[2])
            filings = [urljoin(HD_INDEX, h) for h in cells[2].xpath(".//a/@href")]
            filing = single(filings, "Home Depot report") if filings else None
            if filing and not re.fullmatch(
                rf"https://ir\.homedepot\.com/~/media/Files/H/HomeDepot-IR/reports-and-presentations/quarterly-earnings/{yr}/[^/]*10-?{'k' if q==4 else 'q'}\.pdf",
                filing,
                re.I,
            ):
                raise ValueError("Unexpected Home Depot report or form")
            entries[yr, q] = (release, filing)
        return doc

    # The archive publishes a separate canonical URL for each fiscal year. Its undated alias redirects.
    # Requesting the canonical page directly keeps the same transparent publisher identification.
    year = date.today().year
    try:
        doc = scan(fetch(f"{HD_INDEX}/{year}"))
    except HTTPError as exc:
        if exc.code != 404:
            raise
        doc = scan(fetch(f"{HD_INDEX}/{year-1}"))
    if not any(q == 4 for _, q in entries):
        previous = (max(entries)[0] if entries else year) - 1
        prev = HD_INDEX + "/" + str(previous)
        if any(
            urljoin(HD_INDEX, a.get("href")) == prev and a.text_content().strip() == str(previous)
            for a in doc.xpath("//a[@href]")
        ):
            scan(fetch(prev))
    return entries


def hd_year_end(fiscal_year):
    # Fiscal year ends on the Sunday nearest January 31, including 53-week years.
    jan31 = date(fiscal_year + 1, 1, 31)
    return jan31 + timedelta(days=(6 - jan31.weekday() + 3) % 7 - 3)


def hd_periods(year, q, mode):
    periods = []
    for fy in (year - 1, year):
        first = hd_year_end(fy - 1) + timedelta(days=1)
        start = first + timedelta(weeks=13 * (q - 1)) if mode == "quarter" else first
        end = hd_year_end(fy) if q == 4 else first + timedelta(weeks=13 * q, days=-1)
        periods.append(
            dict(
                start=start.isoformat(), end=end.isoformat(), label=end.isoformat(), labelEn=end.isoformat()
            )
        )
    return periods


def hd_amount(cell):
    if cell in {"—", "–", "-"}:
        return 0
    if not re.fullmatch(r"\(?\d+(?:,\d{3})*\)?", cell) or cell.startswith("(") != cell.endswith(")"):
        raise ValueError("Invalid Home Depot dollar amount")
    return (-1 if cell.startswith("(") else 1) * int(cell.strip("()").replace(",", ""))


def hd_press(lines, year, q, url):
    headline = " ".join(lines[:6])
    if (
        f"The Home Depot Announces {ORDINAL[q-1]} Quarter" not in headline
        or f"Fiscal {year} Results" not in headline
    ):
        raise ValueError("Home Depot quarter or issuer does not match the earnings archive")
    stamp = re.search(r"ATLANTA, (" + MONTH_DAY + r", 20\d\d)", headline)
    if not stamp:
        raise ValueError("Missing Home Depot release date")
    published = datetime.strptime(stamp[1], "%B %d, %Y").date()
    start = single(
        [i for i, l in enumerate(lines) if l == "CONDENSED CONSOLIDATED STATEMENTS OF EARNINGS"],
        "GAAP earnings statement",
    )
    i = next(
        (i for i, l in enumerate(lines[start + 1 : start + 12], start + 1) if l.startswith("Net sales ")),
        None,
    )
    if i is None:
        raise ValueError("Missing consolidated net sales")
    heading = " ".join(lines[start:i])
    time_title = {
        1: "Three Months Ended",
        2: "Six Months Ended",
        3: "Nine Months Ended",
        4: "Fiscal Year Ended",
    }[q]
    if not all(
        s in heading for s in ("in millions, except per share data", "Three Months Ended", time_title)
    ):
        raise ValueError("Unrecognised earnings units or time span")
    ends = [date.fromisoformat(p["end"]) for p in reversed(hd_periods(year, q, "annual"))]
    times = 1 if q == 1 else 2
    if re.findall(MONTH_DAY, heading) != [f"{d.strftime('%B')} {d.day}" for d in ends] * times:
        raise ValueError("Unverified retail fiscal calendar")
    if re.findall(r"\b20\d\d\b", heading) != [str(d.year) for d in ends] * times:
        raise ValueError("Wrong retail fiscal year")
    if not ends[0] < published <= date.today() or (published - ends[0]).days > 110:
        raise ValueError("Home Depot press date outside reporting window")
    source = dict(
        label="홈디포 실적 발표",
        labelEn="Home Depot earnings release",
        url=url,
        periodEnd=ends[0].isoformat(),
        published=published.isoformat(),
    )
    metrics = {}
    for label in list(HD_ROWS) + [
        "Cost of sales",
        "Total operating expenses",
        "Interest and other, net",
        "Provision for income taxes",
    ]:
        found = single([l[len(label) + 1 :] for l in lines[i : i + 25] if l.startswith(label + " ")], label)
        fields = found.replace("$", "").replace("%", "").split()
        if len(fields) != 3 * times:
            raise ValueError("Inconsistent earnings or change columns for " + label)
        metrics[label] = [hd_amount(n) for j, n in enumerate(fields) if j % 3 != 2]
    for bigger, subtract, smaller in (
        ("Net sales", "Cost of sales", "Gross profit"),
        ("Gross profit", "Total operating expenses", "Operating income"),
        ("Operating income", "Interest and other, net", "Earnings before provision for income taxes"),
        ("Earnings before provision for income taxes", "Provision for income taxes", "Net earnings"),
    ):
        if [a - b for a, b in zip(metrics[bigger], metrics[subtract])] != metrics[smaller]:
            raise ValueError("Printed Home Depot financial results do not reconcile")
    return source, metrics


def hd_product_note(lines, year, q, url, metrics):
    form = "10-K" if q == 4 else "10-Q"
    fiscal = f"Fiscal {year} Form {form}" if q == 4 else f"Fiscal Q{q} {year} Form {form}"
    if not any(fiscal in l for l in lines):
        raise ValueError("Home Depot original report does not match the fiscal year, quarter or form")
    signed = single([i for i, l in enumerate(lines) if l == "SIGNATURES"], "report signature")
    signature = " ".join(lines[signed : signed + 19])
    stamp = re.search(r"Date: (" + MONTH_DAY + r", 20\d\d)", signature)
    if "THE HOME DEPOT, INC." not in signature or not stamp:
        raise ValueError("Home Depot signature not found")
    signature_date = datetime.strptime(stamp[1], "%B %d, %Y").date()
    end = date.fromisoformat(hd_periods(year, q, "annual")[-1]["end"])
    if not end < signature_date <= date.today() or (signature_date - end).days > 140:
        raise ValueError("HD signature date outside reporting window")
    a = single(
        [
            i
            for i, l in enumerate(lines)
            if l.startswith("The following table presents net sales by major product line")
            and "Other net sales" in l
        ],
        "product note",
    )
    b = next(
        (i for i, l in enumerate(lines[a + 1 : a + 10], a + 1) if l.startswith("Building Materials $")),
        None,
    )
    if b is None:
        raise ValueError("Missing Home Depot major product table")
    heading = " ".join(lines[a + 1 : b])
    if "in millions" not in heading:
        raise ValueError("No amount units on product table")
    count = {1: 2, 2: 4, 3: 4, 4: 3}[q]
    if q == 4:
        if re.findall(r"\b20\d\d\b", heading) != [str(year - j) for j in range(count)]:
            raise ValueError("Annual product note has different periods")
    else:
        dates = re.findall(r"(" + MONTH_DAY + r"),\s*(20\d\d)", heading)
        cells = [datetime.strptime(f"{s} {y}", "%B %d %Y").date().isoformat() for s, y in dates]
        if cells != [p["end"] for p in reversed(hd_periods(year, q, "quarter"))] * (count // 2):
            raise ValueError("Product note has different comparison periods")
    rows = {}
    for label in [*HD_PRODUCTS, "Primary segment net sales", "Net sales"]:
        line = single([l for l in lines[b : b + 6] if l.startswith(label + " ")], label)
        amounts = re.sub(r"^\s*\(1\)\s*", "", line[len(label) :]).replace("$", "").split()
        if len(amounts) != count:
            raise ValueError("Unexpected product note columns")
        rows[label] = list(map(hd_amount, amounts))
    if [sum(v) for v in zip(rows["Building Materials"], rows["Décor"], rows["Hardlines"])] != rows[
        "Primary segment net sales"
    ]:
        raise ValueError("HD primary segment subtotal does not reconcile")
    if [a + b for a, b in zip(rows["Primary segment net sales"], rows["Other net sales"])] != rows[
        "Net sales"
    ]:
        raise ValueError("HD product breakdown does not reconcile")
    if (
        rows["Net sales"][:2] != metrics["Net sales"][-2:]
        if q == 4
        else rows["Net sales"] != metrics["Net sales"]
    ):
        raise ValueError("HD product sales disagree with the independently published earnings release")
    day = signature_date.isoformat()
    return (
        dict(
            label=f"홈디포 {form} · 서명 {day}",
            labelEn=f"Home Depot {form} · signed {day}",
            url=url,
            periodEnd=end.isoformat(),
            signed=day,
        ),
        rows,
    )


def hd_statement(refs, year, q, fetch, warnings):
    release_url, filing_url = refs
    source, metrics = hd_press(lines_from_pdf(fetch(release_url), None), year, q, release_url)
    products = None
    try:
        if not filing_url:
            raise ValueError("Home Depot posted its earnings release before the original product note")
        note, products = hd_product_note(
            lines_from_pdf(fetch(filing_url), None), year, q, filing_url, metrics
        )
    except (OSError, ValueError) as exc:
        warnings.append(f"{'annual' if q == 4 else 'interim'}-product-note-unavailable ({exc})")
    modes = [("annual", 2, 0)] if q == 4 else [("quarter", 0, 0)]
    if q in (2, 3):
        modes.append(("ytd", 2, 2))
    tables = []
    for mode, earn_idx, product_idx in modes:
        periods = hd_periods(year, q, mode)
        tk, te = {
            "annual": ("연간", "Full year"),
            "quarter": ("분기", "Quarter"),
            "ytd": ("연초 이후 누적", "Year to date"),
        }[mode]
        amounts = {
            label: list(reversed(values[earn_idx : earn_idx + 2])) for label, values in metrics.items()
        }
        if products:
            sales = {
                label: list(reversed(values[product_idx : product_idx + 2]))
                for label, values in products.items()
            }
            product = result_table(
                "hd-ir-product-" + mode,
                "제품군별 순매출 · " + tk,
                "Net sales by product line · " + te,
                "revenue",
                HD_PRODUCTS,
                sales,
                periods,
                sales["Net sales"],
                note,
                (
                    "주력 사업의 세 제품군과 기타 사업을 합한 금액입니다. 관련 서비스가 포함됩니다.",
                    "Three major product lines in the Primary segment include related services. Other net sales are shown separately.",
                ),
            )
            if all(v >= 0 for row in product["rows"] for v in row["values"]):
                product["compositionKeys"] = [r["key"] for r in product["rows"]]
                product["compositionPeriods"] = [p["label"] for p in periods]
            tables.append(product)
        tables.append(
            result_table(
                "hd-ir-income-" + mode,
                "연결 손익 · " + tk,
                "Consolidated earnings · " + te,
                "financial-results",
                HD_ROWS,
                amounts,
                periods,
                None,
                source,
                (
                    "각 줄은 순매출에서 비용을 차례로 뺀 손익계산서의 주요 항목입니다.",
                    "The lines are successive measures of earnings after expenses.",
                ),
            )
        )
    return source, tables


JPM_NONINTEREST = {
    "Investment banking fees": "투자은행 수수료",
    "Principal transactions": "자기계정 거래수익",
    "Lending- and deposit-related fees": "대출·예금 수수료",
    "Asset management fees": "자산운용 수수료",
    "Commissions and other fees": "중개·기타 수수료",
    "Investment securities gains/(losses)": "투자증권 손익",
    "Mortgage fees and related income": "주택담보대출 수수료·관련 수익",
    "Card income": "카드 수익",
    "Other income": "기타수익",
}


def jpm_directory(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("Invalid JPMorganChase earnings directory")
    result = {}
    quarters = ["1st", "2nd", "3rd", "4th"]
    for entry in data["items"]:
        if not isinstance(entry, dict) or str(entry.get("year", "")) < "2023":
            continue
        if not re.fullmatch(r"20\d\d", str(entry.get("year"))) or entry.get("quarter") not in quarters:
            raise ValueError("Unknown JPMorganChase reporting period")
        year, ordinal = int(entry["year"]), entry["quarter"]
        q = quarters.index(ordinal) + 1
        refs = []
        for key, suffix in (
            ("pressRelease", ".pdf"),
            ("tenkSupplementalDoc", ".xlsx"),
            ("supplement", ".pdf"),
        ):
            attachment = entry.get("docs", {}).get(key)
            if not attachment:
                refs.append(None)
                continue
            if not isinstance(attachment, dict) or not isinstance(attachment.get("link"), str):
                raise ValueError("Unexpected JPMorganChase attachment metadata")
            url = urljoin(JPM_INDEX, attachment["link"])
            parts = urlsplit(url)
            if (
                parts.scheme != "https"
                or parts.netloc != "www.jpmorganchase.com"
                or parts.query
                or parts.fragment
                or not parts.path.startswith(
                    f"/content/dam/jpmc/jpmorgan-chase-and-co/investor-relations/documents/quarterly-earnings/{year}/{ordinal}-quarter/"
                )
                or not parts.path.lower().endswith(suffix)
            ):
                # Some earlier items provide the supplement in XLS rather than XLSX. Reject when chosen.
                refs.append(None)
                continue
            refs.append(url)
        if (year, q) in result:
            raise ValueError("Ambiguous JPMorganChase earnings release")
        result[year, q] = refs
    return result


def jpm_financials(sheet, year, q, source):
    # Page 4 is explicitly the consolidated GAAP income statement. Segment highlight pages use managed-basis results.
    required = [
        "JPMORGAN CHASE & CO.",
        "CONSOLIDATED STATEMENTS OF INCOME",
        "(in millions, except per share and ratio data)",
    ]
    if not all(any(r.get("B") == t for r in sheet[:6]) for t in required):
        raise ValueError("Wrong JPMorganChase identity, statement or amount unit")
    idx = single([n for n, r in enumerate(sheet) if r.get("B") == "REVENUE"], "consolidated revenue header")
    period_row = sheet[idx]
    if idx < 2 or sheet[idx - 2].get("F") != "QUARTERLY TRENDS":
        raise ValueError("Quarterly amounts not found in JPMorganChase statement")
    if (period_row.get("F"), period_row.get("N")) != (f"{q}Q{year%100:02d}", f"{q}Q{(year-1)%100:02d}"):
        raise ValueError("Wrong JPMorganChase quarter columns")
    end = date(year, q * 3, monthrange(year, q * 3)[1])
    if q > 1:
        ytd = {2: "SIX MONTHS ENDED JUNE 30,", 3: "NINE MONTHS ENDED SEPTEMBER 30,", 4: "FULL YEAR"}[q]
        if (
            sheet[idx - 2].get("T") != ytd
            or str(period_row.get("T")) != str(year)
            or str(period_row.get("V")) != str(year - 1)
        ):
            raise ValueError("Wrong annual or cumulative JPMorganChase columns")
    block = sheet[idx + 1 :]

    def values(label, columns):
        row = single([r for r in block if r.get("B") == label or r.get("C") == label], label)
        nums = [row.get(c) for c in columns]
        if not all(isinstance(n, Decimal) and n == n.to_integral_value() for n in nums):
            raise ValueError("Missing GAAP dollars for " + label)
        return list(map(int, nums))

    modes = [("annual", "VT")] if q == 4 else [("quarter", "NF")]
    if q in (2, 3):
        modes.append(("ytd", "VT"))
    tables = []
    for mode, columns in modes:
        labels = dict(JPM_NONINTEREST, **{"Net interest income": "순이자이익"})
        income = {l: values(l, columns) for l in labels}
        noninterest = values("Noninterest revenue", columns)
        netinterest = income["Net interest income"]
        total = values("TOTAL NET REVENUE", columns)
        net = values("NET INCOME", columns)
        if (
            [sum(v) for v in zip(*(income[l] for l in JPM_NONINTEREST))] != noninterest
            or [
                a - b
                for a, b in zip(values("Interest income", columns), values("Interest expense", columns))
            ]
            != netinterest
            or [a + b for a, b in zip(noninterest, netinterest)] != total
        ):
            raise ValueError("JPMorganChase GAAP revenue components do not reconcile")
        provisions = values("Provision for credit losses", columns)
        expense = values("TOTAL NONINTEREST EXPENSE", columns)
        beforetax = values("Income before income tax expense", columns)
        tax = values("Income tax expense", columns)
        if [a - b - c for a, b, c in zip(total, provisions, expense)] != beforetax or [
            a - b for a, b in zip(beforetax, tax)
        ] != net:
            raise ValueError("JPMorganChase reported consolidated net income does not reconcile")
        periods = []
        for y in (year - 1, year):
            stop = end.replace(year=y).isoformat()
            first = date(y, 3 * q - 2 if mode == "quarter" else 1, 1)
            periods.append(dict(start=first.isoformat(), end=stop, label=stop, labelEn=stop))
        tk, te = {
            "annual": ("연간", "Full year"),
            "quarter": ("분기", "Quarter"),
            "ytd": ("연초 이후 누적", "Year to date"),
        }[mode]
        tables.append(
            result_table(
                "jpm-ir-revenue-" + mode,
                "이자와 수수료 등 순수익 구성 · " + tk,
                "Sources of reported net revenue · " + te,
                "revenue",
                labels,
                income,
                periods,
                total,
                source,
                (
                    "순이자이익은 이자수익에서 이자비용을 뺀 금액입니다. 공시 회계기준의 순수익에는 투자증권 손익도 들어갑니다.",
                    "Net interest income deducts interest expense. Reported GAAP net revenue includes gains and losses on investment securities.",
                ),
            )
        )
    return tables


def jpm_statement(refs, year, q, fetch):
    press, xlsx, supplement = refs
    if not all(refs):
        raise ValueError("Missing official quarterly earnings attachments")
    text = " ".join(lines_from_pdf(fetch(press), None))
    if (
        "JPMorgan Chase & Co." not in text
        or "NYSE symbol: JPM" not in text
        or f"JPMORGANCHASE REPORTS {ORDINAL[q-1].upper()}-QUARTER {year} NET INCOME" not in text
    ):
        raise ValueError("JPMorganChase earnings identity or date mismatch")
    # The release identifies its own date as 'today'. PDF creation/modification timestamps can differ by weeks.
    stamp = re.search(r"conference call today, (" + MONTH_DAY + r"), (20\d\s?\d),", text)
    if not stamp:
        raise ValueError("Missing publication date on JPMorganChase earnings release")
    published = datetime.strptime(stamp[1] + " " + stamp[2].replace(" ", ""), "%B %d %Y").date()
    end = date(year, q * 3, monthrange(year, q * 3)[1])
    if not end < published <= date.today() or (published - end).days > 100:
        raise ValueError("JPMorganChase earnings release date outside reporting window")
    source = dict(
        label="JP모건체이스 실적 보충자료",
        labelEn="JPMorganChase earnings supplement",
        url=supplement,
        periodEnd=end.isoformat(),
        published=published.isoformat(),
        releaseUrl=press,
        dataUrl=xlsx,
    )
    return source, jpm_financials(sheet_cells(fetch(xlsx), "Page 4", 58), year, q, source)


def refresh_additional(report, cik, fetch_bytes):
    ticker = report["ticker"]
    if (ticker, int(cik)) not in {("COP", 1163165), ("HD", 354950), ("JPM", 19617)}:
        raise ValueError("Unsupported issuer")
    if ticker == "COP":
        entries, statement = cop_directory(fetch_bytes(COP_INDEX)), cop_statement
    elif ticker == "HD":
        entries, statement = hd_directory(fetch_bytes), None
    else:
        entries, statement = jpm_directory(fetch_bytes(JPM_INDEX)), jpm_statement
    output = deepcopy(report)
    latest, warnings = [], []
    for kind in ("annual", "interim"):
        try:
            choices = [p for p in entries if (p[1] == 4) == (kind == "annual")]
            if not choices:
                raise ValueError("No issuer document for this frequency")
            year, q = max(choices)
            if ticker == "HD":
                source, tables = hd_statement(entries[year, q], year, q, fetch_bytes, warnings)
            else:
                source, tables = statement(entries[year, q], year, q, fetch_bytes)
            end = source["periodEnd"]
            old = output[kind]
            if any(p.get("end", "") > end for t in old for p in t["periods"]):
                raise ValueError("Issuer material predates existing figures")
            if any(
                t["source"].get("periodEnd") == end
                and t["source"].get("published", "") > source["published"]
                for t in old
            ):
                raise ValueError("A newer release is already stored")
            updated_families = {t["id"].rsplit("-", 1)[0] for t in tables}
            kept = [t for t in old if t["id"].rsplit("-", 1)[0] not in updated_families]
            filed = [t for t in kept if t["source"].get("filed") and t["periods"][-1].get("end") == end]
            output[kind] = filed + tables + [t for t in kept if t not in filed]
            latest.append(dict(source, kind=kind))
        except (OSError, ValueError) as exc:
            warnings.append(f"{kind}-unavailable ({exc})")
    if not latest:
        raise ValueError("; ".join(warnings))
    return output, dict(latest=latest, warnings=warnings)
