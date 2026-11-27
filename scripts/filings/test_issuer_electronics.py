import unittest
from copy import deepcopy
from datetime import date
from html import escape
from unittest.mock import patch

import issuer_electronics as filings


def adi_fixture(q=4):
    if q == 4:
        fy, ending, prior, cum, label, day = (
            2025,
            "Nov. 1, 2025",
            "Nov. 2, 2024",
            "Twelve",
            "Fourth Quarter and Fiscal",
            date(2025, 11, 25),
        )
    else:
        fy, ending, prior, cum, label, day = (
            2025,
            "Aug. 2, 2025",
            "Aug. 3, 2024",
            "Nine",
            "Fiscal Third Quarter",
            date(2025, 8, 19),
        )
    title = f"Analog Devices Reports {label} {fy} Financial Results"
    path = "/news-releases/" + title.lower().replace(" ", "-") + "-302948778.html"
    url = "https://www.prnewswire.com" + path

    def table(rows):
        return (
            "<table>"
            + "".join("<tr>" + "".join("<td>" + escape(v) + "</td>" for v in r) + "</tr>" for r in rows)
            + "</table>"
        )

    statement = [
        [
            "ANALOG DEVICES, INC. CONSOLIDATED STATEMENTS OF INCOME (Unaudited) (In thousands, except per share amounts)"
        ],
        ["Three Months Ended", cum + " Months Ended"],
        [ending, prior, ending, prior],
    ]
    for name, sums in [
        ("Revenue", [100, 80, 900, 800]),
        ("Gross margin", [75, 50, 510, 420]),
        ("Operating income", [30, 19, 260, 210]),
        ("Net income", [25, 10, 200, 170]),
    ]:
        statement.append([name, *map(str, sums)])
    markets = []
    for caption, values in [
        ("Three", [(60, 52), (20, 15), (15, 10), (5, 3)]),
        (cum, [(550, 460), (230, 211), (70, 79), (50, 50)]),
    ]:
        markets.extend(
            [
                [caption + " Months Ended"],
                [ending, prior],
                ["Revenue", "% of Revenue 1", "Y/Y%", "Revenue", "% of Revenue 1"],
            ]
        )
        for (current, old), key in zip(values, filings.ADI_MARKETS):
            markets.append([key, str(current), "25 %", "12 %", str(old), "12 %"])
        markets.append(
            [
                "Total revenue",
                str(sum(r[0] for r in values)),
                "100 %",
                "10 %",
                str(sum(r[1] for r in values)),
                "100 %",
            ]
        )
    release = (
        f'<link rel="canonical" href="{url}"><meta name="date" content="{day.isoformat()}T19:00:00Z">'
        f'<h1>{title}</h1><a href="/news/analog-devices%2C-inc./">Analog Devices, Inc.</a>'
        + table(statement)
        + table(markets)
        + table([["GAAP TO NON-GAAP RECONCILIATION"], ["Adjusted revenue", "999", "999"]])
    ).encode()
    return release, (fy, q, day, url)


class Analog(unittest.TestCase):
    def test_year_and_quarter_weights_reconcile_without_misrepresenting_chip_sales_channels(self):
        raw, entry = adi_fixture()
        annual, (markets, profit) = filings.adi_statement(raw, entry, "annual")
        quarter, tables = filings.adi_statement(raw, entry, "interim")
        self.assertEqual(markets["rows"][0]["values"], [460, 550])
        self.assertEqual(profit["rows"][0]["values"], [800, 900])
        self.assertEqual(tables[0]["total"], [80, 100])
        self.assertEqual(markets["unitEn"], "USD thousand")
        self.assertEqual(
            markets["compositionKeys"], ["industrial", "automotive", "communications", "consumer"]
        )
        self.assertEqual(quarter["published"], "2025-11-25")
        self.assertNotIn("filed", annual)

    def test_interim_ytd_is_separate_and_schema_errors_preserve_prior_data(self):
        raw, entry = adi_fixture(3)
        _, ts = filings.adi_statement(raw, entry, "interim")
        self.assertEqual(
            [t["id"] for t in ts],
            ["adi-end-markets-quarter", "adi-gaap-quarter", "adi-end-markets-ytd", "adi-gaap-ytd"],
        )
        self.assertIn("Nine months", ts[2]["periods"][-1]["labelEn"])
        with self.assertRaisesRegex(ValueError, "reconcile"):
            filings.adi_statement(
                raw.replace(b"<td>Industrial</td><td>60</td>", b"<td>Industrial</td><td>59</td>"),
                entry,
                "interim",
            )
        with self.assertRaisesRegex(ValueError, "amount and percentage"):
            filings.adi_statement(raw.replace(b"Y/Y%", b"sequential growth"), entry, "interim")
        with self.assertRaisesRegex(ValueError, "publication|release date"):
            filings.adi_statement(raw.replace(b"2025-08-19T", b"2025-08-18T"), entry, "interim")

    def test_lists_only_dated_actual_results_and_follows_issuer_pagination_for_annual(self):
        q, q_entry = adi_fixture(3)
        annual, a = adi_fixture()

        def item(entry):
            return (
                '<a href="'
                + entry[-1]
                + '">'
                + entry[2].strftime("%b %d, %Y")
                + ", 07:00 ET financial results</a>"
            )

        pages = {
            filings.ADI: (
                item(q_entry)
                + '<a href="/news-releases/analog-devices-to-report-fiscal-third-quarter-2025-financial-results-299.html">Aug 1, 2025, To report</a>'
                + '<a href="?page=2&amp;pagesize=25">2</a>'
            ).encode(),
            filings.ADI + "?page=2&pagesize=25": item(a).encode(),
        }
        found = filings.adi_entries(pages.__getitem__)
        self.assertEqual(found["annual"], a)
        self.assertEqual(found["interim"], a)


