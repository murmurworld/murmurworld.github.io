"""Berkshire Hathaway's after-tax operating earnings, as reconciled by the issuer."""

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

HOME = "https://www.berkshirehathaway.com/"
HOST = urlsplit(HOME).hostname
ORDINALS = ("First", "Second", "Third", "Fourth")
SEGMENTS = {
    "insurance-underwriting": ("underwriting", "보험 인수", "Insurance underwriting"),
    "insurance-investmentincome": ("insurance-income", "보험 투자수익", "Insurance investment income"),
    "bnsf": ("bnsf", "BNSF 철도", "BNSF Railway"),
    "berkshirehathawayenergycompany": ("energy", "버크셔 해서웨이 에너지", "Berkshire Hathaway Energy"),
    "manufacturing,serviceandretailing": (
        "manufacturing",
        "제조·서비스·유통",
        "Manufacturing, service and retail",
    ),
    "other": ("other", "기타", "Other"),
}
VALUE = r"(?:\(?[\d,]+\)?|[—–-])"


def news_indexes(raw, base):
    years = {}
    for href in html.fromstring(raw).xpath("//a[@href]/@href"):
        url = urlsplit(urljoin(base, href))
        match = re.fullmatch(r"/news/(\d{4})news\.html", url.path)
        if match and url.scheme == "https" and url.hostname == HOST:
            years[int(match[1])] = url.geturl()
    return years


def releases(raw, index_url):
    for link in html.fromstring(raw).xpath("//dt/a[@href]"):
        description = link.getparent().getnext()
        if description is None or description.tag.lower() != "dd":
            continue
        title = " ".join(description.text_content().split())
        match = re.fullmatch(r"(First|Second|Third|Fourth) Quarter Earnings (\d{4})", title, re.I)
        if not match:
            continue
        url = urlsplit(urljoin(index_url, link.get("href")))
        if (
            url.scheme != "https"
            or url.hostname != HOST
            or not re.fullmatch(r"/news/[a-z\d]+\.pdf", url.path, re.I)
        ):
            continue
        published = datetime.strptime(" ".join(link.text_content().split()), "%B %d, %Y").date()
        if published <= date.today():
            yield int(match[2]), ORDINALS.index(match[1].title()) + 1, published, url.geturl()


def numbers(s):
    return [
        int(x.replace(",", "").replace("(", "-").replace(")", "")) if re.search(r"\d", x) else 0
        for x in re.findall(VALUE, s)
    ]


def table_rows(page):
    result = {}
    for line in page:
        match = re.fullmatch(r"(.+?)\s*[.$ ]+\s*((?:\$?\s*" + VALUE + r"\s*){2,4})", line)
        if match:
            key = re.sub(r"[ .\*]", "", match[1].lower()).replace("–", "-").replace("—", "-")
            result[key] = numbers(match[2])
    return result


