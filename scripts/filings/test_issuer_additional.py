import unittest
from copy import deepcopy
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import issuer_additional as source


def numbers(label, cells=("D", "E", "F", "G", "H", "J", "K", "L", "M", "N"), base=1):
    return {"B": label, **{column: Decimal(base * (i + 1)) for i, column in enumerate(cells)}}


def cop_sample(q=3):
    years = {"D": Decimal(2025), "J": Decimal(2026)}
    names = (
        source.QUARTER_COLUMNS + ["Full Year"] + source.QUARTER_COLUMNS + ["Full Year" if q == 4 else "YTD"]
    )
    columns = dict(zip("DEFGHJKLMN", names))
    rows = [
        {"D": f"{source.ORDINAL[q-1]}-Quarter 2026 Detailed Supplemental Information"},
        years,
        columns,
        {"B": "$ Millions, Except as Indicated"},
        {"B": "CONSOLIDATED INCOME STATEMENT"},
    ]
    rows += [numbers(t, base=i + 1) for i, t in enumerate(source.COP_INCOME)]
    rows += [
        numbers("Total revenues and other income", base=10),
        numbers("Total costs and expenses", base=2),
        numbers("Income (loss) before income taxes", base=8),
        numbers("Income tax provision (benefit)", base=2),
        numbers("Net income (loss)", base=6),
        years,
        columns,
        {"B": "$ Millions"},
        {"B": "EARNINGS BY SEGMENT"},
    ]
    rows += [numbers(t) for t in source.COP_SEGMENTS]
    return rows + [numbers("Consolidated", base=6)]


def jp_sample(q=3):
    year = 2025
    sheet = [
        {"B": "JPMORGAN CHASE & CO."},
        {"B": "CONSOLIDATED STATEMENTS OF INCOME"},
        {"B": "(in millions, except per share and ratio data)"},
        {"F": "QUARTERLY TRENDS", "T": "FULL YEAR" if q == 4 else "NINE MONTHS ENDED SEPTEMBER 30,"},
        {},
        {"B": "REVENUE", "F": f"{q}Q25", "N": f"{q}Q24", "T": Decimal(year), "V": Decimal(year - 1)},
    ]
    for label in source.JPM_NONINTEREST:
        sheet.append(numbers(label, "FNTV"))
    for label, base in (
        ("Noninterest revenue", 9),
        ("Interest income", 15),
        ("Interest expense", 5),
        ("Net interest income", 10),
        ("TOTAL NET REVENUE", 19),
        ("Provision for credit losses", 2),
        ("TOTAL NONINTEREST EXPENSE", 3),
        ("Income before income tax expense", 14),
        ("Income tax expense", 4),
        ("NET INCOME", 10),
    ):
        sheet.append(numbers(label, "FNTV", base))
    return sheet


