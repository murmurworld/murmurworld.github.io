"""Read consolidated sales from the mining companies' own financial statements."""

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
import re
from urllib.parse import parse_qs, urlsplit

from lxml import html
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from pypdf.constants import UserAccessPermissions

from issuer_additional import result_table, single


RIO_INDEX = "https://www.riotinto.com/invest"
RIO_CDN = "cdn-rio.dataweavers.io"
MINING_HOSTS = {"www.riotinto.com", RIO_CDN}
MINING_TICKERS = {"RIO"}
PRODUCTS = {
    "Iron ore": "철광석",
    "Aluminium, alumina and bauxite": "알루미늄·알루미나·보크사이트",
    "Copper": "구리",
    "Industrial minerals": "산업광물",
    "Gold": "금",
    "Lithium": "리튬",
    "Other products and freight services": "기타 제품·운송 서비스",
}
DESTINATIONS = {
    "Greater China": "중화권",
    "US": "미국",
    "Japan": "일본",
    "Asia (excluding Greater China, Japan and South Korea)": "기타 아시아(중화권·일본·한국 제외)",
    "Europe (excluding UK)": "유럽(영국 제외)",
    "Europe (excluding UK and Netherlands)": "유럽(영국·네덜란드 제외)",
    "South Korea": "한국",
    "Netherlands": "네덜란드",
    "Canada": "캐나다",
    "Australia": "호주",
    "UK": "영국",
    "Other countries": "기타 국가",
}
CELL = re.compile(r"(?:\(?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\)?|[–—−-])")
DATE = r"\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) 20\d\d"


def rio_directory(raw):
    doc = html.fromstring(raw)
    if not any("Invest" in s for s in doc.xpath("//title/text()")):
        raise ValueError("Not the Rio Tinto investor directory")
    docs = {}
    for box in doc.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' document-basket-doc ')]"):
        titles = box.xpath("./div[contains(@class,'document-basket-doc-title')]/text()")
        if len(titles) != 1:
            continue
        title = re.fullmatch(r"(Annual Report|Annual Results|Half Year Results) (20\d\d)", titles[0].strip(), re.I)
        if not title:
            continue
        year = int(title[2])
        kind = {"annual report": "annual", "annual results": "annual-results", "half year results": "interim"}[title[1].lower()]
        url = single(box.xpath(".//a[@href]/@href"), "Rio Tinto document link")
        address = urlsplit(url)
        base = "/-/media/content/documents/invest/"
        suffix = (f"reports/annual-reports/{year}-annual-report.pdf" if kind == "annual" else
                  f"financial-news-and-performance/results/{year}/{year}-" +
                  ("annual-results.pdf" if kind == "annual-results" else "half-year-results.pdf"))
        query = parse_qs(address.query, keep_blank_values=True)
        if (address.scheme != "https" or address.netloc not in MINING_HOSTS
                or address.path.lower() != base + suffix or address.fragment
                or query and (set(query) != {"rev"} or len(query["rev"]) != 1
                              or not re.fullmatch(r"[a-fA-F0-9]{32}", query["rev"][0]))):
            raise ValueError("Unexpected Rio Tinto financial document location")
        if (kind, year) in docs and docs[kind, year] != url:
            raise ValueError("Two Rio Tinto statements for the same period")
        docs[kind, year] = url
    return docs


def outline_entries(pdf, entries):
    for entry in entries:
        if isinstance(entry, list):
            yield from outline_entries(pdf, entry)
        else:
            yield entry.title, pdf.get_destination_page_number(entry)


