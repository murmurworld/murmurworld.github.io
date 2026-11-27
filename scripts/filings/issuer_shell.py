"""Read third-party revenue from Shell's annual accounts and quarterly segment notes."""

import calendar
import json
import re
from copy import deepcopy
from datetime import date, datetime
from io import BytesIO
from urllib.parse import urljoin, urlsplit

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from issuer_native import financial_table

HOST = "www.shell.com"
BASE = "https://" + HOST + "/investors/results-and-reporting/"
SEGMENTS = (
    ("gas", "통합 가스", "Integrated Gas"),
    ("upstream", "탐사·생산", "Upstream"),
    ("marketing", "주유소·윤활유 등 마케팅", "Marketing"),
    ("chemicals", "화학·석유제품", "Chemicals and Products"),
    ("renewables", "재생에너지·에너지 솔루션", "Renewables and Energy Solutions"),
    ("corporate", "본사·기타", "Corporate"),
)
NUMBER = r"(?:\d{1,3}(?:,\d{3})*|\d+)"
AMOUNT = re.compile(rf"^(?:{NUMBER}|\({NUMBER}\)|—)$")
PERIOD = re.compile(r"^(?:(Q[1-4]|Half year|Nine months|Full year) )?(20\d\d)(?: \$ million)?$", re.I)


def objects(node):
    if isinstance(node, list):
        for child in node:
            yield from objects(child)
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from objects(child)


def pdf_url(link):
    url = urljoin(BASE, link["value"])
    address = urlsplit(url)
    if address.scheme != "https" or address.netloc != HOST or not address.path.lower().endswith(".pdf"):
        raise ValueError("Unexpected Shell statement link")
    return url


def statements(data, annual):
    entries = list(objects(json.loads(data)))
    if annual:
        years = {
            int(m[1])
            for e in entries
            if (m := re.fullmatch(r"Annual Report and Accounts (20\d\d)", str(e.get("title", ""))))
        }
        links = {
            pdf_url(e)
            for e in entries
            if re.match(r"^Consolidated Financial Statements \(PDF", str(e.get("name", "")), re.I)
        }
        pattern = r"Shell plc\s*[-–]\s*([A-Za-z]+ \d{1,2})(?:st|nd|rd|th)?, (20\d\d)"
        days = {
            datetime.strptime(m[1] + " " + m[2], "%B %d %Y").date()
            for e in entries
            for m in re.finditer(pattern, str(e.get("text", "")))
        }
        if len(years) != 1 or len(days) != 1 or len(links) != 1:
            raise ValueError("Could not identify the dated annual report and consolidated statements")
        year, published, url = years.pop(), days.pop(), links.pop()
        if published.year != year + 1:
            raise ValueError("Annual report and publication date disagree")
        return year, 4, published, url
    found = []
    for e in entries:
        title = re.fullmatch(r"Q([1-4]) (20\d\d) Results", str(e.get("title", "")), re.I)
        if not title:
            continue
        day = re.fullmatch(
            r"\s*(\d{1,2} [A-Z]{3,9} 20\d\d)\s*", re.sub(r"<[^>]*>", "", str(e.get("text", ""))), re.I
        )
        if not day:
            raise ValueError("Missing date on Shell quarterly result")
        for link in e.get("links", []):
            if re.match(r"^Quarterly unaudited results \(PDF", link.get("name", ""), re.I):
                year, q = int(title[2]), int(title[1])
                url = pdf_url(link)
                if not re.search(rf"/q{q}-{year}-[^/]+\.pdf$", url, re.I):
                    continue
                heard = day[1].split()
                published = datetime.strptime(
                    " ".join((heard[0], heard[1][:3], heard[2])), "%d %b %Y"
                ).date()
                found.append((year, q, published, url))
    if not found:
        raise ValueError("Missing current Shell quarterly figures")
    return max(found)


def numbers(tokens):
    if len(tokens) != 7 or not all(AMOUNT.fullmatch(s) for s in tokens):
        raise ValueError("Expected six segment amounts and a total")

    def read(token):
        if token == "—":
            return 0
        return int(token.replace(",", "").replace("(", "-").replace(")", ""))

    values = list(map(read, tokens))
    # Shell rounds each displayed amount to the nearest million dollars.
    if abs(sum(values[:-1]) - values[-1]) > 3:
        raise ValueError("Third-party revenue does not reconcile with the disclosed total")
    return values


