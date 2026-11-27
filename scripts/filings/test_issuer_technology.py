"""Guard the fiscal periods, data provenance and GAAP reconciliations in the three public archives."""

from datetime import date
from gzip import compress
from unittest import TestCase, main
from unittest.mock import patch

from issuer_technology import (
    wire_list,
    palo_alto_statement,
    broadcom_statement,
    lam_list,
    lam_statement,
    refresh_technology,
    sandisk_list,
    sandisk_statement,
)


def table(rows, caption=""):
    return (
        "<table><caption>"
        + caption
        + "</caption>"
        + "".join("<tr>" + "".join("<td>" + c + "</td>" for c in row) + "</tr>" for row in rows)
        + "</table>"
    )


SNDK_URL = "https://www.sandisk.com/company/newsroom/press-releases/2025/2025-08-14-sandisk-reports-fiscal-fourth-quarter-2025-financial-results"
SNDK_ENTRY = (2025, 4, date(2025, 8, 14), SNDK_URL)
SITEMAP = (
    "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>"
    + SNDK_URL
    + "</loc></url></urlset>"
).encode()
HEAD = "<h1>Sandisk Reports Fiscal Fourth Quarter 2025 Financial Results</h1><p>MILPITAS, Calif. - August 14, 2025</p>"
INCOME = [
    ["Three Months Ended", "Year Ended"],
    ["June 27, 2025", "June 28, 2024"] * 2,
    ["Revenue, net", "$50", "$40", "$300", "$200"],
    ["Gross profit", "30", "25", "165", "95"],
    ["Operating income (loss)", "18", "6", "51", "(11)"],
    ["Net income (loss)", "15", "3", "44", "(15)"],
]
MARKET = [
    ["Revenue", "2025", "2024", "Y/Y"],
    ["Datacenter", "150", "90", "67%"],
    ["Edge", "90", "50", "80%"],
    ["Consumer", "60", "60", "0%"],
    ["Total Revenue", "300", "200", "50%"],
]


def sandisk():
    return (
        "<html><body>"
        + HEAD
        + table(
            INCOME,
            "Condensed Consolidated Statements of Operations (in millions, except per share amounts; unaudited)",
        )
        + table(MARKET, "End Market Summary ($ in millions)")
        + "</body></html>"
    ).encode()


LRCX_URL = "https://investor.lamresearch.com/content/dam/investor/image/Form%2010-Q%20filed%2010_24_2024.pdf"


class Page:
    def __init__(self, text):
        self.text = text

    def extract_text(self, **_):
        return self.text