def rio_document(raw, year, kind):
    if not raw.startswith(b"%PDF-") or len(raw) > 32_000_000:
        raise ValueError("Invalid Rio Tinto financial statement")
    try:
        pdf = PdfReader(BytesIO(raw))
        if (pdf.is_encrypted and not (pdf.user_access_permissions and
                                      pdf.user_access_permissions & UserAccessPermissions.EXTRACT)
                or not 4 <= len(pdf.pages) <= 600):
            raise ValueError("Unsupported Rio Tinto financial document")
        headings = list(outline_entries(pdf, pdf.outline))
        cover = " ".join(pdf.pages[0].extract_text(extraction_mode="layout").split())
        if kind == "annual-results":
            if "Rio Tinto" not in cover or not re.search(rf"{year} full year results", cover, re.I):
                raise ValueError("Wrong Rio Tinto annual results release")
            stamp = re.search(r"full year results\s+(" + DATE + ")", cover, re.I)
            end = date(year, 12, 31)
            matches = []
        elif kind == "annual":
            if (not re.search(rf"Annual Report {year}\b", cover, re.I)
                    or not re.search(rf"Rio Tinto.*Annual Report {year}", pdf.metadata.title or "", re.I)):
                raise ValueError("Wrong Rio Tinto annual report identity or period")
            presentation = single([n for title, n in headings if
                                   "about the presentation of our financial statements" in title.lower()],
                                  "Rio Tinto directors' approval note")
            governance = " ".join(pdf.pages[presentation].extract_text().split())
            if "Rio Tinto plc" not in governance or "Rio Tinto Limited" not in governance:
                raise ValueError("Wrong consolidated accounting entity")
            stamp = re.search(r"authorised for issue in accordance with a Directors[’'] resolution on (" + DATE + ")", governance)
            end = date(year, 12, 31)
            matches = [n for title, n in headings if re.search(r"revenue by destination and product", title, re.I)]
        else:
            if (not re.search(rf"{str(year)[:3]}\s?{year%10} half year results", cover, re.I)
                    or "Rio Tinto" not in cover or not re.search(r"Six months ended 30 June", cover, re.I)):
                raise ValueError("Wrong Rio Tinto half year release identity or period")
            stamp = re.search(r"half year results\s+(" + DATE + ")", cover, re.I)
            end = date(year, 6, 30)
            matches = [n for title, n in headings if re.search(r"^\d+[.]? Segmental information\s*[-–]\s*additional information", title, re.I)]
        if not stamp:
            raise ValueError("Missing Rio Tinto approval or publication date")
        signed = datetime.strptime(stamp[1], "%d %B %Y").date()
        if not end < signed <= date.today() or (signed - end).days > 160:
            raise ValueError("Invalid Rio Tinto document date")
        if kind == "annual-results":
            lines = [" ".join(line.split()) for line in pdf.pages[0].extract_text(extraction_mode="layout").splitlines() if line.strip()]
            return lines, 1, signed.isoformat(), end.isoformat()
        start = single(matches, "consolidated revenue note in the issuer PDF outline")
        if not isinstance(start, int) or not 0 <= start < len(pdf.pages):
            raise ValueError("Invalid PDF note reference")
        for page in range(start, min(start + 3, len(pdf.pages))):
            lines = [" ".join(s.split()) for s in pdf.pages[page].extract_text(extraction_mode="layout").splitlines() if s.strip()]
            if "Consolidated sales revenue by product" in lines and any(
                s.startswith("Consolidated sales revenue by destination") for s in lines
            ):
                return lines, page + 1, signed.isoformat(), end.isoformat()
    except (PyPdfError, KeyError, IndexError, AttributeError) as exc:
        raise ValueError("Unreadable mining financial statement") from exc
    raise ValueError("Missing consolidated product and geographical revenue notes")


def numeric_rows(lines, first, end, width):
    """Pair a wrapped table label with the exact number of trailing numerical cells."""
    start = single([i for i, s in enumerate(lines) if s.startswith(first + " ")], first + " row")
    pending = ""
    for line in lines[start:]:
        words = line.split()
        split = len(words)
        while split and CELL.fullmatch(words[split - 1]):
            split -= 1
        if len(words) == split:
            pending = line if line.startswith("Industrial minerals") else ""
            continue
        if len(words) - split != width:
            raise ValueError("Changed consolidated table column count")
        label = (pending + " " + " ".join(words[:split])).strip()
        pending = ""
        cells = []
        for token in words[split:]:
            if token in {"-", "−", "–", "—"}:
                cells.append(None)
                continue
            if token.startswith("(") != token.endswith(")"):
                raise ValueError("Unbalanced financial number")
            number = Decimal(token.strip("()").replace(",", ""))
            cells.append(-number if token.startswith("(") else number)
        yield label, cells
        if label == end:
            return
    raise ValueError("Missing consolidated group total")


