from datetime import date
import unittest
from issuer_berkshire import releases, statements


class BerkshireDisclosure(unittest.TestCase):
    release = (2025, 3, date(2025, 11, 1), "https://www.berkshirehathaway.com/news/nov0125.pdf")
    front = """BERKSHIRE HATHAWAY INC.     BRK.B
FOR IMMEDIATE RELEASE November 1, 2025
Dollar amounts are in millions.
Third Quarter   First Nine Months
2025 2024 2025 2024
Net earnings attributable to Berkshire shareholders   14 12 22 18
Operating earnings   9 10 20 16"""
    back = """Third Quarter   First Nine Months
2025 2024 2025 2024
Insurance-underwriting   (1) 2 4 2
Insurance-investment income   2 2 3 3
BNSF   1 1 2 2
Berkshire Hathaway Energy Company   3 2 4 4
Manufacturing, service and retailing   3 2 4 3
Other*   1 1 3 2
Operating earnings   9 10 20 16"""

    def test_quarter_and_year_to_date_are_after_tax_and_separate(self):
        src, sections = statements([self.front, self.back], self.release)
        quarter, net, ytd, *_ = sections["interim"]
        self.assertEqual(src["published"], "2025-11-01")
        self.assertEqual(quarter["measure"], "after-tax-operating-earnings")
        self.assertEqual(quarter["rows"][0]["values"], [2, -1])
        self.assertEqual(quarter["total"], [10, 9])
        self.assertEqual(net["rows"][0]["values"], [12, 14])
        self.assertEqual(ytd["total"], [16, 20])
        self.assertEqual(quarter["periods"][1]["start"], "2025-07-01")
        self.assertEqual(ytd["periods"][1]["start"], "2025-01-01")

    def test_mismatched_segment_or_reporting_period_is_rejected(self):
        for replacement in (self.back.replace("20 16", "25 16"), self.back.replace("2025 2024", "2023 2022")):
            with self.assertRaises(ValueError):
                statements([self.front, replacement], self.release)

    def test_only_dated_actual_releases_in_company_archive(self):
        fixture = b"""<dl><dt><a href="nov0125.pdf">November 1, 2025</a></dt><dd>Third Quarter Earnings 2025</dd>
        <dt><a href="oct2925.pdf">October 29, 2025</a></dt><dd>Information Regarding Third Quarter Earnings Release</dd>
        <dt><a href="https://example.com/news/fake.pdf">November 2, 2025</a></dt><dd>Third Quarter Earnings 2025</dd></dl>"""
        self.assertEqual(
            list(releases(fixture, "https://www.berkshirehathaway.com/news/2025news.html")), [self.release]
        )
