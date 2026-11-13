"""Run existing tests unchanged, in isolated temporary locations, offline.

Original QA scripts are byte-identical copies with their output routed to an
isolated test tree. Missing fixtures/assertion failures are reported unchanged.
"""
import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import time
import traceback
import unittest
from unittest.mock import patch

from run_baseline import configure_dependencies, production_manifest, head_commit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deps-dir', type=Path)
    args = parser.parse_args()
    dll_handle = configure_dependencies(args.deps_dir)
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(REPO / 'tests'))
    sys.dont_write_bytecode = True
    output = args.output.resolve()
    if not output.is_relative_to(REPO):
        raise SystemExit('Use a test output directory within the local checkout')
    output.mkdir(parents=True, exist_ok=False)
    temp = output / 'temp'
    temp.mkdir()
    tempfile.tempdir = str(temp)
    os.environ['TEMP'] = os.environ['TMP'] = str(temp)
    before = production_manifest()
    network_attempts, com_attempts, vault_attempts = [], [], []

    def audit(event, values):
        if event in {'socket.connect', 'socket.getaddrinfo'}:
            network_attempts.append(event)
            raise RuntimeError('Network forbidden in regression run')
    sys.addaudithook(audit)

    def no_hancom(*args, **kwargs):
        com_attempts.append('HANCOM_ACTIVATION_ATTEMPT')
        raise RuntimeError('Real Hancom activation forbidden')

    def no_vault(*args, **kwargs):
        vault_attempts.append('REAL_VAULT_ATTEMPT')
        raise RuntimeError('Real credential access forbidden')

    import win32com.client

    captured_results = []
    original_run = unittest.TextTestRunner.run
    def observe_test_result(runner, test):
        result = original_run(runner, test)
        captured_results.append({'run': result.testsRun, 'failures': len(result.failures),
                                 'errors': len(result.errors), 'skipped': len(result.skipped),
                                 'failure_ids': [t.id() for t, _ in result.failures],
                                 'error_ids': [t.id() for t, _ in result.errors]})
        return result

    results = []
    with ExitStack() as guards:
        guards.enter_context(patch('win32com.client.DispatchEx', side_effect=no_hancom))
        guards.enter_context(patch('win32com.client.Dispatch', side_effect=no_hancom))
        guards.enter_context(patch('pythoncom.CoCreateInstance', side_effect=no_hancom))
        guards.enter_context(patch('pythoncom.CoCreateInstanceEx', side_effect=no_hancom))
        from qa.c1_acceptance.storage_double import install
        install(guards)
        import test_shortcut_install
        guards.enter_context(patch.object(test_shortcut_install.NativeInstallerTests,'__unittest_skip__',True,create=True))
        guards.enter_context(patch.object(test_shortcut_install.NativeInstallerTests,'__unittest_skip_why__','Actual COM/installer integration is not approved in this task',create=True))
        for name in ('read', 'save', 'delete'):
            guards.enter_context(patch('inspection.vault.' + name, side_effect=no_vault))
        guards.enter_context(patch('unittest.TextTestRunner.run', new=observe_test_result))
        tasks = [('existing_units', REPO / 'qa' / 'run_unit_checks.py'),
                 ('harness_units', HERE / 'test_measurement.py')]
        for name, script in tasks:
            buffer = io.StringIO()
            start = time.monotonic()
            error = None
            status = 0
            try:
                with redirect_stdout(buffer), redirect_stderr(buffer):
                    if name == 'existing_units':
                        runpy.run_path(str(script), run_name='__main__')
                    else:
                        import test_measurement
                        unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_measurement))
            except SystemExit as exc:
                status = int(exc.code or 0)
            except Exception as exc:
                error = type(exc).__name__ + ': ' + str(exc)
                status = 2
            (output / (name + '.log')).write_text(buffer.getvalue(), encoding='utf-8')
            observed = captured_results[-1] if captured_results else {}
            passed = status == 0 and not error and not observed.get('errors') and not observed.get('failures')
            results.append({'name': name, 'passed': passed, 'exit_code': status,
                            'exception': error, 'unittest': observed,
                            'seconds': round(time.monotonic() - start, 4)})
            print(name, results[-1], flush=True)

        import tkinter as tk
        original_tk = tk.Tk
        roots, callbacks = [], []
        class TrackedTk(original_tk):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                roots.append(self)
            def report_callback_exception(self, exc, val, tb):
                callbacks.append(exc.__name__ + ': ' + str(val))

        for name in ('api_connection_checks', 'report_header_checks', 'reset_checks', 'workflow_checks'):
            target_dir = output / 'isolated' / name / 'qa'
            target_dir.mkdir(parents=True)
            script = target_dir / (name + '.py')
            original = REPO / 'qa' / script.name
            shutil.copyfile(original, script)
            assert script.read_bytes() == original.read_bytes()
            start = time.monotonic()
            buffer = io.StringIO()
            error = None
            notices = []
            callbacks.clear()
            roots.clear()
            try:
                with redirect_stdout(buffer), redirect_stderr(buffer), patch('tkinter.Tk', TrackedTk), \
                        patch('inspection.ui.messagebox.showinfo', side_effect=lambda title, *a, **kw: notices.append(str(title)) or 'ok'), \
                        patch('inspection.ui.messagebox.showerror', return_value='ok'):
                    runpy.run_path(str(script), run_name='__main__')
            except Exception as exc:
                error = type(exc).__name__ + ': ' + str(exc)
                buffer.write(traceback.format_exc().replace(str(REPO), '<REPO>'))
            finally:
                for root in roots:
                    try:
                        for timer in root.tk.call('after', 'info'):
                            root.after_cancel(timer)
                        root.destroy()
                    except tk.TclError:
                        pass
            (output / (name + '.log')).write_text(buffer.getvalue(), encoding='utf-8')
            results.append({'name': name, 'passed': error is None and not callbacks,
                            'exception': error, 'callback_errors': list(callbacks),
                            'notice_titles': notices,
                            'source_copy_identical': script.read_bytes() == original.read_bytes(),
                            'seconds': round(time.monotonic() - start, 4)})
            print(name, results[-1], flush=True)

    after = production_manifest()
    result = {'source_commit': head_commit(), 'source_unchanged': before == after,
              'source_manifest_before': before, 'source_manifest_after': after,
              'network_attempts': network_attempts, 'hancom_attempts': com_attempts,
              'real_vault_attempts': vault_attempts, 'results': results,
              'safety_exclusions': ['Four NativeInstallerTests require actual ShellLink/WScript COM and are explicitly skipped'],
              'storage_double': 'IStorage/ILockBytes mocked; native CFB serialization not validated',
              'scope': 'No real API, COM activation or credential access. Four native installer tests explicitly skipped; HWP storage uses a synthetic double.'}
    (output / 'regressions.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if before == after and all(r['passed'] for r in results) and not network_attempts and not com_attempts and not vault_attempts else 1


if __name__ == '__main__':
    raise SystemExit(main())
