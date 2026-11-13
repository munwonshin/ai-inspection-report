"""Original 151 tests, real ShellLink/storage, isolated synthetic install paths."""
import argparse
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from qa.c1_baseline.run_baseline import configure_dependencies, production_manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dll = configure_dependencies(args.deps_dir)
    root = args.output.resolve()
    if not root.is_relative_to(REPO):
        raise SystemExit('Use a new output directory in this checkout')
    root.mkdir(parents=True, exist_ok=False)
    temp = root / 'temp'
    temp.mkdir()
    os.environ['TEMP'] = os.environ['TMP'] = str(temp)
    tempfile.tempdir = str(temp)
    def deny(*a, **kw):
        raise RuntimeError('Network/Hancom activation forbidden in unit run')
    socket.socket.connect = deny
    socket.getaddrinfo = deny
    import win32com.client
    win32com.client.Dispatch = deny
    win32com.client.DispatchEx = deny
    before = production_manifest()
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(REPO / 'tests'))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    record = {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'failure_ids': [t.id() for t, _ in result.failures],
              'error_ids': [t.id() for t, _ in result.errors], 'source_unchanged': before == production_manifest(),
              'source_manifest': before, 'native_shell_storage': True, 'real_hancom': False}
    (root / 'tests.log').write_text(stream.getvalue(), encoding='utf-8')
    (root / 'results.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('run', 'failures', 'errors', 'skipped', 'source_unchanged')}))
    return 0 if result.wasSuccessful() and result.testsRun == 151 and not result.skipped and record['source_unchanged'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