def statements(pages, entry):
    year, q, published, url = entry
    end_month = q * 3
    end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    text = " ".join(pages[0].split())
    release_date = re.search(r"FOR IMMEDIATE RELEASE\s+([A-Za-z]+\s+\d+,\s*\d{4})", text)
    if (
        not release_date
        or datetime.strptime(release_date[1], "%B %d, %Y").date() != published
        or published < end
        or "BERKSHIRE HATHAWAY INC." not in text
        or "BRK.B" not in text
        or not re.search(r"dollar amounts are in millions", text, re.I)
    ):
        raise ValueError("Berkshire release identity, units or publication date changed")
    page_lists = [[" ".join(s.strip().split()) for s in page.splitlines() if s.strip()] for page in pages]
    years = " ".join(map(str, [year, year - 1] * (1 if q == 1 else 2)))
    period_header = ORDINALS[q - 1] + " Quarter"
    suffix = {1: "", 2: "First Six Months", 3: "First Nine Months", 4: "Full Year"}[q]
    for lines in page_lists:
        compact = {s.replace(" ", "").lower() for s in lines}
        if (
            years.replace(" ", "") not in compact
            or (period_header + suffix).replace(" ", "").lower() not in compact
        ):
            raise ValueError("Unrecognized Berkshire comparative periods")
    top, components = (table_rows(lines) for lines in page_lists)
    net = top["netearningsattributabletoberkshireshareholders"]
    operating = components["operatingearnings"]
    if (
        len(net) != (2 if q == 1 else 4)
        or top["operatingearnings"] != operating
        or any(len(components[k]) != len(net) for k in SEGMENTS)
    ):
        raise ValueError("Inconsistent operating-earnings reconciliation")
    if [sum(components[k][i] for k in SEGMENTS) for i in range(len(net))] != operating:
        raise ValueError("Berkshire segment contributions do not reconcile")
    statement = dict(
        label="버크셔 실적 발표",
        labelEn="Berkshire earnings release",
        published=published.isoformat(),
        periodEnd=end.isoformat(),
        url=url,
    )

    def make(scope, start_month, offset):
        periods = []
        for y in (year - 1, year):
            start = date(y, start_month, 1).isoformat()
            finish = date(y, end_month, calendar.monthrange(y, end_month)[1]).isoformat()
            n = end_month - start_month + 1
            periods.append(
                {
                    "label": f"{finish} 종료 {n}개월",
                    "labelEn": f"{n} months to {finish}",
                    "start": start,
                    "end": finish,
                }
            )

        def pair(values):
            return [values[offset + 1], values[offset]]

        segments = financial_table(
            "berkshire-operating-" + scope,
            (
                "사업별 세후 영업이익 (버크셔 기준)",
                "After-tax operating earnings by business (Berkshire definition)",
            ),
            periods,
            statement,
            [(identity, pair(components[key])) for key, identity in SEGMENTS.items()],
        )
        segments.update(
            measure="after-tax-operating-earnings",
            total=pair(operating),
            compositionKeys=[s[0] for s in SEGMENTS.values()],
            compositionPeriods=[p["label"] for p in periods],
            notes=[
                "투자손익과 일부 손상차손을 제외한 뒤, 보험·철도 등 각 사업이 이익에 얼마나 보탰는지 보여주는 버크셔의 세후 지표입니다."
            ],
            notesEn=[
                "Berkshire's non-GAAP measure excludes investment gains and losses and certain impairments. Amounts are after tax."
            ],
        )
        earnings = financial_table(
            "berkshire-net-" + scope,
            ("주주 귀속 순이익", "Net earnings attributable to Berkshire shareholders"),
            periods,
            statement,
            [(("net", "주주 귀속 순이익", "Net earnings attributable to shareholders"), pair(net))],
        )
        return [segments, earnings]

    quarter = make("quarter", end_month - 2, 0)
    if q == 1:
        return statement, {"interim": quarter}
    cumulative = make("annual" if q == 4 else "ytd", 1, 2)
    return statement, (
        {"annual": cumulative, "interim": quarter} if q == 4 else {"interim": quarter + cumulative}
    )


def refresh_berkshire(report, cik, fetch):
    if report["ticker"] != "BRK.B" or cik != 1067983:
        raise ValueError("Unexpected Berkshire issuer")
    indexes = news_indexes(fetch(HOME), HOME)
    if not indexes:
        raise ValueError("No current Berkshire news index")
    current = max(indexes)
    raw = fetch(indexes[current])
    entries = list(releases(raw, indexes[current]))
    if not any(x[1] == 4 for x in entries):
        prior = news_indexes(raw, indexes[current]).get(current - 1)
        if prior:
            entries.extend(releases(fetch(prior), prior))
    output = deepcopy(report)
    status = {"latest": [], "warnings": []}
    cache = {}
    for section in ("annual", "interim"):
        try:
            entry = max(e for e in entries if section == "interim" or e[1] == 4)
            if entry not in cache:
                file = PdfReader(BytesIO(fetch(entry[3])))
                if len(file.pages) < 2:
                    raise ValueError("Berkshire earnings breakdown is missing")
                cache[entry] = statements(
                    [p.extract_text(extraction_mode="layout") for p in file.pages[:2]], entry
                )
            src, parts = cache[entry]
            previous = report[section]
            if any(p.get("end", "") > src["periodEnd"] for table in previous for p in table["periods"]):
                raise ValueError("Berkshire release lags the existing report")
            tables = parts[section]
            identifiers = {t["id"] for t in tables}
            output[section] = tables + [t for t in previous if t["id"] not in identifiers]
            status["latest"].append({**src, "kind": section})
        except (KeyError, ValueError, OSError, IndexError, PyPdfError) as error:
            status["warnings"].append(f"{section}-unavailable ({error})")
    if not status["latest"]:
        raise ValueError("; ".join(status["warnings"]))
    return output, status
