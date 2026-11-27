"""Read dated primary releases when a filing directory omits a comparable period."""

from calendar import monthrange
from datetime import date, datetime, timedelta
from html import unescape
from io import BytesIO
import json
import re
from urllib.parse import urlsplit

from lxml import html
from pypdf import PdfReader

from issuer_native import financial_table


META_CDN = "s21.q4cdn.com"
MRK_LIST = "https://www.merck.com/wp-json/wp/v2/news_item?search=full-year%20financial%20results&per_page=12&_fields=date,link,title"
FULL_DATE = r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},\s*\d{4}"
GAAP = {
    "sales": ("매출", "Revenue"),
    "op": ("영업이익", "Operating income"),
    "net": ("순이익", "Net income"),
    "gross": ("매출총이익", "Gross profit"),
}


def insist(ok, message):
    if not ok:
        raise ValueError(message)


def full_date(s):
    return datetime.strptime(re.sub(r",\s*", ", ", s), "%B %d, %Y").date()


def cells(node):
    return " ".join(" ".join(node.itertext()).split())


def period(d, start=None):
    p = {"label": d.isoformat(), "labelEn": d.isoformat(), "end": d.isoformat()}
    if start:
        p["start"] = start.isoformat()
    return p


def numeric(s):
    insist(
        re.fullmatch(r"(?:\(?\d[\d,]*\)?|[—–-])", s) and (s.startswith("(") == s.endswith(")")),
        "Unexpected financial table amount",
    )
    return 0 if s in {"—", "–", "-"} else int(s.replace(",", "").replace("(", "-").replace(")", ""))


def amounts(lines, title, count, idx):
    data = [
        s[len(title) + 1 :].replace("$", "").split()
        for s in lines
        if re.match(re.escape(title) + r"\s+[$(\d—–-]", s)
    ]
    insist(len(data) == 1 and len(data[0]) == count, "Ambiguous or missing financial statement row: " + title)
    ns = [numeric(v) for v in data[0]]
    return [ns[i] for i in idx]


def table(prefix, suffix, ko, en, dates, source, items):
    return financial_table(
        prefix + "-" + suffix, (ko, en), dates, source, [((key, k, e), vals) for key, k, e, vals in items]
    )


def metrics(lines, names, count, idx):
    return [(key, *GAAP[key], amounts(lines, label, count, idx)) for key, label in names.items()]


def income_page(pages, issuer, title):
    choices = [p for p in pages if issuer in p[:3] and title in p[:4]]
    insist(len(choices) == 1, "Missing unique consolidated GAAP statement")
    return choices[0]


def pdf_pages(data):
    insist(data.startswith(b"%PDF-") and len(data) <= 16_000_000, "Invalid issuer release PDF")
    reader = PdfReader(BytesIO(data))
    insist(0 < len(reader.pages) <= 120, "Unexpected issuer release page count")
    return [
        [
            " ".join(s.split())
            for s in (pg.extract_text(extraction_mode="layout") or "").splitlines()
            if s.strip()
        ]
        for pg in reader.pages
    ]


