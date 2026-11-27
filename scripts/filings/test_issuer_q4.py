import unittest

from playwright.sync_api import sync_playwright
from issuer_q4 import filing_date, listing


class IssuerFilingRows(unittest.TestCase):
    def test_accessible_label_and_other_issuer_in_same_directory(self):
        root = "https://d18rn0p25nwr6d.cloudfront.net"
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.set_content(
                f"""
              <table><tbody>
                <tr><td>12/31/24</td><td><a>10-Q<span> filing dated December 31, 2024</span></a></td>
                <td><a href="{root}/CIK-0000018230/aaa.zip">XBRL</a>
                <a href="{root}/CIK-0000018230/aaa.html">HTML</a></td></tr>
                <tr><td>11/12/25</td><td>10-Q</td>
                <td><a href="{root}/CIK-0000764764/bbb.zip">XBRL</a></td></tr>
                <tr><td>02/23/25</td><td>10-K</td>
                <td><a href="{root}/CIK-0000018230/ccc.zip">XBRL</a></td></tr>
              </tbody></table>"""
            )
            found = listing(page, "10-Q", "investors.caterpillar.com", 18230)
            self.assertEqual(
                found, ("2024-12-31", root + "/CIK-0000018230/aaa.html", root + "/CIK-0000018230/aaa.zip")
            )
            self.assertIsNone(listing(page, "10-Q", "investors.caterpillar.com", 100))
            browser.close()

    def test_reports_use_the_dates_shown_by_the_issuer(self):
        self.assertEqual(filing_date("Form 10-Q on Jul. 29, 2026"), "2026-07-29")
        self.assertEqual(filing_date("07/29/26"), "2026-07-29")
        self.assertIsNone(filing_date("07/36/26"))