def collect(pages):
    result = {}
    for page in pages:
        layout = [s for s in page.splitlines() if s.strip()]
        lines = [" ".join(s.split()) for s in layout]
        for i, line in enumerate(lines):
            row = re.match(r"^Third-party(?: revenue)?\s+(?=[\d(—])(.+)$", line, re.I)
            if not row:
                continue
            start = next((j for j in range(i - 1, max(-1, i - 11), -1) if PERIOD.fullmatch(lines[j])), None)
            if start is None:
                raise ValueError("Revenue row without its own period")
            header = " ".join(lines[start:i])
            labels = (
                "Integrated",
                "Gas",
                "Upstream",
                "Marketing",
                "Chemicals",
                "Products",
                "Renewables",
                "Energy",
                "Solutions",
                "Corporate",
                "Total",
            )
            if "$ million" not in header or not all(word in header for word in labels):
                raise ValueError("Unrecognised Shell segment columns or units")
            # Names wrap over different lines, but the PDF layout preserves the
            # horizontal position of each segment. Reject changed column order.
            anchors = ("Integrated", "Upstream", "Marketing", "Chemicals", "Renewables", "Corporate", "Total")
            positions = [
                next((m.end() for original in layout[start:i] if (m := re.search(rf"\b{name}\b", original))), -1)
                for name in anchors
            ]
            if -1 in positions or any(left >= right for left, right in zip(positions, positions[1:])):
                raise ValueError("Shell segment order has changed")
            key = PERIOD.fullmatch(lines[start])
            period = (int(key[2]), (key[1] or "annual").lower())
            vector = numbers(row[1].split())
            if period in result and result[period] != vector:
                raise ValueError("Conflicting Shell revenue rows for the same period")
            result[period] = vector
    return result


def segment_table(identifier, scope, vector, columns, source):
    periods = []
    for y, label in columns:
        end_month = (
            12 if label == "annual" else {"half year": 6, "nine months": 9, "full year": 12}.get(label)
        )
        start_month = 1
        if end_month is None:
            end_month = 3 * int(label[1])
            start_month = end_month - 2
        end = date(y, end_month, calendar.monthrange(y, end_month)[1]).isoformat()
        periods.append(dict(label=end, labelEn=end, start=date(y, start_month, 1).isoformat(), end=end))
    rows = [(identity, [vector[col][i] for col in columns]) for i, identity in enumerate(SEGMENTS)]
    title = {
        "annual": ("외부 고객 매출 · 사업별", "Revenue from external customers by segment"),
        "quarter": ("분기 외부 고객 매출 · 사업별", "Quarterly external revenue by segment"),
        "ytd": ("누계 외부 고객 매출 · 사업별", "Year-to-date external revenue by segment"),
    }[scope]
    item = financial_table(identifier, title, periods, source, rows)
    item.update(
        measure="revenue",
        total=[vector[c][-1] for c in columns],
        compositionKeys=[s[0] for s in SEGMENTS],
        compositionPeriods=[p["label"] for p in periods],
        notes=[
            "외부 고객 매출만 집계했습니다. 부문 간 거래는 제외하며, 각 금액을 백만 달러 단위로 반올림해 합계에 차이가 날 수 있습니다."
        ],
        notesEn=[
            "Only third-party revenue is included. Inter-segment sales are excluded. Amounts rounded to USD millions may not add to the total."
        ],
    )
    return item


def refresh_shell(report, cik, fetch):
    if report["ticker"] != "SHEL" or cik != 1306965:
        raise ValueError("Unexpected Shell issuer")
    output = deepcopy(report)
    status = {"latest": [], "warnings": []}
    for section in ("annual", "interim"):
        annual = section == "annual"
        try:
            endpoint = "annual-report" if annual else "quarterly-results"
            year, q, published, url = statements(fetch(BASE + endpoint + ".model.json"), annual)
            end = date(year, q * 3, calendar.monthrange(year, q * 3)[1])
            if not end < published <= date.today() or any(
                p.get("end", "") > end.isoformat() for t in report[section] for p in t["periods"]
            ):
                raise ValueError("Publication date or covered period is out of range")
            pdf = PdfReader(BytesIO(fetch(url)))
            if not 2 < len(pdf.pages) <= 175:
                raise ValueError("Unexpected financial statement length")
            vector = collect(p.extract_text(extraction_mode="layout") for p in pdf.pages)
            src = dict(
                url=url,
                periodEnd=end.isoformat(),
                published=published.isoformat(),
                label="셸 연결재무제표" if annual else "셸 분기 실적 원문 (미감사)",
                labelEn=(
                    "Shell consolidated financial statements"
                    if annual
                    else "Shell interim results (unaudited)"
                ),
            )
            if annual:
                columns = sorted(k for k in vector if k[1] == "annual" and k[0] <= year)
                if len(columns) < 2 or columns[-1][0] != year:
                    raise ValueError("Latest annual segment note unavailable")
                tables = [segment_table("segments", "annual", vector, columns, src)]
            else:
                columns = [(y, f"q{q}") for y in (year - 1, year)]
                tables = [segment_table("shell-quarter-segments", "quarter", vector, columns, src)]
                if q in (2, 3):
                    ytd = [(y, "half year" if q == 2 else "nine months") for y in (year - 1, year)]
                    tables.append(segment_table("shell-ytd-segments", "ytd", vector, ytd, src))
            updated_ids = {t["id"] for t in tables} | ({"shell-ytd-segments"} if not annual else set())
            output[section] = tables + [t for t in report[section] if t["id"] not in updated_ids]
            status["latest"].append({**src, "kind": section})
        except (KeyError, ValueError, OSError, IndexError, PyPdfError) as err:
            status["warnings"].append(f"{section}-unavailable ({err})")
    if not status["latest"]:
        raise ValueError("; ".join(status["warnings"]))
    return output, status
