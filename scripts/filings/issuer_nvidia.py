"""Read NVIDIA's GAAP earnings tables between its earnings release and filing of the 10-Q."""

import re
from copy import deepcopy
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urljoin, urlsplit

from lxml import html
from issuer_native import financial_table
from pypdf.errors import PyPdfError

NEWS = "https://nvidianews.nvidia.com"
INDEX = NEWS + "/news?q=financial+results"
IR = "https://investor.nvidia.com/financial-info/financial-reports/"
NVIDIA_HOSTS = {"nvidianews.nvidia.com", "investor.nvidia.com", "s201.q4cdn.com"}
QUARTERS = {"first": 1, "second": 2, "third": 3, "fourth": 4}
ORDINAL = {number: name.title() for name, number in QUARTERS.items()}
ITEM = re.compile(
    r"/news/nvidia-announces-financial-results-for-(first|second|third|fourth)-quarter-(?:and-)?fiscal-(20\d{2})(?:-\d+)?/?$"
)
METRICS = {
    "Revenue": ("revenue", "매출", "Revenue"),
    "Cost of revenue": ("cost", "매출원가", "Cost of revenue"),
    "Gross profit": ("gross", "매출총이익", "Gross profit"),
    "Research and development": ("rd", "연구개발비", "Research and development"),
    "Sales, general and administrative": ("sga", "판매비·관리비", "Sales, general and administrative"),
    "Total operating expenses": ("opex", "영업비용", "Total operating expenses"),
    "Operating income": ("operating", "영업이익", "Operating income"),
    "Income before income tax": ("pretax", "세전이익", "Income before income tax"),
    "Income tax expense": ("tax", "법인세 비용", "Income tax expense"),
    "Net income": ("net", "순이익", "Net income"),
}


def archive(raw, url):
    entries, more = {}, None
    current_page = int(parse_qs(urlsplit(url).query).get("page", ["1"])[0])
    for a in html.fromstring(raw).xpath("//a[@href]"):
        href = urljoin(url, a.get("href"))
        parts = urlsplit(href)
        if parts.scheme != "https" or parts.netloc != "nvidianews.nvidia.com" or parts.fragment:
            continue
        match = ITEM.fullmatch(parts.path)
        if match and not parts.query:
            key = int(match[2]), QUARTERS[match[1]]
            if key in entries and entries[key] != href:
                raise ValueError("NVIDIA release archive has conflicting URLs")
            entries[key] = href
        elif (
            " ".join(a.text_content().split()).lower() == "next"
            and parts.path == "/news"
            and parse_qs(parts.query) == {"q": ["financial results"], "page": [str(current_page + 1)]}
        ):
            more = href
    return entries, more


