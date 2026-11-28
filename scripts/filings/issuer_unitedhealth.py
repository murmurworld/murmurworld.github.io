"""UnitedHealth Group's GAAP earnings releases and their two levels of sales elimination."""

import calendar
import re
from copy import deepcopy
from datetime import date, datetime
from io import BytesIO
from urllib.parse import urljoin, urlsplit

from lxml import html
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from issuer_native import financial_table

HOST = "www.unitedhealthgroup.com"
INDEX = "https://" + HOST + "/investors/financial-reports.html"
OPERATIONS = "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS"
BUSINESS = "REVENUES BY BUSINESS - SUPPLEMENTAL FINANCIAL INFORMATION"
INTEGER = r"(?:\d+|\d{1,3}(?:,\d{3})+)"
AMOUNT = rf"(?:\$?(?:{INTEGER}|\({INTEGER}\))|[—–])"
SCOPE = {1: None, 2: "Six Months", 3: "Nine Months", 4: "Year"}
ORDINAL = {1: "First", 2: "Second", 3: "Third", 4: "Fourth"}
INSURANCE = {
    "UnitedHealthcare Employer & Individual - Total": ("employer", "직장·개인 보험", "Employer & Individual"),
    "UnitedHealthcare Medicare & Retirement": ("medicare", "메디케어·은퇴자 보험", "Medicare & Retirement"),
    "UnitedHealthcare Community & State": ("community", "주정부·지역사회 보험", "Community & State"),
}
INCOME = {
    "Total revenues": ("sales", "연결 매출", "Consolidated revenue"),
    "Earnings from operations": ("operating", "영업이익", "Operating earnings"),
    "Net earnings": ("net", "연결 순이익", "Net earnings"),
    "Net earnings attributable to UnitedHealth Group common shareholders": (
        "attributable",
        "보통주주 귀속 순이익",
        "Net earnings attributable to common shareholders",
    ),
}


def discover(raw):
    doc = html.fromstring(raw)
    entries = {}
    for drawer in doc.xpath("//li[@data-drawer]"):
        label = " ".join(drawer.xpath('string(./a[@role="button"])').split())
        if not re.fullmatch(r"20\d\d", label):
            continue
        for link in drawer.xpath(".//a[@href]"):
            if " ".join(link.text_content().lower().split()) != "earnings release":
                continue
            column = next((p for p in link.iterancestors() if "col-md-6" in p.get("class", "").split()), None)
            if column is None:
                continue
            quarters = column.xpath('./p/b[starts-with(normalize-space(.),"Q")]/text()')
            if len(quarters) != 1 or not re.fullmatch(r"Q[1-4]", quarters[0].strip()):
                continue
            url = urljoin(INDEX, link.get("href"))
            parts = urlsplit(url)
            if parts.scheme != "https" or parts.netloc != HOST or parts.query or parts.fragment:
                continue
            if not parts.path.lower().startswith("/content/dam/uhg/pdf/") or not parts.path.lower().endswith(
                ".pdf"
            ):
                continue
            key = (int(label), int(quarters[0].strip()[1]))
            if key in entries and entries[key] != url:
                raise ValueError("Ambiguous official UNH release for period")
            entries[key] = url
    if not entries:
        raise ValueError("UNH archive has no dated earnings release")
    return entries


def amounts(text, count):
    parts = text.split()
    if len(parts) != count or not all(re.fullmatch(AMOUNT, p) for p in parts):
        raise ValueError("Invalid UNH amount columns")
    result = []
    for part in parts:
        raw = part.removeprefix("$")
        if raw.startswith("(") != raw.endswith(")"):
            raise ValueError("Unbalanced UNH amount")
        result.append(
            0 if raw in ("—", "–") else int(raw.replace(",", "").replace("(", "-").replace(")", ""))
        )
    return result


def row(lines, label, count):
    prefix = re.compile(re.escape(label) + r"\s*(?:\.{2,}\s*|\s+)(?=\$?\(?\d|[—–])")
    found = [prefix.sub("", s, count=1) for s in lines if prefix.match(s)]
    if len(found) != 1:
        raise ValueError("Missing or duplicate UNH line " + label)
    return amounts(found[0], count)