def rio_tables(lines, year, kind, source):
    annual = kind == "annual"
    years = [year, year - 1, year - 2] if annual else [year, year - 1]
    count = len(years)
    geography = single([i for i, s in enumerate(lines) if s.startswith("Consolidated sales revenue by destination")], "destination heading")
    products = single([i for i, s in enumerate(lines) if s == "Consolidated sales revenue by product"], "product heading")
    if products <= geography:
        raise ValueError("Unexpected ordering of revenue notes")
    geo = lines[geography:products]
    prod = lines[products:]
    gy = " ".join(str(y) for y in years)
    py = gy if annual else " ".join(str(y) for y in years for _ in range(3))
    geo_header = " ".join(geo[:single([i for i, s in enumerate(geo) if s.startswith("Greater China ")], "first destination")])
    product_header = " ".join(prod[:single([i for i, s in enumerate(prod) if s.startswith("Iron ore ")], "first product")])
    if (f"{gy} {gy}" not in geo_header or py not in product_header
            or geo_header.count("US$m") != count or product_header.count("US$m") != count * 3
            or "contracts with" not in product_header or "Other" not in product_header
            or (not annual and "Six months ended 30 June" not in product_header)):
        raise ValueError("Changed currency, financial period or consolidated revenue columns")
    periods = [
        dict(start=f"{y}-01-01", end=f"{y}-" + ("12-31" if annual else "06-30"),
             label=f"FY{y}" if annual else f"{y} 상반기", labelEn=f"FY{y}" if annual else f"H1 {y}")
        for y in reversed(years)
    ]

    product_values, place_values, percentages = {}, {}, {}
    total_name = "Consolidated sales revenue"
    for label, cells in numeric_rows(prod, "Iron ore", total_name, count * 3):
        label = re.sub(r"\s*\([a-z]\)$", "", label)
        if label.startswith("Industrial minerals (comprising titanium"):
            label = "Industrial minerals"
        if label in product_values or label not in PRODUCTS and label != total_name:
            raise ValueError("Unknown or repeated product in the issuer statement")
        consolidated = []
        for i in range(0, len(cells), 3):
            contracts, adjustment, sales = cells[i:i + 3]
            if (contracts or 0) + (adjustment or 0) != (sales or 0):
                raise ValueError("Contract sales and other revenue do not reconcile")
            consolidated.append(sales)
        product_values[label] = consolidated
    for label, cells in numeric_rows(geo, "Greater China", total_name, count * 2):
        if label in place_values or label not in DESTINATIONS and label != total_name:
            raise ValueError("Unknown or repeated customer destination")
        percentages[label], place_values[label] = cells[:count], cells[count:]

    total = product_values.pop(total_name)
    if (place_values.pop(total_name) != total or percentages.pop(total_name) != [100] * count
            or any(n is None or n <= 0 for n in total)):
        raise ValueError("Product and destination totals disagree")
    for values in (product_values, place_values):
        if any(sum((v[i] or 0) for v in values.values()) != value for i,value in enumerate(total)):
            raise ValueError("Disclosed lines do not add to consolidated sales")
        if any(v is not None and (v < 0 or v != int(v)) for row in values.values() for v in row):
            raise ValueError("Non-integral or negative sales in USD millions")
    for label, cells in place_values.items():
        if any(abs((n or 0) * 100 / total[i] - (percentages[label][i] or 0)) > Decimal("0.11") for i,n in enumerate(cells)):
            raise ValueError("Geographic shares disagree with disclosed money amounts")
    def table(name, title, en, labels, values, notes):
        converted = {key: [None if x is None else int(x) for x in reversed(row)] for key,row in values.items()}
        t = result_table(f"rio-{name}-{kind}", title, en, "revenue",
                         {k: labels[k] for k in values}, converted, periods, [int(n) for n in reversed(total)], source, notes)
        t["compositionKeys"] = [r["key"] for r in t["rows"]]
        t["compositionPeriods"] = [p["label"] for i, p in enumerate(periods) if all(r["values"][i] is not None for r in t["rows"])]
        return t
    return [
        table("products", "외부 고객에게 판매한 제품별 연결 매출", "Consolidated sales to external customers by product", PRODUCTS, product_values, (
            "계약 매출에 광물의 잠정 판매가격 정산액 등을 반영한 금액이다. 구리 광산에서 나온 금은 금 매출에 잡힌다. 관계기업 매출을 지분만큼 더하는 사업부문 표와 집계 기준이 다르다.",
            "These are sales to external customers, including adjustments to provisional prices. Gold sold by a copper mine is reported as gold. Segment revenue also includes Rio Tinto’s share of equity-accounted businesses.")),
        table("destinations", "판매 목적지별 연결 매출", "Consolidated sales by customer destination", DESTINATIONS, place_values, (
            "제품의 최종 도착지를 기준으로 나눈다. 목적지를 확인하기 어려운 거래는 고객의 배송지로 분류한다.",
            "Sales are assigned to the final destination of the product when known. Otherwise Rio Tinto uses the customer’s shipping address.")),
    ]