class TechnologyTests(TestCase):
    def test_palo_alto_uses_sales_before_costs_and_marks_preliminary(self):
        rows = [
            ["Palo Alto Networks, Inc."],
            ["Preliminary Condensed Consolidated Statements of Operations"],
            ["(In millions, except per share data)"],
            ["(Unaudited)"],
            ["Three Months Ended"],
            ["October 31,"],
            ["2024", "2023"],
            ["Revenue:"],
            ["Product", "$ 20", "$ 12"],
            ["Subscription and support", "80", "68"],
            ["Total revenue", "100", "80"],
            ["Cost of revenue:"],
            ["Product", "6", "3"],
            ["Subscription and support", "20", "16"],
            ["Total gross profit", "74", "61"],
            ["Operating income", "10", "8"],
            ["Net income", "4", "5"],
        ]
        head = (
            "<h1>Palo Alto Networks Reports Fiscal First Quarter 2025 Financial Results</h1>"
            '<a href="/news/palo-alto-networks%2C-inc./">Palo Alto Networks, Inc.</a>'
            '<meta name="date" content="2024-11-20T16:00:00Z">'
        )
        entry = (2025, 1, date(2024, 11, 20), "https://www.prnewswire.com/sample")
        raw = (head + table(rows)).encode()
        source, data = palo_alto_statement(raw, entry, "interim")
        self.assertIn("preliminary", source["labelEn"])
        self.assertEqual(source["periodEnd"], "2024-10-31")
        self.assertEqual(data[0]["rows"][0]["values"], [12, 20])
        self.assertEqual(data[0]["total"], [80, 100])
        with self.assertRaises(ValueError):
            palo_alto_statement(raw.replace(b"October 31,", b"September 30,"), entry, "interim")

    def test_sandisk_gzip_and_annual_columns(self):
        self.assertEqual(sandisk_list(compress(SITEMAP))["annual"], SNDK_ENTRY)
        source, tables = sandisk_statement(compress(sandisk()), SNDK_ENTRY, "annual")
        self.assertEqual(source["published"], "2025-08-14")
        self.assertNotIn("filed", source)
        self.assertEqual(tables[0]["total"], [200, 300])
        self.assertEqual(tables[1]["rows"][-1]["values"], [-15, 44])
        self.assertEqual(tables[0]["unitEn"], "USD million")

    def test_sandisk_rejects_foreign_origin_revenue_mismatch_and_wrong_date(self):
        self.assertIsNone(sandisk_list(SITEMAP.replace(b"www.sandisk.com", b"example.org"))["annual"])
        for before, after in [
            (b"($ in millions)", b"(in thousands)"),
            (b"<td>150</td>", b"<td>149</td>"),
            (b"August 14, 2025", b"August 12, 2025"),
            (b"June 27, 2025", b"June 27, 2023"),
        ]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                sandisk_statement(sandisk().replace(before, after), SNDK_ENTRY, "annual")

    def test_broadcom_scheduled_call_not_results(self):
        path = "/news-releases/broadcom-inc-announces-third-quarter-fiscal-year-2025-financial-results-and-quarterly-dividend-1234.html"
        html = (
            '<a href="'
            + path
            + '">Sep 02, 2025, 16:15 ET Issued</a><a href="'
            + path.replace("announces-third", "to-announce-fourth")
            + '">Nov 9, 2025, 16:15 ET Future call</a>'
        )
        self.assertEqual(wire_list(html.encode(), "AVGO")["interim"][:3], (2025, 3, date(2025, 9, 2)))
        self.assertIsNone(wire_list(html.encode(), "AVGO")["annual"])

    def test_broadcom_author_scope_units_and_percent_columns(self):
        source = "https://www.prnewswire.com/news-releases/broadcom-inc-announces-third-quarter-fiscal-year-2025-financial-results-123.html"
        entry = 2025, 3, date(2025, 9, 2), source
        head = """<h1>Broadcom Inc. Announces Third Quarter Fiscal Year 2025 Financial Results</h1>
          <a href="/news/broadcom-inc./">Broadcom Inc.</a><meta name="date" content="2025-09-02T21:15:00+01:00">"""
        pnl = [
            ["BROADCOM INC."],
            ["CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS - UNAUDITED"],
            ["(IN MILLIONS, EXCEPT PER SHARE DATA)"],
            ["Fiscal Quarter Ended", "Three Fiscal Quarters Ended"],
            ["August 3,", "May 4,", "August 4,", "August 3,", "August 4,"],
            ["2025", "2025", "2024", "2025", "2024"],
            ["Net revenue", "50", "43", "35", "160", "109"],
            ["Gross margin", "29", "25", "21", "70", "64"],
            ["Operating income", "14", "12", "9", "40", "28"],
            ["Net income", "11", "8", "5", "28", "19"],
        ]
        seg = [
            ["Net revenue by segment"],
            ["(Dollars in millions)", "Q3 25", "Q3 24", "Change"],
            ["Semiconductor solutions", "30", "60", "%", "20", "57", "%", "+50", "%"],
            ["Infrastructure software", "20", "40", "15", "43", "+33", "%"],
            ["Total net revenue", "50", "100", "%", "35", "100", "%"],
        ]
        raw = (head + table(pnl) + table(seg)).encode()
        source, tables = broadcom_statement(raw, entry, "interim")
        self.assertEqual(source["periodEnd"], "2025-08-03")
        self.assertEqual(tables[0]["total"], [35, 50])
        self.assertEqual(tables[1]["rows"][-1]["values"], [5, 11])
        for before, after in [
            (b'">Broadcom Inc.</a>', b'">Different publisher</a>'),
            (b"Q3 24", b"FY 24"),
            (b"<td>30</td>", b"<td>18</td>"),
        ]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                broadcom_statement(raw.replace(before, after), entry, "interim")

    def test_lam_signed_form_and_separate_quarter_periods(self):
        cover = "UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 10-Q For the quarterly period ended September 29, 2024 LAM RESEARCH CORPORATION"
        income = """CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS
(in thousands, except per share data)
Three Months Ended
September 29, September 24,
2024 2023
Revenue $ 89 $ 76
Gross margin 30 28
Operating income 26 21
Net income 21 17"""
        data = """Three Months Ended
September 29, September 24,
2024 2023
(in thousands)
Systems revenue $ 50 $ 40
Customer support-related revenue and other 39 36
$ 89 $ 76"""
        signed = """SIGNATURES
Pursuant to the requirements of the Securities Exchange Act of 1934, the Registrant has duly caused this Report to be signed.
Date: October 24, 2024"""

        def parse(last_date):
            with patch("issuer_technology.PdfReader") as doc:
                doc.return_value.pages = [
                    Page(cover),
                    Page(income),
                    Page(data),
                    Page(signed.replace("October 24", last_date)),
                ]
                return lam_statement(b"", ((2024, 9), LRCX_URL), "interim")

        source, tables = parse("October 24")
        self.assertEqual(source["filed"], "2024-10-24")
        self.assertNotIn("published", source)
        self.assertEqual(tables[0]["total"], [76, 89])
        self.assertEqual(tables[0]["unitEn"], "USD thousand")
        with self.assertRaises(ValueError):
            parse("October 21")

    def test_lam_uses_fiscal_period_not_stale_accessibility_caption(self):
        page = b'<div data-year="2024"><div class="item_name">SEPTEMBER QUARTER</div><a aria-label="2014 March" href="/new.pdf">FORM 10-Q</a></div>'
        self.assertEqual(lam_list(page)["interim"][0], (2024, 9))

    def test_refresh_preserves_previous_packet_and_rejects_other_ciks(self):
        original = {"ticker": "SNDK", "annual": [], "interim": []}
        fetch = lambda url: SITEMAP if url.endswith("sitemap.xml") else sandisk()
        result, status = refresh_technology(original, 2023554, fetch)
        self.assertEqual(len(status["latest"]), 1)  # fixture has annual numbers only
        self.assertTrue(status["warnings"])
        self.assertEqual(original["annual"], [])
        future = result["annual"][0]["periods"][-1]
        future["end"] = "2026-06-28"
        with self.assertRaises(ValueError):
            refresh_technology(result, 2023554, fetch)
        with self.assertRaises(ValueError):
            refresh_technology(original, 1, fetch)


if __name__ == "__main__":
    main()
