"""Alphabet's product notes use two axes: Google Services and its disclosed product."""

from copy import deepcopy


SEGMENTS = ("GoogleServicesMember", "GoogleCloudMember", "AllOtherSegmentsMember")
ADVERTISING = ("GoogleSearchOtherMember", "YouTubeAdvertisingRevenueMember", "GoogleNetworkMember")
AD_TOTAL = "GoogleAdvertisingRevenueMember"
SUBSCRIPTIONS = "SubscriptionsPlatformsAndDevicesRevenueMember"
SERVICES_PRODUCTS = "GoogleServicesProductOrServiceAxis"


def segment_dimension(members, cik):
    pairs = [(m.get("dimension", "").split(":")[-1], (m.text or "").split(":")[-1]) for m in members]
    if len(pairs) == 1:
        return pairs[0]
    # Never flatten unrelated axes or add product rows a second time to segment revenue.
    if int(cik) == 1652044 and len(pairs) == 2:
        axes = dict(pairs)
        if axes.get("StatementBusinessSegmentsAxis") == SEGMENTS[0] and "ProductOrServiceAxis" in axes:
            return SERVICES_PRODUCTS, axes["ProductOrServiceAxis"]
    return None


def alphabet_tables(report, filing, currency, spans, observations, dimensional, amount, table_base):
    """Retain the product hierarchy only when both disclosed subtotals reconcile exactly."""
    reference = next((t for t in report["annual"] if t["id"] == "segments"), None)
    total_revenue = next(
        (values for key, values in observations.items() if key[:2] == ("us-gaap", "Revenues")), None
    )
    customer_revenue = ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax")
    if not reference or not total_revenue:
        return []
    result = []
    products = {AD_TOTAL, *ADVERTISING, SUBSCRIPTIONS}
    for frequency, periods in spans:
        columns = []
        totals = []
        for period in periods:
            total = total_revenue.get(period)
            segments = dimensional.get((*customer_revenue, "StatementBusinessSegmentsAxis", period), {})
            children = dimensional.get((*customer_revenue, SERVICES_PRODUCTS, period), {})
            if total is None or set(segments) != set(SEGMENTS) or set(children) != products:
                break
            values = {**segments, **children}
            if any(len(v) != 1 or min(v) < 0 for v in values.values()):
                break
            values = {k: next(iter(v)) for k, v in values.items()}
            if (
                sum(values[k] for k in ADVERTISING) != values[AD_TOTAL]
                or values[AD_TOTAL] + values[SUBSCRIPTIONS] != values[SEGMENTS[0]]
            ):
                break
            values["__residual"] = total - sum(values[k] for k in SEGMENTS)
            columns.append(values)
            totals.append(amount(total))
        if len(columns) != len(periods):
            continue
        ko, en = {
            "annual": ("연간", "annual"),
            "quarter": ("분기", "quarter"),
            "half": ("6개월", "six months"),
            "nine-months": ("9개월", "nine months"),
        }[frequency]
        table = table_base(
            "sec-alphabet-" + frequency,
            "사업부문·광고별 매출 · " + ko,
            "Segment and advertising revenue · " + en,
            filing,
            currency,
            periods,
        )
        for template in reference["rows"]:
            key = template["key"]
            if key not in columns[0]:
                continue
            row = deepcopy(template)
            row["values"] = [amount(c[key]) for c in columns]
            if key == "__residual":
                row.update(ko="연결 매출과 세 부문 합계의 차이", en="Difference to consolidated revenue")
            table["rows"].append(row)
        if {r["key"] for r in table["rows"]} != set(columns[0]):
            continue
        table.update(
            measure="revenue",
            total=totals,
            compositionKeys=list(SEGMENTS),
            compositionPeriods=[p["label"] for p in table["periods"]],
            notes=[
                "검색·YouTube·네트워크 광고는 광고 합계에 들어갑니다. 광고와 구독·플랫폼·기기를 합친 금액이 Google 서비스 매출입니다."
            ],
            notesEn=[
                "Search, YouTube and Network make up advertising revenue. Advertising and subscriptions, platforms and devices make up Google Services revenue."
            ],
        )
        result.append(table)
    return result