class OfficialAdditionalTests(unittest.TestCase):
    def test_conoco_dateline_and_matching_news_release_header(self):
        self.assertEqual(
            source.cop_publication_date("NEWS RELEASE headline HOUSTON— April 30, 2026 —conocophillips"),
            date(2026, 4, 30),
        )
        self.assertEqual(
            source.cop_publication_date("NEWS RELEASE Nov. 5, 2026 ... HOUSTON— Nov. 5, 2026"),
            date(2026, 11, 5),
        )
        with self.assertRaises(ValueError):
            source.cop_publication_date("NEWS RELEASE Nov. 5, 2026 ... HOUSTON— Nov. 6, 2026")

    def test_conoco_separates_standalone_and_cumulative_and_full_year(self):
        quarter = source.cop_financials(cop_sample(), 2026, 3, {})
        self.assertEqual(quarter[0]["periods"][-1]["start"], "2026-07-01")
        self.assertEqual(quarter[2]["periods"][-1]["start"], "2026-01-01")
        self.assertEqual(quarter[0]["total"], [18, 48])
        self.assertEqual(quarter[2]["total"], [60])
        self.assertEqual(quarter[0]["measure"], "net-income")
        self.assertEqual(quarter[0]["compositionKeys"], [])
        annual = source.cop_financials(cop_sample(4), 2026, 4, {})
        self.assertEqual(annual[0]["total"], [30, 60])

    def test_conoco_cannot_substitute_adjusted_results_unsigned_issuer_or_wrong_totals(self):
        for label, replacement in (
            ("EARNINGS BY SEGMENT", "ADJUSTED EARNINGS"),
            ("$ Millions", "Units of production"),
        ):
            sheet = cop_sample()
            next(r for r in sheet if r.get("B") == label)["B"] = replacement
            with self.assertRaises(ValueError):
                source.cop_financials(sheet, 2026, 3, {})
        sheet = cop_sample()
        sheet[-1]["L"] += 1
        with self.assertRaises(ValueError):
            source.cop_financials(sheet, 2026, 3, {})
        with self.assertRaises(ValueError):
            source.refresh_additional({"ticker": "COP"}, 19617, lambda _: None)

    def test_jpm_correct_dollar_columns_only(self):
        tables = source.jpm_financials(jp_sample(), 2025, 3, {})
        self.assertEqual(tables[0]["total"], [38, 19])
        self.assertEqual(tables[1]["total"], [76, 57])
        self.assertEqual(len(tables[0]["rows"]), 10)
        self.assertEqual(tables[1]["periods"][0]["start"], "2024-01-01")
        annual = source.jpm_financials(jp_sample(4), 2025, 4, {})
        self.assertEqual(annual[0]["periods"][1]["end"], "2025-12-31")

    def test_jpm_does_not_publish_managed_basis_or_swapped_quarters(self):
        for row, key, value in (
            (1, "B", "RECONCILIATION FROM REPORTED TO MANAGED BASIS"),
            (5, "N", "2Q25"),
            (3, "T", "FULL YEAR"),
        ):
            sheet = jp_sample()
            sheet[row][key] = value
            with self.assertRaises(ValueError):
                source.jpm_financials(sheet, 2025, 3, {})
        sheet = jp_sample()
        next(r for r in sheet if r.get("B") == "Card income")["F"] += 3
        with self.assertRaises(ValueError):
            source.jpm_financials(sheet, 2025, 3, {})

    def test_home_depot_retail_calendar_including_extra_week(self):
        previous, current = source.hd_periods(2025, 4, "annual")
        self.assertEqual((previous["start"], previous["end"]), ("2024-01-29", "2025-02-02"))
        self.assertEqual((current["start"], current["end"]), ("2025-02-03", "2026-02-01"))
        self.assertEqual(source.hd_periods(2026, 3, "quarter")[1]["start"], "2026-08-03")

    def test_official_product_rows_require_the_independent_release_total(self):
        rows = [
            "Fiscal Q3 2026 Form 10-Q",
            "The following table presents net sales by major product line and Other net sales.",
            "Three Months Ended Nine Months Ended",
            "in millions November 1,2026 November 2,2025 November 1,2026 November 2,2025",
            "Building Materials $ 14,113 $ 13,649 $ 41,516 $ 40,846",
            "Décor 13,125 12,886 39,659 39,136",
            "Hardlines 11,292 10,927 37,924 36,924",
            "Primary segment net sales 38,530 37,462 119,099 116,906",
            "Other net sales (1) 4,868 3,890 13,925 9,579",
            "Net sales $ 43,398 $ 41,352 $ 133,024 $ 126,485",
            "SIGNATURES",
            "THE HOME DEPOT, INC.",
            "Date: November 20, 2026",
        ]

        class CheckDate(date):
            @classmethod
            def today(cls):
                return cls(2027, 1, 1)

        with patch.object(source, "date", CheckDate):
            s, table = source.hd_product_note(
                rows, 2026, 3, "https://example.org/note", {"Net sales": [43398, 41352, 133024, 126485]}
            )
            self.assertEqual(s["signed"], "2026-11-20")
            self.assertNotIn("filed", s)
            self.assertEqual(table["Net sales"][0], 43398)
            with self.assertRaises(ValueError):
                source.hd_product_note(
                    rows, 2026, 3, "https://example.org/note", {"Net sales": [43399, 41352, 133024, 126485]}
                )

    def test_partial_release_preserves_older_products_and_all_originals(self):
        old_product = {
            "id": "hd-ir-product-quarter",
            "periods": [{"end": "2025-11-02"}],
            "source": {"url": "prior"},
        }
        item = {"ticker": "HD", "annual": [], "interim": [old_product]}
        original = deepcopy(item)
        release = {"periodEnd": "2026-11-01", "published": "2026-11-17", "url": "current"}
        fresh = {"id": "hd-ir-income-quarter", "source": release, "periods": [{"end": "2026-11-01"}]}
        with patch.object(
            source, "hd_directory", return_value={(2026, 3): ("release", None)}
        ), patch.object(source, "hd_statement", return_value=(release, [fresh])):
            updated, status = source.refresh_additional(item, 354950, lambda _: None)
        self.assertEqual(updated["interim"], [fresh, old_product])
        self.assertEqual(item, original)
        self.assertEqual([r["kind"] for r in status["latest"]], ["interim"])

    def test_copy_has_no_external_or_computed_formula_fetch(self):
        with self.assertRaises(ValueError):
            source.sheet_cells(b"not a spreadsheet", "Page 4", 60)


if __name__ == "__main__":
    unittest.main()
