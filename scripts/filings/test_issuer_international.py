"""Period and accounting checks for TSMC's Taiwan reporting format."""

from datetime import date
import json
import unittest
from unittest.mock import patch

from issuer_international import TSMC_ARCHIVE, refresh_international, toyota_listing, toyota_statement, tsm_listing, tsm_statement, twse_tsm_income


def listing():
    return b"""<div><h2>Consolidated Financial Statements</h2><a href="javascript:void(0)">2024</a>
      <div class="consolidated-list-wrapper red"><a href="/sites/ir/financial-report/2024/annual.pdf">2024</a></div>
      <div class="consolidated-list-wrapper"><a href="/sites/ir/financial-report/2025/interim.pdf">2025 Nine Months</a></div></div>
      <div><h2>Unconsolidated Financial Statements</h2><div class="consolidated-list-wrapper">
      <a href="/sites/ir/financial-report/2025/solo.pdf">2025</a></div></div>"""


def statement(annual):
    scopes = "Years Ended December 31" if annual else "Three Months Ended September 30 Nine Months Ended September 30"
    years = "2024 2023" if annual else "2025 2024 2025 2024"
    weight = [3, 2] if annual else [3, 2, 9, 6]
    def values(base, percentages=False):
        return " ".join("$ " + f"{base*x:,}" + (" 100" if percentages else "") for x in weight)
    base = [
        "Taiwan Semiconductor Manufacturing Company Limited and Subsidiaries",
        "(Amounts in Thousands of New Taiwan Dollars, Unless Specified Otherwise)",
        "Financial statements were approved and authorized for issuance by the Board of Directors on " +
        ("February 1, 2025." if annual else "November 1, 2025."),
        "NET REVENUE (Notes 12 and 20) " + values(21_000, True),
        "Disaggregation of revenue from contracts with customers", scopes, "Product " + years,
        "Wafer " + values(3000), "Others " + values(18000), values(21000), scopes, "Platform " + years,
    ]
    for index, name in enumerate(["High Performance Computing","Smartphone","Internet of Things","Automotive",
                                  "Digital Consumer Electronics","Others"], 1):
        base.append(name + " " + values(index*1000))
    return base + [values(21_000), scopes, "Resolution " + years, "2-nanometer " + values(2000),
                   "0.25 micron and above " + values(1000), "Wafer revenue " + values(3000)]


class TaiwanIssuerTests(unittest.TestCase):
    def test_discovery_and_security(self):
        by_period = tsm_listing(listing())
        self.assertEqual(sorted(by_period), [(2024,4),(2025,3)])
        with self.assertRaises(ValueError):
            tsm_listing(listing().replace(b"/sites/ir/financial-report/2024/annual.pdf",
                                          b"https://example.org/sites/ir/financial-report/2024/annual.pdf"))

    def test_scope_order_and_date_semantics(self):
        source, tables = tsm_statement(statement(False), 2025, 3, "official.pdf")
        self.assertEqual(source["authorized"], "2025-11-01")
        self.assertNotIn("published", source)
        self.assertNotIn("filed", source)
        self.assertEqual([t["total"] for t in tables], [[126,189],[18,27],[126,189],[42,63],[6,9],[42,63]])
        self.assertEqual([p["start"] for p in tables[0]["periods"]], ["2024-01-01","2025-01-01"])
        self.assertEqual([p["start"] for p in tables[3]["periods"]], ["2024-07-01","2025-07-01"])
        self.assertEqual(tables[0]["currency"], "TWD")
        _, annual = tsm_statement(statement(True), 2024, 4, "official.pdf")
        self.assertEqual(annual[0]["total"], [42,63])
        self.assertEqual(annual[0]["periods"][1]["end"], "2024-12-31")

    def test_new_node_and_displayed_zero(self):
        lines = statement(False)
        idx = next(i for i,x in enumerate(lines) if x.startswith("2-nanometer"))
        lines[idx] = "2-nanometer $ 6,000 $ - $ 18,000 $ -"
        lines[idx+2] = "Wafer revenue $ 9,000 $ 2,000 $ 27,000 $ 6,000"
        product = next(i for i,x in enumerate(lines) if x.startswith("Wafer $"))
        lines[product] = "Wafer $ 9,000 $ 2,000 $ 27,000 $ 6,000"
        lines[product+1] = "Others $ 54,000 $ 40,000 $ 162,000 $ 120,000"
        _, result = tsm_statement(lines, 2025, 3, "official.pdf")
        self.assertEqual(result[1]["rows"][0]["values"], [0,18])

    def test_bad_period_unit_or_unreconciled_amount_fails(self):
        lines = statement(False)
        for old,new in [("Nine Months Ended", "Six Months Ended"), ("New Taiwan Dollars","U.S. Dollars"),
                        ("NET REVENUE (Notes 12 and 20) $ 63,000", "NET REVENUE (Notes 12 and 20) $ 62,000"),
                        ("Automotive $ 12,000", "Automotive $ 12,001")]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                tsm_statement([line.replace(old,new) for line in lines], 2025, 3, "official.pdf")

    def test_refresh_is_idempotent_retains_other_basis_and_partial_failure(self):
        annual_20f = {"id":"products","source":{"filed":"2025-04-15","periodEnd":"2024-12-31"},
                      "periods":[{"end":"2024-12-31"}]}
        baseline = {"ticker":"TSM","annual":[annual_20f],"interim":[]}
        by_period = tsm_listing(listing())
        blobs = {TSMC_ARCHIVE:listing(), by_period[2024,4]:b"annual", by_period[2025,3]:b"interim"}
        with patch("issuer_international.lines_from_pdf", side_effect=lambda body:statement(body==b"annual")):
            first, meta = refresh_international(baseline,1046179,blobs.__getitem__)
            self.assertEqual([x["kind"] for x in meta["latest"]], ["annual","interim"])
            self.assertEqual(first["annual"][0], annual_20f)
            second, _ = refresh_international(first,1046179,blobs.__getitem__)
            self.assertEqual(first, second)
            newer = dict(first,interim=[{"id":"unrelated","periods":[{"end":"2025-12-31"}],"source":{}}])
            def no_exchange(url):
                if url not in blobs:
                    raise OSError("Exchange unavailable")
                return blobs[url]
            partial, meta = refresh_international(newer,1046179,no_exchange)
            self.assertEqual(partial["interim"], newer["interim"])
            self.assertTrue(any(s.startswith("interim-unavailable") for s in meta["warnings"]))
            with self.assertRaises(ValueError):
                refresh_international(baseline,123,blobs.__getitem__)

    def test_independent_exchange_ytd_units_and_timestamp(self):
        row={"公司代號":"2330","公司名稱":"台積電","出表日期":"1141115","年度":"114","季別":"3","營業收入":"100000.00",
             "營業成本":"40000.00","營業毛利（毛損）":"60000.00","營業利益（損失）":"50000.00","稅前淨利（淨損）":"52500.00",
             "所得稅費用（利益）":"14000.00","繼續營業單位本期淨利（淨損）":"38500.00","本期淨利（淨損）":"38500.00",
             "淨利（淨損）歸屬於母公司業主":"37500.00"}
        report={"annual":[],"interim":[]}
        out, meta=twse_tsm_income(report,json.dumps([row]).encode())
        table=out["interim"][0]
        self.assertEqual(meta["datasetAsOf"],"2025-11-15")
        self.assertNotIn("published",meta)
        self.assertNotIn("filed",meta)
        self.assertEqual(table["periods"][0]["start"],"2025-01-01")
        self.assertEqual(meta["periodEnd"],"2025-09-30")
        self.assertEqual([r["values"][0] for r in table["rows"]], [100,60,50,52.5,38.5,37.5])
        self.assertEqual(twse_tsm_income(out,json.dumps([row]).encode())[0],out)
        for key,val in [("公司代號","1234"),("公司名稱","Other"),("營業成本","39999.00"),("出表日期","1140801")]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                twse_tsm_income(report,json.dumps([{**row,key:val}]).encode())


