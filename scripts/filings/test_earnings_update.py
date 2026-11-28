import unittest
from unittest.mock import patch

from refresh import nvidia_earnings_update


class EarningsBeforePeriodicFiling(unittest.TestCase):
    def test_new_earnings_keep_the_annual_check(self):
        annual = {'kind': 'annual', 'periodEnd': '2026-01-25', 'url': 'https://www.sec.gov/annual'}
        old = {'kind': 'interim', 'periodEnd': '2026-07-26', 'url': 'https://www.sec.gov/quarter'}
        new = {'kind': 'interim', 'periodEnd': '2026-10-25', 'url': 'https://nvidianews.nvidia.com/results'}
        status = {'latest': [annual, old], 'warnings': ['interim-unavailable']}
        with patch('refresh.refresh_nvidia', return_value=({'interim': ['newest']}, {'latest': [new], 'warnings': []})):
            packet, checks, _ = nvidia_earnings_update({}, status, 'SEC', 1045810, None)
        self.assertEqual(packet['interim'], ['newest'])
        self.assertEqual(checks, {'latest': [annual, new], 'warnings': []})

    def test_missing_release_preserves_existing_verified_quarter(self):
        status = {'latest': [{'kind': 'interim', 'periodEnd': '2026-10-25'}], 'warnings': []}
        packet = {'interim': ['verified']}
        with patch('refresh.refresh_nvidia', side_effect=OSError('offline')):
            kept, checks, provider = nvidia_earnings_update(packet, status, 'SEC', 1045810, None)
        self.assertIs(kept, packet)
        self.assertEqual(checks['latest'], status['latest'])
        self.assertEqual(provider, 'SEC')
