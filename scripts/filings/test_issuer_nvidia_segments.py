import unittest

from issuer_nvidia_segments import (
    CDN_ROOT, VERIFIED, _geography, _markets, _segments, nvidia_disclosure_links,
)


PERIODS = [{"label": "FY26 Q3", "end": "2025-10-26"}, {"label": "FY27 Q3", "end": "2026-10-25"}]
SOURCE = {"periodEnd": "2026-10-25", "published": "2026-11-17"}
SCOPES = {"quarter": (PERIODS, [57006, 115844]), "ytd": (PERIODS, [147811, 293681])}
GEO = """NVIDIA Corporation
Supplemental Financial Information
For the Quarter Ended October 25, 2026
Three Months Ended Nine Months Ended
Oct 25, 2026 Oct 26, 2025 Oct 25, 2026 Oct 26, 2025
(In millions)
Geographic Revenue based upon Customer
Headquarters Location:
United States $ 72,899 $ 39,177 $ 196,742 $ 97,759
Taiwan 30,295 13,751 69,286 30,301
China (including Hong Kong) 11,050 2,973 23,480 16,617
Other 1,600 1,105 4,173 3,134
Total revenue $ 115,844 $ 57,006 $ 293,681 $ 147,811"""
MARKET = """NVIDIA QUARTERLY REVENUE
REVENUE BY MARKET PLATFORM
Fiscal 2026 Fiscal 2027
($ in millions) Q1 Q2 Q3 Q4 Q1 Q2 Q3
Data Center $39,112 $41,096 $51,215 $62,314 $75,246 $89,023 $107,610
Hyperscale 22,260 24,168 35,140 42,213 43,050 48,710 60,136
AI Clouds,
Industrial, & 16,852 16,928 16,075 20,101 32,196 40,313 47,474
Enterprise
Edge Computing 4,950 5,647 5,791 5,813 6,369 7,198 8,234
TOTAL $44,062 $46,743 $57,006 $68,127 $81,615 $96,221 $115,844"""
SEGMENT = """CFO Commentary on Third Quarter Fiscal 2027 Results
Revenue by Reportable Segments
($ in billions) Q3 FY27 Q2 FY27 Q3 FY26 Q/Q* Y/Y*
Compute & Networking $106.0 $88.3 $50.9 20 % 108 %
Graphics 9.8 7.9 6.1 25 % 62 %
Total $115.8 $96.2 $57.0 20 % 103 %"""


class NvidiaDimensions(unittest.TestCase):
    def test_geography_reads_reported_quarter_and_ytd(self):
        groups = _geography(GEO.splitlines(), SOURCE, SCOPES, 2027, 3)
        self.assertEqual(groups["quarter"][0]["total"], [57006, 115844])
        self.assertEqual(groups["ytd"][0]["rows"][0]["values"], [97759, 196742])
        self.assertIn("headquarters", groups["quarter"][0]["titleEn"])

    def test_rejects_modified_geography_dates_amounts_and_billing_address(self):
        for before, after in (("72,899", "72,900"), ("Oct 26, 2025", "Oct 25, 2025"),
                              ("Headquarters Location:", "Billing Location:")):
            with self.subTest(before=before), self.assertRaises(ValueError):
                _geography(GEO.replace(before, after).splitlines(), SOURCE, SCOPES, 2027, 3)

    def test_published_market_quarter_survives_one_million_ytd_difference(self):
        groups = _markets(MARKET.splitlines(), SOURCE, SCOPES, 2027, 3)
        self.assertEqual(set(groups), {"quarter"})
        table = groups["quarter"][0]
        self.assertEqual(table["total"], [57006, 115844])
        self.assertEqual(table["compositionKeys"], ["datacenter", "edge"])
        rows = {r["key"]: r for r in table["rows"]}
        self.assertEqual(rows["hyperscale"]["parent"], "datacenter")
        self.assertEqual(rows["acie"]["values"], [16075, 47474])

    def test_rejects_corrupt_market_component_even_when_grand_total_matches(self):
        broken = MARKET.replace("47,474", "47,475").splitlines()
        with self.assertRaises(ValueError):
            _markets(broken, SOURCE, SCOPES, 2027, 3)

    def test_cfo_published_units_and_periods(self):
        groups = _segments(SEGMENT.splitlines(), SOURCE, SCOPES, 2027, 3)
        self.assertEqual(set(groups), {"quarter"})
        table = groups["quarter"][0]
        self.assertEqual(table["unitEn"], "USD billion")
        self.assertEqual(table["total"], [57.0, 115.8])
        self.assertEqual(table["rows"][0]["values"], [50.9, 106.0])
        with self.assertRaises(ValueError):
            _segments(SEGMENT.replace("FY27 Q2 FY27", "FY27 Q1 FY27").splitlines(), SOURCE, SCOPES, 2027, 3)

    def test_discovery_stays_with_verified_issuer_tenant_and_quarter(self):
        url = CDN_ROOT + "2028/Q328/Q3FY28-CFO-Commentary.pdf"
        wrong = url.replace("141608511", "1234")
        old = VERIFIED[2027, 3]["segments"]
        listing = f'<a href="{wrong}">CFO</a><a href="{old}">CFO</a><a href="{url}">CFO</a>'
        self.assertEqual(nvidia_disclosure_links(listing, 2028, 3), {"segments": url})
        self.assertEqual(nvidia_disclosure_links("<html/>", 2028, 3), {})


if __name__ == "__main__":
    unittest.main()
