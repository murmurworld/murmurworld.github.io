import unittest
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import issuer_mining as mining
from public_company_sec import sec_cik


def note(annual=False):
    years = [2025, 2024, 2023] if annual else [2026, 2025]
    n = len(years)
    years_line = " ".join(map(str, years))
    heading = "" if annual else "Six months ended 30 June "
    values = [120, 100, 80][:n]
    def dest(label, pct, amounts):
        return " ".join([label, *([str(pct)] * n), *map(str, amounts)])
    def product(label, amounts):
        return label + " " + " ".join(f"{v + 2} (2) {v}" for v in amounts)
    return [
        "Consolidated sales revenue by destination(a)", years_line + " " + years_line,
        heading + " ".join(["%"]*n + ["US$m"]*n),
        dest("Greater China", 50, [v // 2 for v in values]), dest("US", 50, [v // 2 for v in values]),
        dest("Consolidated sales revenue", 100, values),
        "Consolidated sales revenue by product", "Revenue from contracts with customers Other Consolidated sales revenue",
        years_line if annual else " ".join(str(y) for y in years for _ in range(3)),
        heading + " ".join(["US$m"]*3*n),
        product("Iron ore", [v//2 for v in values]), product("Copper", [v//4 for v in values]),
        "Industrial minerals (comprising titanium", product("dioxide slag, borates and salt)", [v//4 for v in values]),
        product("Consolidated sales revenue", values),
    ]


def directory(label, url):
    return f"""<html><head><title>Invest | Global</title></head><body><div class="document-basket-doc">
        <div class="document-basket-doc-title">{label}</div><a href="{url}"></a></div></body></html>"""


HALF = "https://cdn-rio.dataweavers.io/-/media/content/documents/invest/financial-news-and-performance/results/2026/2026-half-year-results.pdf"
YEAR = "https://cdn-rio.dataweavers.io/-/media/content/documents/invest/reports/annual-reports/2025-annual-report.pdf"
EARLY = "https://cdn-rio.dataweavers.io/-/media/content/documents/invest/financial-news-and-performance/results/2025/2025-annual-results.pdf"


class RioTintoResults(unittest.TestCase):
    def test_rio_adr_uses_the_same_joint_report_as_the_australian_registrant(self):
        path = Path(__file__).resolve().parents[2] / "public/data/company-reports/rio-tinto.json"
        original = json.loads(path.read_bytes())
        adr_cik = sec_cik(original)
        self.assertEqual(int(adr_cik), 863064)
        # Leave the checked-in data free to advance beyond this small mock statement.
        identity = {**original, "annual": [], "interim": []}
        with patch.object(mining, "rio_directory", return_value={("interim", 2026):HALF}), patch.object(
                mining, "rio_document", return_value=(note(), 44, "2026-07-29", "2026-06-30")):
            for cik in (adr_cik, 887028):
                out, status = mining.refresh_mining(identity,cik,lambda _:b"pdf")
                self.assertEqual(out["ticker"],"RIO")
                self.assertEqual(status["latest"][0]["periodEnd"],"2026-06-30")
            with self.assertRaises(ValueError):
                mining.refresh_mining(identity, 811809, lambda _:b"pdf")

    def test_directory_matches_document_year_type_and_official_host(self):
        self.assertEqual(mining.rio_directory(directory("Half Year Results 2026", HALF)), {("interim", 2026): HALF})
        self.assertEqual(mining.rio_directory(directory("Third Quarter Operations Review 2026", HALF)), {})
        for url in (HALF.replace("cdn-rio.dataweavers.io", "example.com"), HALF.replace("/2026/", "/2025/"), HALF + "?else=0"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                mining.rio_directory(directory("Half Year Results 2026", url))

    def test_currency_years_contract_adjustments_and_original_percentages(self):
        product, country = mining.rio_tables(note(), 2026, "interim", {})
        self.assertEqual(product["total"], [100, 120])
        self.assertEqual(product["rows"][0]["values"], [50, 60])
        self.assertEqual(product["rows"][-1]["ko"], "산업광물")
        self.assertEqual(product["periods"][1]["start"], "2026-01-01")
        self.assertEqual(product["periods"][1]["end"], "2026-06-30")
        self.assertEqual(country["total"], product["total"])
        self.assertEqual(len(product["compositionPeriods"]), 2)
        for change, replacement in (("62 (2) 60", "61 (2) 60"), ("Greater China 50 50", "Greater China 55 50"),
                                    ("US$m", "A$m"), ("2026 2026 2026 2025 2025 2025", "2025 2025 2025 2026 2026 2026"),
                                    ("Copper ", "Copper equivalent tonnes ")):
            bad = [x.replace(change, replacement) for x in note()]
            with self.subTest(change=change), self.assertRaises(ValueError):
                mining.rio_tables(bad, 2026, "interim", {})

    def test_annual_dash_is_missing_and_both_notes_must_reconcile(self):
        data = note(True)
        data.insert(-1, "Lithium — — — — — — — — —")
        products, _ = mining.rio_tables(data, 2025, "annual", {})
        self.assertEqual(products["rows"][-1]["values"], [None, None, None])
        self.assertEqual(products["compositionPeriods"], [])
        self.assertEqual(products["periods"][0]["end"], "2023-12-31")
        with self.assertRaisesRegex(ValueError, "totals disagree"):
            mining.rio_tables([s.replace("100 100 100 120 100 80", "100 100 100 115 100 80") for s in data], 2025, "annual", {})
        with self.assertRaisesRegex(ValueError, "add to consolidated"):
            mining.rio_tables([s for s in data if not s.startswith("Copper ")], 2025, "annual", {})

    def test_early_annual_does_not_add_cash_flow_to_revenue(self):
        data = ["Year ended 31 December 2025 2024 Change",
                "Net cash generated from operating activities (US$ millions) 640 600 7 %",
                "Consolidated sales revenue (US$ millions) 4,500 4,000 13 %"]
        t = mining.rio_early_annual(data, 2025, {})[0]
        self.assertIsNone(t["total"])
        self.assertEqual(t["rows"][0]["values"], [4000, 4500])
        with self.assertRaises(ValueError):
            mining.rio_early_annual(data, 2024, {})

    def test_partial_error_leaves_annual_and_verified_old_series_intact(self):
        old = dict(id="segments", periods=[dict(end="2024-12-31")], source={"periodEnd":"2024-12-31"})
        report = dict(ticker="RIO", annual=[old], interim=[old], easy={"keep":1})
        saved = deepcopy(report)
        def read(raw, year, kind):
            if kind == "annual": raise ValueError("Incorrect document identity")
            return note(), 44, "2026-07-29", "2026-06-30"
        with patch.object(mining, "rio_directory", return_value={("annual", 2025):YEAR,("interim", 2026):HALF}), patch.object(mining,"rio_document",side_effect=read):
            updated, status = mining.refresh_mining(report,887028,lambda url:b"original")
        self.assertEqual(report, saved)
        self.assertEqual(updated["annual"], saved["annual"])
        self.assertEqual(updated["interim"][-1],old)
        self.assertEqual([x["kind"] for x in status["latest"]],["interim"])
        self.assertEqual(status["latest"][0]["published"],"2026-07-29")
        self.assertEqual(status["latest"][0]["url"],HALF+"#page=44")
        self.assertTrue(status["warnings"][0].startswith("annual-unavailable"))
        with self.assertRaises(ValueError):
            mining.refresh_mining(report,811809,lambda _:None)

    def test_current_early_release_takes_priority_over_old_annual_notes(self):
        docs={("annual",2024):YEAR.replace("2025","2024"),("annual-results",2025):EARLY}
        report=dict(ticker="RIO", annual=[], interim=[], easy={})
        early=["Year ended 31 December 2025 2024 Change","Net cash generated from operating activities (US$ millions) 25 20 25 %",
               "Consolidated sales revenue (US$ millions) 201 200 1 %"]
        with patch.object(mining,"rio_directory",return_value=docs),patch.object(mining,"rio_document",return_value=(early,1,"2026-02-19","2025-12-31")) as read:
            updated,status=mining.refresh_mining(report,887028,lambda _:b"pdf")
        read.assert_called_once_with(b"pdf",2025,"annual-results")
        self.assertEqual(updated["annual"][0]["id"],"rio-results-annual")
        self.assertIn("annual-product-notes-unavailable",status["warnings"])


if __name__ == "__main__":
    unittest.main()
