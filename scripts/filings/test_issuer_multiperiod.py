import json
import unittest
from copy import deepcopy
from datetime import date
from html import escape
from unittest.mock import patch

from issuer_multiperiod import fourth_quarter, merck_annual, meta_quarter
from issuer_q4 import add_period_releases


def costco():
    return [
        [
            "Item 2.02. Results of Operations and Financial Condition",
            "On September 24, 2026, the Company issued a press release containing its operating results.",
        ],
        [
            "Exhibit 99.1",
            "COSTCO WHOLESALE CORPORATION REPORTS FOURTH QUARTER AND FISCAL YEAR 2026 OPERATING RESULTS",
        ],
        [
            "Press Release",
            "COSTCO WHOLESALE CORPORATION",
            "CONSOLIDATED STATEMENTS OF INCOME",
            "(dollars in millions, except per share data) (unaudited)",
            "16 Weeks Ended 52 Weeks Ended",
            "August 30,2026 August 31,2025 August 30,2026 August 31,2025",
            "Net sales $ 93,873 $ 84,432 $ 297,247 $ 269,912",
            "Membership fees 1,850 1,724 5,907 5,323",
            "Total revenue 95,723 86,156 303,154 275,235",
            "Operating income 3,801 3,341 11,685 10,383",
            "NET INCOME 2,998 2,610 9,226 8,099",
            "NET INCOME PER COMMON SHARE:",
        ],
    ]


def micron():
    names = [
        "Cloud Memory Business Unit",
        "Core Data Center Business Unit",
        "Mobile and Client Business Unit",
        "Automotive and Embedded Business Unit",
    ]
    business = ["Quarterly Business Unit Financial Results", "FQ4-26 FQ3-26 FQ4-25"]
    for i, name in enumerate(names, 1):
        business.extend([name, f"Revenue {i*20} {i*15} {i}"])
    return [
        [
            "Item 2.02. Results of Operations and Financial Condition.",
            "On September 30, 2026, Micron Technology, Inc. announced the fiscal results.",
        ],
        [
            "Exhibit 99.1",
            "MICRON TECHNOLOGY, INC. REPORTS RECORD FISCAL",
            "FOURTH-QUARTER AND FULL-YEAR 2026 RESULTS",
        ],
        business,
        [
            "MICRON TECHNOLOGY, INC.",
            "CONSOLIDATED STATEMENTS OF OPERATIONS",
            "(In millions, except per share amounts)",
            "(Unaudited)",
            "4th Qtr. 3rd Qtr. 4th Qtr. Year Ended",
            "September 3,2026 May 28,2026 August 28,2025 September 3,2026 August 28,2025",
            "Revenue 54,229 41,456 11,315 133,188 37,378",
            "Gross margin 47,047 35,056 5,054 107,504 14,873",
            "Operating income 43,751 33,318 3,654 99,340 9,770",
            "Net income 37,701 28,243 3,201 84,969 8,539",
        ],
        ["MICRON TECHNOLOGY, INC.", "RECONCILIATION OF GAAP TO NON-GAAP MEASURES", "Net income 9 9 9 9 9"],
    ]


def meta():
    return [
        [
            "Meta Reports Third Quarter 2025 Results",
            "MENLO PARK, Calif. – October 29, 2025 –",
            "Meta Platforms, Inc. (Nasdaq: META) today reported financial results for the quarter ended September 30, 2025.",
        ],
        [
            "META PLATFORMS, INC.",
            "CONDENSED CONSOLIDATED STATEMENTS OF INCOME",
            "(In millions, except per share amounts)",
            "(Unaudited)",
            "Three Months Ended September 30, Nine Months Ended September 30,",
            "2025 2024 2025 2024",
            "Revenue 108 94 205 182",
            "Income from operations 20 17 41 32",
            "Net income 18 13 38 29",
        ],
        [
            "Segment Information",
            "(In millions)",
            "(Unaudited)",
            "Three Months Ended Nine Months Ended",
            "September 30, September 30,",
            "2025 2024 2025 2024",
            "Revenue:",
            "Advertising 95 80 185 159",
            "Other revenue 8 9 10 13",
            "Family of Apps 103 89 195 172",
            "Reality Labs 5 5 10 10",
            "Total revenue 108 94 205 182",
            "Income (loss) from operations:",
            "Family of Apps 24 18 45 38",
            "Reality Labs (4) (1) (4) (6)",
        ],
    ]


