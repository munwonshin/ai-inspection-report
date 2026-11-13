"""Offline C1 acceptance runner; real Tk actions, synthetic external edges."""
import argparse
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from qa.c1_baseline.run_baseline import configure_dependencies, production_manifest, SafetyBoundary, head_commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dll_handle = configure_dependencies(args.deps_dir)
    sys.dont_write_bytecode = True
    output = args.output.resolve()
    if not output.is_relative_to(REPO):
        raise SystemExit('Output must stay in checkout')
    output.mkdir(parents=True, exist_ok=False)
    temp = output / 'temp'
    temp.mkdir()
    os.environ['C1_TEST_TEMP'] = str(temp)
    tempfile.tempdir = str(temp)
    before = production_manifest()
    guard = SafetyBoundary(output)
    sys.meta_path.insert(0, guard)
    sys.addaudithook(guard.audit)
    buffer = io.StringIO()
    outcomes = []

    class RecordedResult(unittest.TextTestResult):
        def startTest(self, test):
            super().startTest(test)
            print(test.id(), flush=True)
        def addSuccess(self, test):
            super().addSuccess(test)
            outcomes.append({'id': test.id(), 'status': 'PASS'})

        def addFailure(self, test, err):
            super().addFailure(test, err)
            outcomes.append({'id': test.id(), 'status': 'FAIL'})

        def addError(self, test, err):
            super().addError(test, err)
            outcomes.append({'id': test.id(), 'status': 'ERROR'})

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            outcomes.append({'id': str(subtest), 'status': 'PASS' if err is None else 'FAIL'})

    guard.active = True
    try:
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern='test_*.py')
        result = unittest.TextTestRunner(stream=buffer, verbosity=2, resultclass=RecordedResult).run(suite)
    finally:
        guard.active = False
    after = production_manifest()
    (output / 'checks.log').write_text(buffer.getvalue(), encoding='utf-8')
    record = {'source_commit': head_commit(), 'source_manifest': before,
              'source_unchanged': before == after, 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'outcomes': outcomes,
              'forbidden_attempts': guard.attempts,
              'scope': 'Real UI controls; API/vault/HWP preparation/export mocked. No actual COM or HWP file.'}
    (output / 'checks.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(buffer.getvalue())
    print(json.dumps({key: record[key] for key in ('tests_run', 'failures', 'errors', 'skipped', 'source_unchanged', 'forbidden_attempts')}))
    return 0 if result.wasSuccessful() and before == after and not guard.attempts else 1


if __name__ == '__main__':
    raise SystemExit(main())