class ToyotaIssuerTests(unittest.TestCase):
    def test_archive_and_fiscal_year(self):
        archive=b"""<div><h3>FY2027 2Q Financial Results (November 5, 2026)</h3>
        <ul><li><a href="/pages/global_toyota/ir/financial-results/2027_2q_summary_en.pdf">Financial Summary</a></li></ul></div>"""
        idx,_=toyota_listing(archive)
        self.assertEqual(idx[2027,2][1],date(2026,11,5))
        with self.assertRaises(ValueError):
            toyota_listing(archive.replace(b"2027_2q_summary",b"2027_1q_summary"))

    def test_automotive_external_income_and_region_are_distinct(self):
        end_year=2025
        pub=date(2025,11,5)
        lines=["TOYOTA MOTOR CORPORATION","FY2026 Semi-Annual Consolidated Financial Results","IFRS",
               "April 1, 2025 through September 30, 2025", "November 5, 2025","Company name : Toyota Motor Corporation",
               "Code number : 7203","Total sales revenues 100 150","Operating income 5 10"]
        for i,y in enumerate((end_year-1,end_year)):
            lines.extend([f"For the first half ended September 30, {y}:","Yen in millions","Inter-segment","Elimination/",
                          "Financial Unallocated","Automotive services All other Amount Consolidated","Sales revenues",
                          ["Revenues from external customers 80 15 5 － 100","Revenues from external customers 120 25 5 － 150"][i],
                          ["Operating income 4 2 1 (2) 5","Operating income 7 4 1 (2) 10"][i]])
        lines.extend(["(iv) Sales revenues by location of external customers","Yen in millions",
                      "For the first half ended September 30,","2024 2025","Japan 20 30","North America 40 60",
                      "Europe 10 15","Asia 20 30","Other 10 15","Total 100 150"])
        src,tables=toyota_statement(lines,2026,2,"https://global.toyota/statement",pub)
        self.assertEqual(src["published"],pub.isoformat())
        self.assertNotIn("filed",src)
        self.assertEqual(tables[0]["periods"][-1]["start"],"2025-04-01")
        self.assertEqual(tables[0]["rows"][0]["values"],[80,120])
        self.assertEqual(tables[1]["rows"][0]["values"],[20,30])
        self.assertEqual(tables[2]["rows"][-1]["values"],[-2,-2])
        for old,new in [("100 150","100 151"),("2024 2025","2025 2024"),("Code number : 7203","Code number : 9999")]:
            with self.subTest(old=old),self.assertRaises(ValueError):
                toyota_statement([s.replace(old,new) for s in lines],2026,2,"statement",pub)


if __name__ == "__main__":
    unittest.main()