def rio_early_annual(lines, year, source):
    # The earnings release can arrive before the full annual report and its notes.
    header = f"Year ended 31 December {year} {year-1} Change"
    start = single([n for n,line in enumerate(lines) if line == header], "annual earnings highlights years")
    labels = {"Consolidated sales revenue": "연결 매출", "Net cash generated from operating activities": "영업활동 현금흐름"}
    amounts = {}
    for name in labels:
        row = single([s for s in lines[start+1:] if s.startswith(name + " (US$ millions) ")], name)
        fields = row.split("(US$ millions) ", 1)[1].split()
        if len(fields) < 3 or not all(re.fullmatch(r"\d+(?:,\d{3})*", n) for n in fields[:2]):
            raise ValueError("Unexpected annual earnings amounts or units")
        amounts[name] = [int(n.replace(",", "")) for n in fields[:2]][::-1]
    periods = [dict(start=f"{y}-01-01", end=f"{y}-12-31", label=f"FY{y}", labelEn=f"FY{y}") for y in (year-1, year)]
    return [result_table("rio-results-annual", "연간 실적 발표의 연결 지표", "Group figures in the annual results release",
                         "financial-results", labels, amounts, periods, None, source, (
        "회사의 연간 실적 발표에 기재된 두 지표다. 제품별 매출은 같은 해 연차보고서 주석에서 확인할 수 있다.",
        "Sales and cash from operations are separate group figures. The annual report supplies the sales breakdown by product."))]


def refresh_mining(report, cik, fetch):
    # The RIO ADR is Rio Tinto plc. The same group statement on Form 20-F
    # is filed jointly by plc (863064) and Rio Tinto Limited (887028).
    if report["ticker"] != "RIO" or int(cik) not in {863064, 887028}:
        raise ValueError("Unsupported mining issuer")
    docs = rio_directory(fetch(RIO_INDEX))
    updated = deepcopy(report)
    latest, warnings = [], []
    for kind in ("annual", "interim"):
        try:
            annual = kind == "annual"
            years = [y for freq, y in docs if freq == kind or (annual and freq == "annual-results")]
            if not years:
                raise ValueError("No current financial document for this frequency")
            year = max(years)
            fmt = kind if (kind, year) in docs else "annual-results"
            url = docs[fmt, year]
            try:
                lines, page, stamp, end = rio_document(fetch(url), year, fmt)
            except (OSError, ValueError):
                if fmt != "annual" or ("annual-results", year) not in docs:
                    raise
                fmt = "annual-results"
                url = docs[fmt, year]
                lines, page, stamp, end = rio_document(fetch(url), year, fmt)
            source = dict(label="리오틴토 연차보고서" if annual else "리오틴토 반기 실적보고서",
                          labelEn="Rio Tinto annual report" if annual else "Rio Tinto half year results",
                          periodEnd=end, url=f"{url}#page={page}")
            if fmt == "annual-results":
                source.update(label="리오틴토 연간 실적 발표", labelEn="Rio Tinto annual results release")
                warnings.append("annual-product-notes-unavailable")
            dated = "authorized" if fmt == "annual" else "published"
            source[dated] = stamp
            old = updated[kind]
            if any(p.get("end", "") > end for t in old for p in t["periods"]):
                raise ValueError("The issuer report predates existing figures")
            if any(t["source"].get("periodEnd") == end and t["source"].get(dated, "") > stamp for t in old):
                raise ValueError("A later issuer statement is already stored")
            tables = rio_early_annual(lines, year, source) if fmt == "annual-results" else rio_tables(lines, year, kind, source)
            ids = {t["id"] for t in tables}
            updated[kind] = tables + [t for t in old if t["id"] not in ids]
            latest.append(dict(source, kind=kind))
        except (OSError, ValueError) as exc:
            warnings.append(f"{kind}-unavailable ({exc})")
    if not latest:
        raise ValueError("; ".join(warnings))
    return updated, dict(latest=latest, warnings=warnings)