def parse_pages(pages, year, q, url):
    lines = [[" ".join(s.split()) for s in p.splitlines() if s.strip()] for p in pages]
    front = lines[0]
    title = rf"UnitedHealth Group Reports {ORDINAL[q]} Quarter {year} Results\b"
    if q == 4:
        title = rf"UnitedHealth Group Reports (?:{year} Results\b|Fourth Quarter {year} Results\b)"
    if not any(re.match(title, s, re.I) for s in front) or "UnitedHealth Group (NYSE: UNH)" not in " ".join(
        front
    ):
        raise ValueError("UNH company or fiscal quarter mismatch")
    dates = [s for s in front if re.fullmatch(r"[A-Z][a-z]+ \d{1,2}, 20\d\d", s)]
    if len(dates) != 1:
        raise ValueError("Ambiguous UNH publication date")
    published = datetime.strptime(dates[0], "%B %d, %Y").date()
    month = q * 3
    end = date(year, month, calendar.monthrange(year, month)[1])
    if published <= end or (published - end).days > 150:
        raise ValueError("UNH release date outside the reported period")
    source = dict(
        label="유나이티드헬스 실적 발표",
        labelEn="UnitedHealth Group earnings release",
        published=published.isoformat(),
        periodEnd=end.isoformat(),
        url=url,
    )

    def page(title, unit):
        matches = [p for p in lines if title in p]
        if len(matches) != 1 or unit not in matches[0]:
            raise ValueError("UNH statement heading or units changed")
        return matches[0]

    ops = page(OPERATIONS, "(in millions, except per share data; unaudited)")
    seg = page(BUSINESS, "(in millions; unaudited)")
    periods = ["Three Months"] + ([SCOPE[q]] if SCOPE[q] else [])
    day = end.strftime("%B") + f" {end.day},"
    headings = [
        " ".join(s + " Ended" for s in periods),
        " ".join([day] * len(periods)),
        " ".join([f"{year} {year-1}"] * len(periods)),
    ]
    for table in [ops, seg]:
        if not any(table[i : i + 3] == headings for i in range(len(table) - 2)):
            raise ValueError("UNH time periods or comparison years changed")
    if not any(
        re.fullmatch(
            r"UnitedHealthcare Health(?: \([a-z]\))? Insight(?: \([a-z]\))? Rx Optum \(a\) Consolidated \(a\)",
            s,
        )
        for s in seg
    ):
        raise ValueError("Unexpected order of UNH business columns")
    n = len(periods) * 2
    income = {k: row(ops, k, n) for k in INCOME}
    products = [row(ops, s, n) for s in ("Premiums", "Products", "Services", "Investment and other income")]
    if list(map(sum, zip(*products))) != income["Total revenues"]:
        raise ValueError("UNH GAAP revenue components do not reconcile")
    insurance = {k: row(seg, k, n) for k in INSURANCE}
    insurance_total = row(seg, "Total UnitedHealthcare revenues", n)
    if list(map(sum, zip(*insurance.values()))) != insurance_total:
        raise ValueError("UnitedHealthcare insurance revenue does not reconcile")
    footnote = " ".join(seg).lower()
    tables = {}
    for index, period in enumerate(periods):
        scope = "quarter" if index == 0 else ("annual" if q == 4 else "ytd")
        start_month = month - 2 if scope == "quarter" else 1
        published_rows = []
        for y in [year - 1, year]:
            header = f"{period} Ended {day} {y}"
            if seg.count(header) != 1:
                raise ValueError("UNH business period label missing")
            at = seg.index(header)
            published_rows.append(row(seg[at + 1 : at + 2], "Total revenues", 6))
        note = (
            rf"for the {period.lower()} ended {day.lower()} {year} and {year-1} include optum eliminations of "
            r"\$([\d,]+) and \$([\d,]+); and corporate eliminations of \$([\d,]+) and \$([\d,]+), respectively"
        )
        matches = re.findall(note, footnote)
        if len(matches) != 1:
            raise ValueError("UNH dated intercompany eliminations missing")
        a, b, c, d = (int(s.replace(",", "")) for s in matches[0])
        inside, corporate = [b, a], [d, c]
        ins, health, insight, rx, optum, total = map(list, zip(*published_rows))

        def pair(values):
            return [values[index * 2 + 1], values[index * 2]]

        for j in range(2):
            if (
                health[j] + insight[j] + rx[j] - inside[j] != optum[j]
                or ins[j] + optum[j] - corporate[j] != total[j]
            ):
                raise ValueError("UNH reported business eliminations do not reconcile")
        if total != pair(income["Total revenues"]) or ins != pair(insurance_total):
            raise ValueError("UNH segment and consolidated GAAP statements disagree")
        time = []
        for y in (year - 1, year):
            finish = date(y, month, calendar.monthrange(y, month)[1]).isoformat()
            months = month - start_month + 1
            time.append(
                dict(
                    label=f"{finish} 종료 {months}개월",
                    labelEn=f"{months} months to {finish}",
                    start=date(y, start_month, 1).isoformat(),
                    end=finish,
                )
            )
        pieces = [
            (("insurance", "유나이티드헬스케어 보험", "UnitedHealthcare"), ins),
            (("optum", "Optum 합계", "Total Optum"), optum),
            (("optum-health", "Optum Health · 진료·돌봄", "Optum Health"), health),
            (("optum-insight", "Optum Insight · 데이터·서비스", "Optum Insight"), insight),
            (("optum-rx", "Optum Rx · 약제 서비스", "Optum Rx"), rx),
            (
                ("optum-elimination", "Optum 내부거래 차감", "Less transactions within Optum"),
                [-v for v in inside],
            ),
            (
                ("group-elimination", "그룹 내부거래 차감", "Corporate intercompany eliminations"),
                [-v for v in corporate],
            ),
        ]
        business = financial_table(
            "unh-business-" + scope,
            ("보험·Optum 매출과 내부거래", "Insurance and Optum revenue reconciliation"),
            time,
            source,
            pieces,
        )
        business.update(
            total=total,
            measure="revenue",
            notes=[
                "Optum 세 사업 사이의 매출을 먼저 차감합니다. 보험과 Optum 매출을 합친 뒤 그룹 내부거래를 한 번 더 빼면 연결 매출이 됩니다."
            ],
            notesEn=[
                "Sales within Optum are removed first. Transactions between businesses are then removed from the sum of UnitedHealthcare and Optum revenue to arrive at consolidated revenue."
            ],
        )
        if "prior period amounts have been recast to reflect the realignment of optum financial" in footnote:
            business["notes"].append(
                "Optum Financial의 소속 변경에 맞춰 회사가 다시 표시한 전년 동기 수치를 사용했습니다."
            )
            business["notesEn"].append(
                "The company recast the comparison period to reflect the realignment of Optum Financial."
            )
        for r in business["rows"]:
            if r["key"].startswith("optum-"):
                r.update(level=1, parent="optum")
            if r["key"].endswith("elimination"):
                r["kind"] = "adjustment"
        coverage = financial_table(
            "unh-unitedhealthcare-" + scope,
            ("보험 고객군별 매출", "UnitedHealthcare revenue by customer group"),
            time,
            source,
            [(labels, pair(insurance[name])) for name, labels in INSURANCE.items()],
        )
        coverage.update(
            measure="revenue",
            total=ins,
            compositionKeys=[x[0] for x in INSURANCE.values()],
            compositionPeriods=[p["label"] for p in time],
        )
        earnings = financial_table(
            "unh-income-" + scope,
            ("연결 손익", "Consolidated GAAP results"),
            time,
            source,
            [(labels, pair(income[name])) for name, labels in INCOME.items()],
        )
        tables[scope] = [business, coverage, earnings]
    if q == 4:
        return source, {"annual": tables["annual"], "interim": tables["quarter"]}
    return source, {"interim": tables["quarter"] + tables.get("ytd", [])}


def refresh_unitedhealth(report, cik, fetch):
    if report["ticker"] != "UNH" or cik != 731766:
        raise ValueError("Unexpected UnitedHealth Group issuer")
    entries = discover(fetch(INDEX))
    out = deepcopy(report)
    status = {"latest": [], "warnings": []}
    cache = {}
    for section in ("annual", "interim"):
        try:
            key = max(k for k in entries if section == "interim" or k[1] == 4)
            url = entries[key]
            if key not in cache:
                reader = PdfReader(BytesIO(fetch(url)))
                text = [p.extract_text(extraction_mode="layout") for p in reader.pages]
                cache[key] = parse_pages(text, *key, url)
            src, sets = cache[key]
            if any(p["end"] > src["periodEnd"] for t in report[section] for p in t["periods"]):
                raise ValueError("UNH year or quarter predates stored results")
            out[section] = sets[section] + [t for t in report[section] if not t["id"].startswith("unh-")]
            status["latest"].append({**src, "kind": section})
        except (ValueError, OSError, KeyError, IndexError, PyPdfError) as err:
            status["warnings"].append(f"{section}-unavailable ({err})")
    if not status["latest"]:
        raise ValueError("; ".join(status["warnings"]))
    return out, status
