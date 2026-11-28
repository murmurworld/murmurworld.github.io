"""Exercise the investor-linked 10-Q route with SEC's reported September 2026 values."""

from copy import deepcopy
from datetime import date
import unittest

from issuer_tesla import CIK, INDEX, discover, refresh_tesla


ARCHIVE = "https://www.sec.gov/Archives/edgar/data/1318605"
Q3_PATH = ARCHIVE + "/000162828026066775/"
Q3 = Q3_PATH + "tsla-20260930.htm"
FILING_INDEX = Q3_PATH + "0001628280-26-066775-index.htm"
Q2 = ARCHIVE + "/000162828026051234/tsla-20260630.htm"
IR = f"""
<table>
  <tr><td>2026</td><td>Q4</td><td><a href="{Q3}">10-K</a></td></tr>
  <tr><td>2026</td><td>Q2</td><td><a href="{Q2}">10-Q</a></td></tr>
  <tr><td>2026</td><td>Q3</td><td><a href="{Q3}">10-Q</a></td></tr>
  <tr><td><a href="{Q3.replace('www.sec.gov', 'example.org').replace('20260930', '20270930')}">10-Q</a></td></tr>
</table>
""".encode()
DATE_META = b"""
<div class="formGrouping"><div class="infoHead">Filing Date</div><div class="info">2026-10-22</div></div>
<div class="formGrouping"><div class="infoHead">Period of Report</div><div class="info">2026-09-30</div></div>
"""


def inline_report():
    # Tesla's 2026-09-30 10-Q, Consolidated Statements of Operations, USD million.
    amounts = {
        "old-quarter": ("2025-07-01", "2025-09-30", (28095, 1624, 1373)),
        "quarter": ("2026-07-01", "2026-09-30", (28046, 718, 787)),
        "old-ytd": ("2025-01-01", "2025-09-30", (69926, 2946, 2954)),
        "ytd": ("2026-01-01", "2026-09-30", (78669, 2057, 2378)),
    }
    contexts = [
        f"""<x:context id="{name}">
           <x:entity><x:identifier>{CIK}</x:identifier></x:entity>
           <x:period><x:startDate>{start}</x:startDate><x:endDate>{end}</x:endDate></x:period>
        </x:context>"""
        for name, (start, end, values) in amounts.items()
    ]
    names = ("Revenues", "OperatingIncomeLoss", "NetIncomeLoss")
    facts = [
        f'<ix:nonFraction name="g:{metric}" contextRef="{name}" unitRef="usd" scale="6">{value:,}</ix:nonFraction>'
        for name, (_, _, values) in amounts.items()
        for metric, value in zip(names, values, strict=True)
    ]
    return f"""
    <html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
          xmlns:x="http://www.xbrl.org/2003/instance" xmlns:iso="http://www.xbrl.org/2003/iso4217"
          xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:g="http://fasb.org/us-gaap/2026">
    {''.join(contexts)}
      <x:unit id="usd"><x:measure>iso:USD</x:measure></x:unit>
      <ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="quarter">{CIK:010d}</ix:nonNumeric>
      <ix:nonNumeric name="dei:DocumentType" contextRef="quarter">10-Q</ix:nonNumeric>
      <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="quarter">September 30, 2026</ix:nonNumeric>
    {''.join(facts)}
    </html>""".strip().encode()


class TeslaFiling(unittest.TestCase):
    def setUp(self):
        self.report = {
            "ticker": "TSLA",
            "slug": "tesla",
            "easy": {"line": "existing editorial content"},
            "annual": [],
            "interim": [{"id": "segments", "currency": "USD", "periods": [{"end": "2026-06-30"}], "source": {"url": Q2}}],
        }
        self.original = deepcopy(self.report)
        self.pages = {INDEX: IR, FILING_INDEX: DATE_META, Q3: inline_report()}

    def test_picks_teslas_newest_original_quarter(self):
        self.assertEqual(discover(IR), (date(2026, 9, 30), "000162828026066775", Q3))

    def test_reads_reported_quarter_and_nine_months_and_keeps_earlier_table(self):
        updated, state = refresh_tesla(self.report, CIK, self.pages.__getitem__)
        quarter, year_to_date, previous = updated["interim"]
        self.assertEqual([quarter["id"], year_to_date["id"]], ["sec-consolidated-quarter", "sec-consolidated-nine-months"])
        self.assertEqual([r["values"] for r in quarter["rows"]], [[28095, 28046], [1624, 718], [1373, 787]])
        self.assertEqual([r["values"] for r in year_to_date["rows"]], [[69926, 78669], [2946, 2057], [2954, 2378]])
        self.assertEqual(state["latest"], [{
            "kind": "interim", "label": "10-Q", "url": Q3, "filed": "2026-10-22", "periodEnd": "2026-09-30"
        }])
        self.assertEqual(previous, self.original["interim"][0])
        self.assertIsNot(previous, self.report["interim"][0])
        self.assertEqual(updated["annual"], self.original["annual"])
        self.assertEqual(updated["easy"], self.original["easy"])
        self.assertEqual(self.report, self.original)

    def test_fails_without_replacing_data_on_incomplete_or_unavailable_sources(self):
        for url, data in (
            (INDEX, b"<html>no filings</html>"),
            (FILING_INDEX, DATE_META.replace(b"2026-09-30", b"2026-06-30")),
            (Q3, inline_report().replace(b'name="g:Revenues" contextRef="ytd"', b'name="g:Unrecognized" contextRef="ytd"')),
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    refresh_tesla(self.report, CIK, {**self.pages, url: data}.__getitem__)
                self.assertEqual(self.report, self.original)

        def offline(url):
            if url == Q3:
                raise OSError("SEC unavailable")
            return self.pages[url]

        with self.assertRaises(OSError):
            refresh_tesla(self.report, CIK, offline)
        self.assertEqual(self.report, self.original)
