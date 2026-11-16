"""Run synthetic PDF QA offline and inventory all root QA entry points."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from qa.c1_baseline.run_baseline import configure_dependencies, SafetyBoundary


def main():
    parser = argparse.ArgumentParser()
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
    tempfile.tempdir = str(temp)
    sys.path.insert(0, str(REPO / 'qa'))
    guard = SafetyBoundary(output)
    sys.meta_path.insert(0, guard)
    sys.addaudithook(guard.audit)
    log = io.StringIO()
    error = None
    guard.active = True
    try:
        with redirect_stdout(log), redirect_stderr(log):
            sys.argv = ['pdf_speed_benchmark.py']
            runpy.run_path(str(REPO / 'qa/pdf_speed_benchmark.py'), run_name='__main__')
    except Exception as exc:
        error = repr(exc)
    finally:
        guard.active = False
    (output / 'pdf_speed_benchmark.log').write_text(log.getvalue(), encoding='utf-8')
    statuses = {}
    for path in sorted((REPO / 'qa').glob('*.py')):
        name = path.stem
        if name in {'api_connection_checks', 'report_header_checks', 'reset_checks', 'workflow_checks', 'run_unit_checks'}:
            status = 'SEE_REGRESSIONS'
        elif name == 'pdf_speed_benchmark':
            status = 'FAIL' if error else 'PASS'
        elif name in {'pdf_baseline', 'pdf_visual_verify'}:
            status = 'HELPER_EXECUTED_BY_PDF_BENCHMARK'
        elif name == 'verify_frozen':
            status = 'NOT_RUN_NO_NEW_FROZEN_BUILD'
        elif name == 'package_release':
            status = 'NOT_RUN_RELEASE_NOT_AUTHORIZED'
        else:
            status = 'NOT_RUN_REQUIRES_REAL_API_OR_COM_OR_NATIVE_HWP'
        statuses[path.name] = status
    result = {'qa_inventory': statuses, 'pdf_error': error, 'forbidden_attempts': guard.attempts,
              'note': 'Synthetic local PDF comparison only; durations are not C1 user outcomes.'}
    (output / 'inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if error or guard.attempts else 0


if __name__ == '__main__':
    raise SystemExit(main())