def read_income(raw, fiscal_year, q, url):
    doc = html.fromstring(raw)
    title = " ".join(doc.xpath("string(//h1)").split())
    pattern = (
        f"NVIDIA Announces Financial Results for {ORDINAL[q]} Quarter "
        + ("(?:and )?" if q == 4 else "")
        + f"Fiscal {fiscal_year}"
    )
    if not re.fullmatch(pattern, title, re.I):
        raise ValueError("NVIDIA release issuer or fiscal quarter mismatch")
    dates = doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," article-date ")]')
    if len(dates) != 1:
        raise ValueError("NVIDIA release date missing")
    published = datetime.strptime(" ".join(dates[0].text_content().split()), "%B %d, %Y").date()
    header = "CONDENSED CONSOLIDATED STATEMENTS OF INCOME"
    found = []
    for table in doc.xpath("//table"):
        rows = []
        for tr in table.xpath("./tr|./thead/tr|./tbody/tr"):
            cells = [" ".join(c.text_content().split()) for c in tr.xpath("./td|./th")]
            if any(cells):
                rows.append([cell for cell in cells if cell and cell != "$"])
        if rows[:2] == [["NVIDIA CORPORATION"], [header]]:
            found.append(rows)
    if len(found) != 1:
        raise ValueError("NVIDIA GAAP income statement missing or ambiguous")
    rows = found[0]
    labels = ["Three Months Ended"] + (
        [{2: "Six Months Ended", 3: "Nine Months Ended", 4: "Twelve Months Ended"}[q]] if q > 1 else []
    )
    if ["(In millions, except per share data)"] not in rows[:5] or labels not in rows:
        raise ValueError("NVIDIA income units or period lengths changed")
    at = rows.index(labels)
    if len(rows[at + 1]) != len(labels) * 2 or len(rows[at + 2]) != len(labels) * 2:
        raise ValueError("NVIDIA missing comparison dates")
    ends = [
        datetime.strptime(day + " " + year, "%B %d, %Y").date()
        for day, year in zip(rows[at + 1], rows[at + 2])
    ]
    if q > 1 and ends[:2] != ends[2:]:
        raise ValueError("NVIDIA year-to-date and quarter end dates disagree")
    current, prior = ends[:2]
    month = {1: 4, 2: 7, 3: 10, 4: 1}[q]

    def in_fiscal_window(d):
        # A 52/53-week calendar can cross the month boundary by several days.
        first = date(d.year, month, 20)
        return d.weekday() == 6 and first <= d <= first + timedelta(days=17)

    if (
        current.year != (fiscal_year if q == 4 else fiscal_year - 1)
        or current.year != prior.year + 1
        or not all(in_fiscal_window(d) for d in (current, prior))
        or not current < published <= date.today()
        or (published - current).days > 150
    ):
        raise ValueError("NVIDIA fiscal and publication dates are inconsistent")
    data = {}
    for r in rows[at + 3 :]:
        if r[0] not in METRICS:
            continue
        numbers = r[1:]
        if (
            r[0] in data
            or len(numbers) != len(ends)
            or not all(
                re.fullmatch(r"\(?\d+(?:,\d{3})*\)?", n) and n.startswith("(") == n.endswith(")")
                for n in numbers
            )
        ):
            raise ValueError("Invalid NVIDIA GAAP metric " + r[0])
        data[r[0]] = [int(n.replace(",", "").replace("(", "-").replace(")", "")) for n in numbers]
    if data.keys() != METRICS.keys():
        raise ValueError("NVIDIA GAAP statement lacks required lines")
    for i in range(len(ends)):
        pairs = [
            ("Revenue", "Cost of revenue", "Gross profit"),
            ("Gross profit", "Total operating expenses", "Operating income"),
            ("Total operating expenses", "Research and development", "Sales, general and administrative"),
            ("Income before income tax", "Income tax expense", "Net income"),
        ]
        if any(data[a][i] - data[b][i] != data[c][i] for a, b, c in pairs):
            raise ValueError("NVIDIA consolidated GAAP statement does not reconcile")
    return (
        dict(
            label="NVIDIA 실적 발표",
            labelEn="NVIDIA earnings release",
            published=published.isoformat(),
            periodEnd=current.isoformat(),
            url=url,
        ),
        [prior, current],
        data,
    )


def report_tables(current, previous, fiscal_end, q):
    source, finish, metrics = current
    scopes = {}
    tables = {}
    headline = ["Revenue", "Operating income", "Net income"]
    display_order = headline + [name for name in METRICS if name not in headline]
    prior_ends = [("quarter", previous)]
    if q in (2, 3):
        prior_ends.append(("ytd", fiscal_end))
    elif q == 4:
        # The comparative annual columns also validate Q4 supplements. The audited
        # annual data published by the regulatory provider remains authoritative.
        prior_ends.append(("annual", fiscal_end))
    for k, (scope, previous_ends) in enumerate(prior_ends):
        periods = []
        for start_end, end in zip(previous_ends, finish):
            start = start_end + timedelta(days=1)
            duration = (end - start).days + 1
            if duration % 7 or not (84 <= duration <= 98 if not k else 84 * q <= duration <= 98 * q):
                raise ValueError("NVIDIA previous statement provides inconsistent fiscal start")
            months = 3 if not k else 3 * q
            periods.append(
                dict(
                    start=start.isoformat(),
                    end=end.isoformat(),
                    label=f"{end} 종료 {months}개월",
                    labelEn=f"{months} months to {end}",
                )
            )

        def pair(line):
            return [line[k * 2 + 1], line[k * 2]]

        scopes[scope] = (periods, pair(metrics["Revenue"]))
        tables[scope] = financial_table(
            "nvidia-gaap-" + scope,
            ("연결 손익 (GAAP)", "Consolidated GAAP results"),
            periods,
            source,
            [(METRICS[name], pair(metrics[name])) for name in display_order],
        )
    return scopes, tables


def check_regulatory_revenue(report, scopes):
    """A prior press release cannot contradict a 10-Q or later amendment already on file."""
    names = {"Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"}
    for table in report["interim"]:
        if not table["source"].get("filed") or table.get("measure") != "financial-results":
            continue
        for r in table["rows"]:
            if r["key"].split(":")[-1] not in names:
                continue
            existing = {
                (p["start"], p["end"]): v for p, v in zip(table["periods"], r["values"]) if v is not None
            }
            for periods, total in scopes.values():
                current = periods[-1]
                old = existing.get((current["start"], current["end"]))
                if old is not None and old != total[-1]:
                    raise ValueError("NVIDIA press revenue conflicts with a filed statement")


