import unittest
from issuer_unitedhealth import BUSINESS, OPERATIONS, INSURANCE, discover, parse_pages

URL = "https://www.unitedhealthgroup.com/content/dam/UHG/PDF/investors/2025/results.pdf"


def line(name, values):
    return name + " ... " + " ".join(str(v) for v in values)


def statements():
    front = "UnitedHealth Group Reports 2025 Results and Issues 2026 Outlook\nJanuary 27, 2026\nUnitedHealth Group (NYSE: UNH)"
    heads = "Three Months Ended Year Ended\nDecember 31, December 31,\n2025 2024 2025 2024"
    columns = [
        (120, 25, 8, 50, 80, 150),
        (100, 20, 10, 40, 65, 125),
        (480, 100, 32, 200, 320, 600),
        (400, 80, 40, 160, 260, 500),
    ]
    total = [r[-1] for r in columns]
    insurance = [r[0] for r in columns]
    ops = "\n".join(
        [
            OPERATIONS,
            "(in millions, except per share data; unaudited)",
            heads,
            line("Premiums", [v - 12 for v in total]),
            line("Products", [8] * 4),
            line("Services", [3] * 4),
            line("Investment and other income", [1] * 4),
            line("Total revenues", total),
            line("Earnings from operations", [10] * 4),
            line("Net earnings", [7] * 4),
            line("Net earnings attributable to UnitedHealth Group common shareholders", [6] * 4),
        ]
    )
    seg = [
        BUSINESS,
        "(in millions; unaudited)",
        "UnitedHealthcare Health Insight Rx Optum (a) Consolidated (a)",
    ]
    for h, r in zip(
        (
            "Three Months Ended December 31, 2025",
            "Three Months Ended December 31, 2024",
            "Year Ended December 31, 2025",
            "Year Ended December 31, 2024",
        ),
        columns,
    ):
        seg.extend([h, line("Total revenues", r), line("Adjusted revenues", [999] * 6)])
    keys = list(INSURANCE)
    seg.extend(
        [
            "UnitedHealthcare Revenues",
            heads,
            line(keys[0], [20] * 4),
            line(keys[1], [50] * 4),
            line(keys[2], [v - 70 for v in insurance]),
            line("Total UnitedHealthcare revenues", insurance),
            "(a) Optum and consolidated revenues for the three months ended December 31, 2025 and 2024 include Optum eliminations of $3 and $5; and corporate eliminations of $50 and $40, respectively.",
            "Optum and consolidated revenues for the year ended December 31, 2025 and 2024 include Optum eliminations of $12 and $20; and corporate eliminations of $200 and $160, respectively.",
            "(c) Prior period amounts have been recast to reflect the realignment of Optum Financial.",
        ]
    )
    return [front, ops, "\n".join(seg)]


class UnitedHealthStatements(unittest.TestCase):
    def test_fiscal_year_quarter_and_gaap_amounts(self):
        source, table = parse_pages(statements(), 2025, 4, URL)
        self.assertEqual(source["published"], "2026-01-27")
        self.assertNotIn("filed", source)
        annual, insurance, income = table["annual"]
        self.assertEqual(annual["total"], [500, 600])
        self.assertEqual(table["interim"][0]["total"], [125, 150])
        self.assertEqual(table["interim"][0]["periods"][1]["start"], "2025-10-01")
        self.assertEqual(annual["periods"][1]["start"], "2025-01-01")
        self.assertEqual(insurance["total"], [400, 480])
        self.assertEqual(income["rows"][0]["values"], annual["total"])
        terms = {r["key"]: r for r in annual["rows"]}
        self.assertEqual(terms["optum-elimination"]["values"], [-20, -12])
        self.assertEqual(terms["group-elimination"]["values"], [-160, -200])
        self.assertEqual(terms["optum-insight"]["parent"], "optum")
        self.assertEqual(annual["compositionKeys"], [])
        self.assertIn("recast", " ".join(annual["notesEn"]))

    def test_rejects_offsetting_or_adjusted_amounts(self):
        cases = [
            (2, "$12 and $20", "$13 and $20"),
            (2, "$200 and $160", "$199 and $160"),
            (1, "Premiums ... 138", "Premiums ... 140"),
            (2, "480 100 32 200", "480 100 32 201"),
            (1, "2025 2024 2025 2024", "2025 2024 2024 2023"),
            (0, "January 27, 2026", "November 27, 2025"),
            (2, "Insight Rx", "Rx Insight"),
            (2, "120 25 8 50", "121 25 8 50"),
        ]
        for n, old, new in cases:
            with self.subTest(old=old):
                raw = statements()
                self.assertIn(old, raw[n])
                raw[n] = raw[n].replace(old, new)
                with self.assertRaises(ValueError):
                    parse_pages(raw, 2025, 4, URL)

    def test_official_discovery_ignores_other_hosts_and_previous_quarter(self):
        def group(year, quarter, url, text="Earnings Release"):
            return f'<li data-drawer><a role="button">{year}</a><div class="col-md-6"><p><b>Q{quarter}</b></p><p><a href="{url}">{text}</a></p></div></li>'

        annual = group(2025, 4, URL)
        raw = (
            annual
            + group(2026, 1, "https://other.example/data.pdf")
            + group(2026, 2, URL, "Prepared remarks")
        )
        self.assertEqual(discover(raw), {(2025, 4): URL})
        with self.assertRaises(ValueError):
            discover(annual + group(2025, 4, URL.replace("results.pdf", "other.pdf")))