def pltr_fixture():
    filing = "https://issuer.example.test/filing"
    periods = [
        {"start": "2024-07-01", "end": "2024-09-30", "label": "2024Q3"},
        {"start": "2025-07-01", "end": "2025-09-30", "label": "2025Q3"},
    ]
    table = {
        "id": "sec-consolidated-quarter",
        "periods": periods,
        "source": {"url": filing},
        "rows": [
            {"key": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "values": [11.5, 21.75]}
        ],
    }
    body = '<x:unit id="usd"><x:measure>iso:USD</x:measure></x:unit>'
    for i, period in enumerate(periods):
        for name, vals in [
            ("GovernmentOperatingSegmentMember", [8_000_000, 10_000_000]),
            ("CommercialMember", [3_500_000, 11_750_000]),
        ]:
            for geography in [True, False]:
                ctx = f"{i}-{name}-{geography}"
                body += f'<x:context id="{ctx}"><x:entity><x:identifier>0001321655</x:identifier><x:segment>'
                body += '<d:explicitMember dimension="srt:ConsolidationItemsAxis">us-gaap:OperatingSegmentsMember</d:explicitMember>'
                body += f'<d:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">pltr:{name}</d:explicitMember>'
                if geography:
                    body += '<d:explicitMember dimension="srt:CountryAxis">country:US</d:explicitMember>'
                body += f'</x:segment></x:entity><x:period><x:startDate>{period["start"]}</x:startDate><x:endDate>{period["end"]}</x:endDate></x:period></x:context>'
                body += f'<us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="{ctx}" unitRef="usd">{999999 if geography else vals[i]}</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>'
    return (
        f'<x:xbrl xmlns:x="http://www.xbrl.org/2003/instance" xmlns:d="http://xbrl.org/2006/xbrldi" xmlns:iso="http://www.xbrl.org/2003/iso4217" xmlns:us-gaap="http://fasb.org/us-gaap/2025">{body}</x:xbrl>'.encode(),
        table,
        filing,
    )


class Palantir(unittest.TestCase):
    def test_uses_only_global_customer_segments_and_matches_both_consolidated_totals(self):
        raw, t, url = pltr_fixture()
        (result,) = filings.pltr_market_tables(raw, [t], {"url": url})
        self.assertEqual(result["total"], [11.5, 21.75])
        self.assertEqual(result["rows"][0]["values"], [8, 10])
        self.assertEqual(result["rows"][1]["values"], [3.5, 11.75])
        t["rows"][0]["values"][0] = 32
        with self.assertRaisesRegex(ValueError, "does not match"):
            filings.pltr_market_tables(raw, [t], {"url": url})

    def test_real_filing_date_and_matching_issuer_required_for_download(self):
        u = "https://" + filings.CDN + "/CIK-0001321655/abc."

        def row(form, ticker=u):
            return f'<div class="file-container"><p class="date">11 / 03 / 25</p><a href="{ticker}zip">XBRL</a><a href="{ticker}html">XBRL_HTML</a><p class="file-type"><span>{form}</span></p></div>'

        self.assertEqual(filings.filing_entries(row("10-Q"), "10-Q"), ("2025-11-03", u + "html", u + "zip"))
        self.assertIsNone(filings.filing_entries(row("10-Q/A"), "10-Q"))
        self.assertIsNone(filings.filing_entries(row("10-K", u.replace("1321655", "1231234")), "10-K"))

    def test_rejects_stale_or_wrong_issuer_instead_of_overwriting_source(self):
        packet = {
            "ticker": "ADI",
            "annual": [{"id": "old", "source": {}, "periods": [{"end": "2027-01-01"}]}],
            "interim": [{"id": "old", "source": {}, "periods": [{"end": "2027-01-01"}]}],
        }
        before = deepcopy(packet)
        raw, entry = adi_fixture()
        with patch.object(filings, "adi_entries", return_value={"annual": entry, "interim": entry}):
            with self.assertRaisesRegex(ValueError, "predates"):
                filings.refresh_electronics(packet, 6281, lambda _: raw)
        self.assertEqual(packet, before)
        with self.assertRaisesRegex(ValueError, "CIK"):
            filings.refresh_electronics(packet, 1, lambda _: raw)


if __name__ == "__main__":
    unittest.main()
