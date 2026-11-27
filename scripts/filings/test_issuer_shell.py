import json
import unittest

from issuer_shell import collect, segment_table, statements


def page(heading, amounts, unit="$ million", names=None):
    columns = names or ["Integrated Gas", "Upstream", "Marketing", "Chemicals and Products",
                        "Renewables and Energy Solutions", "Corporate", "Total"]
    header = "".join(name.ljust(35) for name in columns)
    return f"{heading} {unit}\n{header}\nRevenue:\nThird-party revenue {amounts}\nInter-segment revenue 1 2 3 4 5 6 21"


class ShellDisclosure(unittest.TestCase):
    def test_different_periods_and_signed_corporate_revenue(self):
        old = page("Q3 2025", "9,736 844 29,648 19,418 8,500 6 68,153")
        current = page("Q3 2026", "13,770 1,665 39,366 26,489 11,545 13 92,848")
        previous = page("Q2 2026", "11,278 1,800 38,015 34,235 9,338 (2) 94,664")
        ytd = page("Nine months 2026", "32,795 4,865 108,076 79,945 31,506 16 257,203")
        rows = collect([old, current, previous, ytd])
        t = segment_table("q", "quarter", rows, [(2025,"q3"),(2026,"q3")], {})
        self.assertEqual([68153, 92848],t["total"])
        self.assertEqual([29648,39366],t["rows"][2]["values"])
        self.assertEqual(-2, rows[2026,"q2"][5])
        self.assertEqual("2026-07-01",t["periods"][1]["start"])
        self.assertEqual(257203,rows[2026,"nine months"][-1])

    def test_rejects_wrong_columns_unit_and_unexplained_mismatch(self):
        for sample in (
            page("Q3 2026","10 20 30 40 50 — 190"),
            page("Q3 2026","10 20 30 40 50 — 150",unit="£ million"),
            page("Q3 2026","10 20 30 40 50 — 150", names=["Integrated Gas","Upstream","Marketing","Renewables and Energy Solutions","Chemicals and Products","Corporate","Total"]),
        ):
            with self.assertRaises(ValueError): collect([sample])

    def test_dated_disclosure_and_safe_source(self):
        def index(url):
            return json.dumps({"model":{"title":"Q3 2026 Results","text":"<p><b>29 OCT 2026</b></p>",
                "links":[{"name":"Quarterly unaudited results (PDF, 575 kB)","value":url}]}})
        year,q,day,_ = statements(index("/reports/q3-2026-qra-document.pdf"),False)
        self.assertEqual((2026,3,"2026-10-29"),(year,q,day.isoformat()))
        with self.assertRaises(ValueError): statements(index("https://example.org/q3-2026-qra-document.pdf"),False)


if __name__ == "__main__":
    unittest.main()
