from datetime import date
from io import BytesIO
import unittest

from openpyxl import Workbook
from issuer_novo import discover, million, read_workbook

DIRECTORY = b"""<p>On 4 November 2026, we announced our financial results for the first nine months of 2026.</p>
<p>Downloads</p><a href="/content/dam/nncorp/investors/Q3-2026-financial-workbook.xlsx">Financial workbook (xlsx)</a>
<p>Q4 &amp; full-year 4 February 2026</p><a href="/content/dam/nncorp/Q4-2025-Financial-Workbook.xlsx">Full-year financial workbook (xlsx)</a>
<a href="https://example.org/Q4-2025-workbook.xlsx">Financial workbook (xlsx)</a>"""


def workbook(bad_total=False):
    book = Workbook()
    income = book.active
    income.title = "IS & OCI"
    income.append([])
    income.append([])
    income.append(["DKK million", "Q3 2026", None, "Q3 2025", None, "9M 2026", None, "9M 2025"])
    for name, values in [
        ("Net sales", [80, 65, 250, 200]),
        ("Gross profit", [55, 50, 130, 100]),
        ("Operating profit", [30, 28, 95, 85]),
        ("NET PROFIT", [22, 20, 81, 75]),
        ("Segment sales:", None),
        ("Obesity and Diabetes", [70, 55, 235, 185]),
        ("Blood & endocrine disorders1", [10, 10, 15, 15]),
        ("Segment operating profit:", None),
    ]:
        if values is None:
            income.append([name])
            continue
        income.append(
            [
                name,
                values[0] * 1_000_000,
                None,
                values[1] * 1_000_000,
                None,
                values[2] * 1_000_000,
                None,
                values[3] * 1_000_000,
            ]
        )
        for col in "BDFH":
            income[f"{col}{income.max_row}"].number_format = "#,##0,,"
    for suffix, period, total in (("Q", "Q3", 80), ("YTD", "9M", 250)):
        sheet = book.create_sheet("Sales IFRS reconciliation - " + suffix)
        sheet.append([])
        sheet.append([])
        sheet.append(
            [
                "Sales split per therapy",
                None,
                period + " 2026 reported sales",
                "340B provision reversal",
                period + " 2026 adjusted sales",
            ]
        )
        for i, name in enumerate(
            ["Wegovy® injectable", "Wegovy® pill", "Saxenda®", "Ozempic®", "Total insulin", "Total sales"], 1
        ):
            reported = total + int(bad_total) if name == "Total sales" else i * 2
            sheet.append([name, None, reported, 1, reported - 1])
            sheet[f"C{sheet.max_row}"].number_format = "#,##0"
    blob = BytesIO()
    book.save(blob)
    return blob.getvalue()


class NovoResultsTests(unittest.TestCase):
    def test_issuer_workbook_and_date(self):
        listing = discover(DIRECTORY)
        self.assertEqual(set(listing), {(2026, 3), (2025, 4)})
        self.assertEqual(listing[2026, 3][0], date(2026, 11, 4))

    def test_display_units_reported_sales_and_interim_duration(self):
        source, tables = read_workbook(workbook(), 2026, 3, date(2026, 11, 4), "issuer.xlsx", "interim")
        self.assertIn("published", source)
        self.assertNotIn("filed", source)
        by_id = {t["id"]: t for t in tables}
        self.assertEqual(by_id["novo-segments-quarter"]["total"], [65, 80])
        self.assertEqual(by_id["novo-segments-ytd"]["total"], [200, 250])
        self.assertEqual(by_id["novo-segments-ytd"]["periods"][-1]["start"], "2026-01-01")
        self.assertEqual(by_id["novo-products-ytd"]["rows"][0]["values"], [2])
        self.assertEqual(by_id["novo-income-quarter"]["unitEn"], "DKK million")
        with self.assertRaisesRegex(ValueError, "reconcile"):
            read_workbook(workbook(True), 2026, 3, date(2026, 11, 4), "issuer.xlsx", "interim")

    def test_unknown_numeric_convention(self):
        cell = Workbook().active["A1"]
        cell.value = 9
        cell.number_format = "0.00%"
        with self.assertRaises(ValueError):
            million(cell)