def fourth_quarter(ticker, pages, filed, url, expected):
    """The 8-K exhibit explicitly prints current and prior-year fourth-quarter results."""
    combined = " ".join(" ".join(p) for p in pages[:5])
    insist("Item 2.02." in combined and "Exhibit 99.1" in combined, "Missing earnings exhibit")
    published = re.search(
        r"\bOn (" + FULL_DATE + r"), .{0,160}(?:issued a press release|announced)", combined, re.I
    )
    insist(published, "Missing earnings announcement date")
    announced = full_date(published[1])
    y = expected.year
    insist(expected < announced <= date.fromisoformat(filed), "Announcement date inconsistent with filing")
    source = {
        "url": url,
        "periodEnd": expected.isoformat(),
        "filed": filed,
        "published": announced.isoformat(),
        "label": "8-K 첨부 99.1 · 4분기 실적",
        "labelEn": "8-K Exhibit 99.1 · fourth-quarter earnings",
    }
    if ticker == "COST":
        lines = income_page(pages, "COSTCO WHOLESALE CORPORATION", "CONSOLIDATED STATEMENTS OF INCOME")
        insist(
            f"FOURTH QUARTER AND FISCAL YEAR {y} OPERATING RESULTS" in combined
            and "(dollars in millions, except per share data) (unaudited)" in lines,
            "Costco income statement period or units unrecognized",
        )
        span = next(
            (
                re.fullmatch(r"(16|17) Weeks Ended (52|53) Weeks Ended", s)
                for s in lines
                if " Weeks Ended" in s
            ),
            None,
        )
        insist(span, "Costco comparison weeks differ or are not explicitly stated")
        idx = lines.index(span[0])
        days = [full_date(s) for s in re.findall(FULL_DATE, lines[idx + 1])]
        insist(
            len(days) == 4
            and days == [expected, days[1], expected, days[1]]
            and 356 <= (expected - days[1]).days <= 373,
            "Costco comparison end dates changed",
        )
        duration = int(span[1]) * 7 - 1
        periods = [period(d, d - timedelta(days=duration)) for d in (days[1], expected)]
        rows = metrics(
            lines, {"sales": "Total revenue", "op": "Operating income", "net": "NET INCOME"}, 4, (1, 0)
        )
        products = [
            ("store", "상품 순매출", "Net sales", amounts(lines, "Net sales", 4, (1, 0))),
            ("fees", "회원비", "Membership fees", amounts(lines, "Membership fees", 4, (1, 0))),
        ]
        insist(
            [a + b for a, b in zip(products[0][3], products[1][3])] == rows[0][3],
            "Costco sales do not reconcile",
        )
        sales = table(
            "cost",
            "quarter-revenue",
            "상품 매출과 회원비 · 4분기",
            "Merchandise and membership revenue · Q4",
            periods,
            source,
            products,
        )
        sales.update(
            measure="revenue",
            total=rows[0][3],
            compositionKeys=["store", "fees"],
            compositionPeriods=[p["label"] for p in periods],
        )
    elif ticker == "MU":
        lines = income_page(pages, "MICRON TECHNOLOGY, INC.", "CONSOLIDATED STATEMENTS OF OPERATIONS")
        insist(
            f"FOURTH-QUARTER AND FULL-YEAR {y} RESULTS" in combined
            and "(In millions, except per share amounts)" in lines
            and "4th Qtr. 3rd Qtr. 4th Qtr. Year Ended" in lines,
            "Micron GAAP period or units unrecognized",
        )
        days = [
            full_date(s)
            for s in re.findall(FULL_DATE, lines[lines.index("4th Qtr. 3rd Qtr. 4th Qtr. Year Ended") + 1])
        ]
        insist(
            len(days) == 5
            and days == [expected, days[1], days[2], expected, days[2]]
            and 356 <= (expected - days[2]).days <= 373
            and 82 <= (expected - days[1]).days <= 99,
            "Micron comparison end dates changed",
        )
        periods = [period(days[2]), period(expected, days[1] + timedelta(days=1))]
        rows = metrics(
            lines,
            {"sales": "Revenue", "gross": "Gross margin", "op": "Operating income", "net": "Net income"},
            5,
            (2, 0),
        )
        section = [p for p in pages if "Quarterly Business Unit Financial Results" in p]
        insist(len(section) == 1, "Missing Micron business-unit disclosure")
        units = section[0][section[0].index("Quarterly Business Unit Financial Results") + 1 :]
        insist(
            units[0] == f"FQ4-{y%100:02d} FQ3-{y%100:02d} FQ4-{(y-1)%100:02d}",
            "Micron unit comparison reordered",
        )
        titles = {
            "Cloud Memory Business Unit": "클라우드 메모리",
            "Core Data Center Business Unit": "코어 데이터센터",
            "Mobile and Client Business Unit": "모바일·클라이언트",
            "Automotive and Embedded Business Unit": "자동차·임베디드",
        }
        insist(
            {s for s in units if s.endswith("Business Unit")} == titles.keys(),
            "Micron business-unit presentation changed",
        )
        products = [
            (
                name,
                ko,
                name,
                amounts(units[units.index(name) + 1 : units.index(name) + 2], "Revenue", 3, (2, 0)),
            )
            for name, ko in titles.items()
        ]
        sales = table(
            "mu",
            "quarter-business-units",
            "사업부별 매출 · 4분기",
            "Business-unit revenue · Q4",
            periods,
            source,
            products,
        )
    else:
        raise ValueError("Unsupported fourth-quarter issuer")
    income = table(
        ticker.lower(),
        "quarter-gaap",
        "연결 실적 · 4분기",
        "Consolidated GAAP results · Q4",
        periods,
        source,
        rows,
    )
    return dict(source, kind="interim"), [sales, income]


