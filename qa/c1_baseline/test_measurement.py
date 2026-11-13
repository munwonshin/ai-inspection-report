"""Tests of the measurement oracle, separate from the 151 product tests."""
import copy
import json
from pathlib import Path
import unittest

from run_baseline import summarize


def row(kind, calls, passed=True, **extra):
    return dict({'class': kind, 'setup_valid': True, 'infra_error': None,
                 'export_entry_count': calls, 'contract_pass': passed,
                 'report_matches_expected': True}, **extra)


class MeasurementTests(unittest.TestCase):
    def test_unreviewed_entry_is_failure_not_a_successful_save(self):
        result = summarize([row('U', 1, False), row('N', 1)], (1, 1))
        self.assertEqual(result['M01_percent'], 100)
        self.assertEqual(result['contract_failures'], 1)
        self.assertFalse(result['all_contracts_pass'])

    def test_blocking_everything_cannot_pass(self):
        result = summarize([row('U', 0), row('N', 0, False)], (1, 1))
        self.assertEqual(result['M01_percent'], 0)
        self.assertEqual(result['M02_percent'], 100)
        self.assertFalse(result['all_contracts_pass'])

    def test_zero_denominators_are_unknown(self):
        result = summarize([])
        self.assertIsNone(result['M01_percent'])
        self.assertIsNone(result['M02_percent'])
        self.assertFalse(result['measurement_complete'])

    def test_errors_and_missing_cases_prevent_complete_measurement(self):
        result = summarize([row('U', 0), row('N', 0, False, infra_error='driver error')], (1, 1))
        self.assertEqual(result['infra_errors'], 1)
        self.assertEqual(result['N_valid'], 0)
        self.assertFalse(result['measurement_complete'])

    def test_duplicate_normal_entry_fails_separate_contract(self):
        result = summarize([row('U', 0), row('N', 2, False)], (1, 1))
        self.assertEqual(result['M02_percent'], 0)
        self.assertEqual(result['duplicate_entry_cases'], 1)
        self.assertFalse(result['all_contracts_pass'])

    def test_wrong_report_is_not_hidden_by_zero_rates(self):
        result = summarize([row('U', 0), row('N', 1, False, report_matches_expected=False)], (1, 1))
        self.assertEqual(result['report_mismatches'], 1)
        self.assertFalse(result['all_contracts_pass'])

    def test_complete_correct_suite_passes(self):
        result = summarize([row('U', 0), row('N', 1)], (1, 1))
        self.assertTrue(result['measurement_complete'])
        self.assertTrue(result['all_contracts_pass'])

    def test_manifest_is_six_distinct_risks_and_ten_normal_paths(self):
        manifest = json.loads((Path(__file__).parent / 'scenarios.json').read_text(encoding='utf-8'))
        cases = manifest['cases']
        self.assertEqual(len(cases), 16)
        self.assertEqual(len({c['id'] for c in cases}), 16)
        self.assertEqual(sum(c['class'] == 'U' for c in cases), 6)
        self.assertEqual(sum(c['class'] == 'N' for c in cases), 10)
        self.assertEqual(len({json.dumps(c['steps'], sort_keys=True) for c in cases}), 16)
        original = copy.deepcopy(cases)
        for case in cases:
            self.assertEqual(case['expected_calls'], 0 if case['class'] == 'U' else 1)
        self.assertEqual(cases, original)


if __name__ == '__main__':
    unittest.main()
