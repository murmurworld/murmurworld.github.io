"""Regression fixtures for issuer-published inline XBRL and publication failure state."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lxml import etree
import refresh
from issuer_filings import read_instance, scaled_value
from issuer_alphabet import (
    ADVERTISING,
    AD_TOTAL,
    SEGMENTS,
    SERVICES_PRODUCTS,
    SUBSCRIPTIONS,
    alphabet_tables,
    segment_dimension,
)
from public_company_sec import amount, iso, table_base


class IssuerFilings(unittest.TestCase):
    def test_supplement_keeps_newer_regulator_source_and_unresolved_segment_warning(self):
        source = {
            "kind": "interim",
            "label": "10-Q",
            "periodEnd": "2026-09-30",
            "url": "https://regulator/q",
            "filed": "2026-10-30",
        }
        packet = {
            "ticker": "TEST",
            "annual": [],
            "interim": [{"measure": "financial-results", "source": {"url": "https://example/old"}}],
        }
        status = {
            "latest": [source],
            "warnings": ["companyfacts-unavailable", "interim-segment-source-unavailable"],
        }
        item = dict(source, url="https://issuer/q")
        report = {**packet, "interim": [{"measure": "financial-results", "source": item}]}
        fresh = {"latest": [item], "warnings": []}
        read = lambda *args: (report, fresh)
        new, verification, provider = refresh.supplement_sec(packet, status, read, 42, None)
        self.assertEqual(provider, "SEC + Issuer IR")
        self.assertEqual(new["interim"], report["interim"])
        self.assertEqual(verification["warnings"], ["interim-segment-source-unavailable"])
        self.assertEqual(verification["latest"][0], source)
        item["periodEnd"] = "2026-06-30"
        self.assertEqual(refresh.supplement_sec(packet, status, read, 42, None), (packet, status, "SEC"))

    def test_alphabet_segment_subtotals_and_consolidation_difference(self):
        period = (iso("2025-01-01"), iso("2025-12-31"))
        filing = {
            "label": "10-K",
            "filed": "2026-02-05",
            "url": "https://example.org/filing",
            "periodEnd": "2025-12-31",
        }
        rows = [{"key": k} for k in [*SEGMENTS, AD_TOTAL, *ADVERTISING, SUBSCRIPTIONS, "__residual"]]
        report = {"annual": [{"id": "segments", "rows": rows}]}
        concept = ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax")
        facts = {("us-gaap", "Revenues", "매출", "Revenue"): {period: 99_000_000}}
        parts = {
            (*concept, "StatementBusinessSegmentsAxis", period): {
                k: {n * 1_000_000} for k, n in zip(SEGMENTS, (70, 29, 1))
            },
            (*concept, SERVICES_PRODUCTS, period): {
                k: {n * 1_000_000}
                for k, n in zip((AD_TOTAL, *ADVERTISING, SUBSCRIPTIONS), (60, 30, 20, 10, 10))
            },
        }

        def read():
            return alphabet_tables(
                report, filing, "USD", [("annual", [period])], facts, parts, amount, table_base
            )

        table = read()[0]
        self.assertEqual(table["total"], [99])
        self.assertEqual(table["rows"][-1]["values"], [-1])
        self.assertEqual(table["compositionKeys"], list(SEGMENTS))
        parts[(*concept, SERVICES_PRODUCTS, period)][ADVERTISING[1]] = {19_000_000}
        self.assertEqual(read(), [])
        axes = [
            etree.Element("member", dimension="us-gaap:StatementBusinessSegmentsAxis"),
            etree.Element("member", dimension="srt:ProductOrServiceAxis"),
        ]
        axes[0].text = "goog:GoogleServicesMember"
        axes[1].text = "goog:GoogleSearchOtherMember"
        self.assertEqual(segment_dimension(axes, 1652044), (SERVICES_PRODUCTS, "GoogleSearchOtherMember"))
        self.assertIsNone(segment_dimension(axes, 42))

    def test_numeric_format_and_unit_boundaries(self):
        def val(text, fmt="", sign="", scale="0"):
            e = etree.Element("fact", format=fmt, sign=sign, scale=scale)
            e.text = text
            return scaled_value(e)

        self.assertEqual(val("1,200", "ixt:num-dot-decimal", "-", "6"), -1_200_000_000)
        self.assertEqual(val("—", "ixt:fixed-zero"), 0)
        self.assertIsNone(val("1,2", "ixt:num-dot-decimal"))
        self.assertIsNone(val("1.200", "ixt:num-comma-decimal"))

    def test_issuer_identification_and_observations(self):
        root = b"""<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:x="http://www.xbrl.org/2003/instance" xmlns:iso="http://www.xbrl.org/2003/iso4217" xmlns:dei="http://xbrl.sec.gov/dei/2025" xmlns:g="http://fasb.org/us-gaap/2025">
          <x:context id="c"><x:entity><x:identifier>42</x:identifier></x:entity><x:period><x:startDate>2025-01-01</x:startDate><x:endDate>2025-12-31</x:endDate></x:period></x:context>
          <x:unit id="usd"><x:measure>iso:USD</x:measure></x:unit>
          <ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="c">00042</ix:nonNumeric>
          <ix:nonNumeric name="dei:DocumentType" contextRef="c">10-K</ix:nonNumeric>
          <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c">December 31, 2025</ix:nonNumeric>
          <ix:nonFraction name="g:Revenues" contextRef="c" unitRef="usd" scale="6">250</ix:nonFraction></html>"""
        end, values, _ = read_instance(root, 42, "10-K", "USD")
        self.assertEqual(end, "2025-12-31")
        self.assertEqual(list(next(iter(values.values())).values()), [250_000_000])
        self.assertFalse(read_instance(root, 42, "10-K", "EUR")[1])
        with self.assertRaises(ValueError):
            read_instance(root, 43, "10-K", "USD")
        with self.assertRaises(ValueError):
            read_instance(root, 42, "10-Q", "USD")

    def test_extracted_instance_values_are_signed_and_scaled_already(self):
        data = b"""<x:xbrl xmlns:x="http://www.xbrl.org/2003/instance" xmlns:iso="http://www.xbrl.org/2003/iso4217" xmlns:dei="http://xbrl.sec.gov/dei/2025" xmlns:g="http://fasb.org/us-gaap/2025" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <x:context id="c"><x:entity><x:identifier>42</x:identifier></x:entity><x:period><x:startDate>2026-01-01</x:startDate><x:endDate>2026-03-31</x:endDate></x:period></x:context>
          <x:unit id="usd"><x:measure>iso:USD</x:measure></x:unit><x:unit id="eur"><x:measure>iso:EUR</x:measure></x:unit>
          <dei:DocumentType contextRef="c">10-Q</dei:DocumentType><dei:EntityCentralIndexKey contextRef="c">00042</dei:EntityCentralIndexKey><dei:DocumentPeriodEndDate contextRef="c">2026-03-31</dei:DocumentPeriodEndDate>
          <g:Revenues contextRef="c" unitRef="usd" decimals="-6">23000000</g:Revenues><g:NetIncomeLoss contextRef="c" unitRef="usd" decimals="-6">-2000000</g:NetIncomeLoss><g:NetIncomeLoss contextRef="c" unitRef="eur">5</g:NetIncomeLoss><g:NetIncomeLoss contextRef="c" unitRef="usd" xsi:nil="true"/></x:xbrl>"""
        end, observations, _ = read_instance(data, 42, "10-Q", "USD")
        self.assertEqual(end, "2026-03-31")
        self.assertEqual(
            {key[1]: next(iter(spans.values())) for key, spans in observations.items()},
            {"Revenues": 23_000_000, "NetIncomeLoss": -2_000_000},
        )
        with self.assertRaises(ValueError):
            read_instance(data, 43, "10-Q", "USD")
        with self.assertRaises(ValueError):
            read_instance(data, 42, "10-K", "USD")

    def test_failed_run_preserves_earlier_check_and_recovers(self):
        last = {"provider": "SEC", "checked": "2025-06-12", "latest": []}
        data = {
            "ticker": "TEST",
            "slug": "test",
            "easy": {},
            "annual": [],
            "interim": [],
            "filingCheck": last,
        }
        status = {
            "latest": [
                {"label": "10-K", "url": "https://www.sec.gov/Archives/example", "filed": "2026-11-25"}
            ],
            "warnings": [],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.json"
            path.write_text(json.dumps(data), encoding="utf8")
            with patch.object(sys, "argv", ["refresh", "--reports", folder]), patch.object(
                refresh, "sec_cik", return_value=42
            ):
                with patch.object(refresh, "refresh_sec", side_effect=OSError("offline")):
                    self.assertEqual(refresh.main(), 0)
                previous = json.loads(path.read_bytes())
                self.assertEqual(previous["filingCheck"], last)
                self.assertEqual(previous["filingAttempt"]["status"], "unavailable")
                with patch.object(refresh, "refresh_sec", return_value=(previous, status)):
                    self.assertEqual(refresh.main(), 0)
                self.assertNotIn("filingAttempt", json.loads(path.read_bytes()))


if __name__ == "__main__":
    unittest.main()