def rendered_disclosures(fiscal_year, quarter):
    """Read ordinary Downloads links when the public IR directory renders them with JavaScript."""
    from playwright.sync_api import Error as BrowserError, sync_playwright
    from issuer_nvidia_segments import nvidia_disclosure_links

    try:
        with sync_playwright() as engine:
            browser = engine.chromium.launch()
            try:
                page = browser.new_page()
                response = page.goto(IR, wait_until="domcontentloaded", timeout=18000)
                if not response or not response.ok or urlsplit(page.url).netloc != "investor.nvidia.com":
                    return {}
                page.locator('.module-financial-mashup a[href*=".pdf" i]').first.wait_for(
                    state="attached", timeout=7000
                )
                return nvidia_disclosure_links(page.content(), fiscal_year, quarter)
            finally:
                browser.close()
    except BrowserError:
        return {}


def refresh_nvidia(report, cik, fetch):
    if report["ticker"] != "NVDA" or cik != 1045810:
        raise ValueError("Unexpected NVIDIA issuer identity")
    listing = INDEX
    entries = {}
    for _ in range(7):
        chunk, more = archive(fetch(listing), listing)
        for key, url in chunk.items():
            if key in entries and entries[key] != url:
                raise ValueError("Conflicting NVIDIA release URLs")
            entries[key] = url
        if entries:
            fy, q = max(entries)
            previous = (fy, q - 1) if q > 1 else (fy - 1, 4)
            fy_end = (fy - 1, 4)
            if previous in entries and fy_end in entries:
                break
        if not more:
            break
        listing = more
    if not entries or previous not in entries or fy_end not in entries:
        raise ValueError("NVIDIA earnings archive lacks the current or preceding release")

    def load(key):
        return read_income(fetch(entries[key]), *key, entries[key])

    current = load((fy, q))
    source = current[0]
    if any(p["end"] > source["periodEnd"] for t in report["interim"] for p in t["periods"]):
        raise ValueError("A newer reporting period is already available")
    previous_ends = load(previous)[1]
    annual_ends = load(fy_end)[1] if fy_end != previous else previous_ends
    scopes, tables = report_tables(current, previous_ends, annual_ends, q)
    check_regulatory_revenue(report, scopes)
    warnings = []
    supplement = {scope: [] for scope in scopes}
    from issuer_nvidia_segments import nvidia_disclosure_links, nvidia_dimension_tables

    try:
        raw_ir = fetch(IR)
    except (OSError, ValueError):
        raw_ir = b"<html></html>"
    try:
        links = nvidia_disclosure_links(raw_ir, fy, q)
        if len(links) < 3 and b"apiMashup(" in raw_ir:
            links.update(rendered_disclosures(fy, q))
    except (OSError, ValueError, KeyError, IndexError) as error:
        links = {}
        warnings.append(f"interim-supplement-directory-unavailable ({error})")
    for kind in ("segments", "markets", "geography"):
        try:
            url = links[kind]
            groups = nvidia_dimension_tables(fetch(url), kind, url, source, scopes, fy, q)
            for scope in scopes:
                supplement[scope].extend(groups.get(scope, []))
        except (OSError, ValueError, KeyError, IndexError, PyPdfError) as error:
            warnings.append(f"interim-{kind}-unavailable ({error})")
    # The visible summary pairs the exact GAAP quarter and YTD from one release.
    # The full tables below it retain separately sourced, differently rounded breakdowns.
    interim = [scope for scope in scopes if scope != "annual"]
    fresh = [tables[scope] for scope in interim]
    for scope in interim:
        fresh.extend(supplement.get(scope, []))
    # A verified current 10-Q keeps priority. A failed supplemental fetch never erases
    # an existing set of company-sourced current-period classifications.
    ids = {t["id"] for t in fresh}
    rest = [t for t in report["interim"] if t["id"] not in ids]
    filed = [t for t in rest if t["source"]["periodEnd"] == source["periodEnd"] and t["source"].get("filed")]
    prior = [t for t in rest if t not in filed]
    out = deepcopy(report)
    out["interim"] = filed + fresh + prior
    return out, {"latest": [{**source, "kind": "interim"}], "warnings": warnings}