class Releases(unittest.TestCase):
    def test_micron_reads_gaap_yoy_and_not_sequential_or_adjusted_columns(self):
        source, (segments, income) = fourth_quarter(
            "MU", micron(), "2026-09-30", "https://example.org/8k", date(2026, 9, 3)
        )
        self.assertEqual(source["filed"], source["published"])
        self.assertEqual(income["rows"][0]["values"], [11315, 54229])
        self.assertEqual(income["rows"][-1]["values"], [3201, 37701])
        self.assertEqual(segments["rows"][0]["values"], [1, 20])
        self.assertNotIn("start", income["periods"][0])
        changed = micron()
        changed[2][1] = "FQ4-26 FQ4-25 FQ3-26"
        with self.assertRaisesRegex(ValueError, "comparison reordered"):
            fourth_quarter("MU", changed, "2026-09-30", "url", date(2026, 9, 3))

    def test_costco_uses_sixteen_week_quarter_and_reconciles_membership_fees(self):
        src, (sales, income) = fourth_quarter("COST", costco(), "2026-09-24", "url", date(2026, 8, 30))
        self.assertEqual(sales["total"], [86156, 95723])
        self.assertEqual(income["rows"][-1]["values"], [2610, 2998])
        self.assertEqual(income["periods"][0]["start"], "2025-05-12")
        self.assertEqual(src["kind"], "interim")
        bad = costco()
        bad[-1][7] = "Membership fees 100 100 100 100"
        with self.assertRaisesRegex(ValueError, "reconcile"):
            fourth_quarter("COST", bad, "2026-09-24", "url", date(2026, 8, 30))

    def test_meta_keeps_quarter_and_ytd_separate_and_does_not_sum_parent_subtotal_twice(self):
        source, tables = meta_quarter(meta(), 2025, 3, "https://issuer.example/test")
        self.assertEqual(source["published"], "2025-10-29")
        self.assertNotIn("filed", source)
        self.assertEqual(tables[0]["compositionKeys"], ["foa", "rl"])
        self.assertEqual(tables[0]["total"], [94, 108])
        self.assertEqual(tables[3]["total"], [182, 205])
        self.assertEqual(tables[0]["periods"][-1]["start"], "2025-07-01")
        self.assertEqual(tables[3]["periods"][-1]["start"], "2025-01-01")
        bad = meta()
        bad[2][8] = "Other revenue 0 0 0 0"
        with self.assertRaisesRegex(ValueError, "reconcile"):
            meta_quarter(bad, 2025, 3, "url")
        with self.assertRaisesRegex(ValueError, "period inconsistent"):
            meta_quarter(meta(), 2024, 3, "url")

    def test_merck_validates_named_issuer_annual_columns_and_no_non_gaap_substitution(self):
        url = "https://www.merck.com/news/annual-example/"
        title = "Merck Announces Fourth-Quarter and Full-Year 2024 Financial Results"
        summary = [{"title": {"rendered": title}, "link": url, "date": "2025-02-05T07:00:00"}]
        income = [
            ["MERCK & CO., INC., RAHWAY, N.J., USA"],
            ["CONSOLIDATED STATEMENT OF INCOME - GAAP"],
            ["(AMOUNTS IN MILLIONS, EXCEPT PER SHARE FIGURES)"],
            ["GAAP", "% Change", "GAAP", "% Change"],
            ["4Q24", "4Q23", "Full Year 2024", "Full Year 2023"],
            ["Sales", "21", "20", "5%", "100", "89", "12%"],
            ["Income Before Taxes", "6", "5", "20%", "31", "21", "47%"],
            ["Net Income", "5", "4", "25%", "29", "19", "53%"],
        ]
        groups = [
            ["Year Ended"],
            ["$ in millions", "Dec. 31, 2024", "Dec. 31, 2023", "Change"],
            ["Total Sales", "100", "89"],
            ["Pharmaceutical", "85", "76"],
            ["Animal Health", "9", "8"],
            ["Other Revenues***", "6", "5"],
            ["WINREVAIR", "12", "10"],
        ]

        def doc():
            def grid(rows):
                return (
                    "<table>"
                    + "".join(
                        "<tr>" + "".join("<td>" + escape(v) + "</td>" for v in r) + "</tr>" for r in rows
                    )
                    + "</table>"
                )

            return (
                f'<link rel="canonical" href="{url}"><h1>{title}</h1><p>February 5, 2025</p>'
                + grid(income)
                + grid(groups)
            ).encode()

        def fetch(u):
            return doc() if u == url else json.dumps(summary)

        src, tables = merck_annual(fetch)
        self.assertEqual(src["published"], "2025-02-05")
        self.assertEqual(tables[0]["total"], [89, 100])
        self.assertEqual(tables[1]["rows"][-1]["values"], [19, 29])
        self.assertEqual(tables[2]["rows"][0]["values"], [10, 12])
        income[1][0] = "CONSOLIDATED STATEMENT OF INCOME - NON-GAAP"
        with self.assertRaisesRegex(ValueError, "GAAP"):
            merck_annual(fetch)

    def test_stale_release_never_replaces_a_newer_table(self):
        report = {
            "ticker": "META",
            "annual": [],
            "interim": [{"id": "prior", "periods": [{"end": "2025-12-31"}]}],
        }
        output = deepcopy(report)
        latest = []
        warnings = ["interim-unavailable (no fresh 10-Q)"]
        with patch(
            "issuer_q4.meta_latest", return_value=({"kind": "interim", "periodEnd": "2025-09-30"}, [])
        ):
            add_period_releases(None, report, output, latest, warnings, 1326801, None)
        self.assertEqual(output, report)
        self.assertEqual(latest, [])
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