def meta_quarter(pages, year, quarter, url):
    heading = ("First", "Second", "Third", "Fourth")[quarter - 1]
    opening = " ".join(pages[0])
    insist(
        opening.startswith(f"Meta Reports {heading} Quarter")
        and "Meta Platforms, Inc. (Nasdaq: META)" in opening,
        "Wrong Meta earnings release",
    )
    match = re.search(
        r"MENLO PARK, Calif\.\s*[–—-]\s*(" + FULL_DATE + r")\s*[–—-].*?quarter ended (" + FULL_DATE + r")",
        opening,
    )
    insist(match, "Missing Meta earnings release dateline")
    published, end = full_date(match[1]), full_date(match[2])
    insist(
        end == date(year, quarter * 3, monthrange(year, quarter * 3)[1]) and end < published <= date.today(),
        "Meta reporting period inconsistent with directory",
    )
    lines = income_page(pages, "META PLATFORMS, INC.", "CONDENSED CONSOLIDATED STATEMENTS OF INCOME")
    insist("(In millions, except per share amounts)" in lines, "Missing Meta statement units")
    sections = [p for p in pages if "Segment Information" in p and "(In millions)" in p and "Revenue:" in p]
    insist(len(sections) == 1, "Meta segment disclosure unavailable")
    segments = sections[0]
    stamp = end.strftime("%B") + f" {end.day},"
    periods_label = {1: "", 2: "Six Months", 3: "Nine Months", 4: "Year"}[quarter]
    total_cols = 2 if quarter == 1 else 4
    expected_years = " ".join([str(year), str(year - 1)] * (total_cols // 2))
    for sheet in (lines, segments):
        insist(expected_years in sheet, "Meta comparison columns changed")
        before = " ".join(sheet[max(0, sheet.index(expected_years) - 3) : sheet.index(expected_years)])
        insist(
            "Three Months Ended" in before
            and stamp in before
            and (quarter == 1 or (periods_label + " Ended") in before),
            "Meta comparison interval changed",
        )
    source = {
        "url": url,
        "label": "메타 분기 실적 발표",
        "labelEn": "Meta quarterly earnings release",
        "published": published.isoformat(),
        "periodEnd": end.isoformat(),
    }
    result = []
    for ytd in [False, True] if quarter > 1 else [False]:
        idx = (3, 2) if ytd else (1, 0)
        dates = [
            period(date(y, end.month, end.day), date(y, 1 if ytd else end.month - 2, 1))
            for y in [year - 1, year]
        ]
        names = ("연초 누계", "year to date", "ytd") if ytd else ("분기", "quarter", "quarter")
        rows = metrics(
            lines, {"sales": "Revenue", "op": "Income from operations", "net": "Net income"}, total_cols, idx
        )
        rev = segments[segments.index("Revenue:") + 1 : segments.index("Income (loss) from operations:")]
        sets = [
            (key, k, eng, amounts(rev, eng, total_cols, idx))
            for key, k, eng in [
                ("foa", "패밀리 오브 앱스", "Family of Apps"),
                ("rl", "리얼리티 랩스", "Reality Labs"),
            ]
        ]
        total = amounts(rev, "Total revenue", total_cols, idx)
        insist(
            total == rows[0][3] == [a + b for a, b in zip(sets[0][3], sets[1][3])],
            "Meta segment sales do not reconcile",
        )
        mix = table(
            "meta",
            "segments-" + names[2],
            "사업부별 매출 · " + names[0],
            "Segment revenue · " + names[1],
            dates,
            source,
            sets,
        )
        mix.update(
            measure="revenue",
            total=total,
            compositionKeys=["foa", "rl"],
            compositionPeriods=[p["label"] for p in dates],
        )
        detail = [
            (key, k, eng, amounts(rev, eng, total_cols, idx))
            for key, k, eng in [("ads", "광고", "Advertising"), ("other", "기타", "Other revenue")]
        ]
        insist(
            sets[0][3] == [a + b for a, b in zip(detail[0][3], detail[1][3])],
            "Meta Family of Apps revenue does not reconcile",
        )
        result.extend(
            [
                mix,
                table(
                    "meta",
                    "income-" + names[2],
                    "연결 실적 · " + names[0],
                    "Consolidated GAAP results · " + names[1],
                    dates,
                    source,
                    rows,
                ),
                table(
                    "meta",
                    "foa-" + names[2],
                    "패밀리 오브 앱스 매출 · " + names[0],
                    "Family of Apps revenue · " + names[1],
                    dates,
                    source,
                    detail,
                ),
            ]
        )
    return dict(source, kind="interim"), result


def merck_annual(fetch):
    candidates = []
    for item in json.loads(fetch(MRK_LIST)):
        title = unescape(item["title"]["rendered"])
        m = re.search(r"\bAnnounces Fourth-Quarter and Full-Year (\d{4}) Financial Results\b", title, re.I)
        url = urlsplit(item["link"])
        if (
            m
            and url.scheme == "https"
            and url.netloc == "www.merck.com"
            and url.path.startswith("/news/")
            and not url.query
        ):
            candidates.append((int(m[1]), title, item["link"], date.fromisoformat(item["date"][:10])))
    insist(candidates, "Missing Merck full-year release")
    year, title, url, published = max(candidates)
    doc = html.fromstring(fetch(url))
    insist(
        doc.xpath('//link[@rel="canonical"]/@href') == [url]
        and [cells(h) for h in doc.xpath("//h1")] == [title]
        and f"{published.strftime('%B')} {published.day}, {published.year}" in cells(doc)
        and date(year, 12, 31) < published <= date.today(),
        "Merck release identity or date mismatch",
    )
    tables = []
    for t in doc.xpath("//table"):
        rows = [
            [v for col in tr.xpath("./td|./th") if (v := cells(col)) and v != "$"]
            for tr in t.xpath("./tr|./thead/tr|./tbody/tr")
        ]
        tables.append([r for r in rows if r])
    sy = [str(year), str(year - 1)]
    income = [
        t
        for t in tables
        if t[:3]
        == [
            ["MERCK & CO., INC., RAHWAY, N.J., USA"],
            ["CONSOLIDATED STATEMENT OF INCOME - GAAP"],
            ["(AMOUNTS IN MILLIONS, EXCEPT PER SHARE FIGURES)"],
        ]
    ]
    insist(
        len(income) == 1
        and ["GAAP", "% Change", "GAAP", "% Change"] in income[0]
        and [f"4Q{year%100:02d}", f"4Q{(year-1)%100:02d}", *(f"Full Year {s}" for s in sy)] in income[0],
        "Merck GAAP comparison columns changed",
    )

    def annual_values(grid, name, offset, width=None):
        matches = [r for r in grid if re.sub(r"\*+$", "", r[0]) == name]
        insist(len(matches) == 1 and (not width or len(matches[0]) == width), "Missing Merck statement row")
        return [numeric(matches[0][i].replace("$", "").strip()) for i in (offset + 1, offset)]

    dates = [period(date(y, 12, 31), date(y, 1, 1)) for y in (year - 1, year)]
    source = {
        "url": url,
        "periodEnd": dates[-1]["end"],
        "published": published.isoformat(),
        "label": "머크 연간 실적 발표",
        "labelEn": "Merck annual earnings release",
    }
    metrics_ = [
        (k, ko, en, annual_values(income[0], line, 4, 7))
        for k, ko, en, line in [
            ("sales", "매출", "Revenue", "Sales"),
            ("pretax", "세전이익", "Income before taxes", "Income Before Taxes"),
            ("net", "연결 순이익", "Consolidated net income", "Net Income"),
        ]
    ]
    split = [
        t
        for t in tables
        if t[0] == ["Year Ended"] and t[1][:3] == ["$ in millions", *(f"Dec. 31, {v}" for v in sy)]
    ]
    insist(len(split) == 1, "Merck annual sales table changed")
    categories = [
        (key, k, en, annual_values(split[0], name, 1))
        for key, k, en, name in [
            ("rx", "의약품", "Pharmaceutical", "Pharmaceutical"),
            ("animal", "동물의약품", "Animal Health", "Animal Health"),
            ("other", "기타 매출", "Other revenues", "Other Revenues"),
        ]
    ]
    total = annual_values(split[0], "Total Sales", 1)
    insist(
        total == metrics_[0][3] == [sum(i) for i in zip(*(r[3] for r in categories))],
        "Merck annual sales do not reconcile",
    )
    mix = table(
        "merck", "annual-sales", "사업별 연간 매출", "Annual revenue by business", dates, source, categories
    )
    mix.update(
        measure="revenue",
        total=total,
        compositionKeys=[r[0] for r in categories],
        compositionPeriods=[p["label"] for p in dates],
    )
    # Product combinations use the issuer's reported labels in both years.
    products = [
        (label, label, label, annual_values(split[0], label, 1))
        for label in ("KEYTRUDA/KEYTRUDA QLEX", "GARDASIL/GARDASIL 9", "WINREVAIR")
        if any(r[0] == label for r in split[0])
    ]
    result = [
        mix,
        table(
            "merck",
            "annual-gaap",
            "연간 연결 실적",
            "Annual consolidated GAAP results",
            dates,
            source,
            metrics_,
        ),
    ]
    if products:
        result.append(
            table(
                "merck",
                "annual-products",
                "주요 의약품 매출",
                "Selected medicine sales",
                dates,
                source,
                products,
            )
        )
    return dict(source, kind="annual"), result
