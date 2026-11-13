"""Read-only native Hancom Open measurements; synthetic C1 outputs only.

Each repeat uses its own COM process. A parent watchdog records a stalled child
without killing Hancom or silently retrying it. Raw output must remain local.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import time
import traceback

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
NAMES = ('C1_A', 'C1_B', 'C1_RENAMED', 'C1_LONG')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)


def hancom_pids():
    import win32process
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    found = []
    for pid in win32process.EnumProcesses():
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            continue
        try:
            size = wintypes.DWORD(32768)
            name = ctypes.create_unicode_buffer(size.value)
            if kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)) and Path(name.value).name.lower() == 'hwp.exe':
                found.append(pid)
        finally:
            kernel.CloseHandle(handle)
    return found


def child(args):
    from qa.c1_baseline.run_baseline import configure_dependencies
    dll = configure_dependencies(args.deps_dir)
    import pythoncom
    import win32com.client
    import win32gui
    import win32process
    from inspection.core import Report, verify_xml

    def deny(*a, **kw):
        raise RuntimeError('Network disabled in synthetic native measurement')
    socket.socket.connect = deny
    socket.getaddrinfo = deny
    output = args.output
    def event(kind, **values):
        with (output / 'events.jsonl').open('a', encoding='utf-8') as out:
            out.write(json.dumps({'event': kind, 'time': time.time(), **values}, ensure_ascii=False) + '\n')
    before = hancom_pids()
    event('preflight', existing_pids=before)
    if before:
        raise RuntimeError('Existing Hancom session: no activation performed')
    pythoncom.CoInitialize()
    hwp = None
    owned = False
    results = []
    started = time.monotonic()
    try:
        hwp = win32com.client.DispatchEx('HWPFrame.HwpObject')
        hwnd = int(hwp.XHwpWindows.Item(0).WindowHandle)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        owned = bool(win32gui.IsWindow(hwnd) and pid not in before and pid in hancom_pids())
        event('ownership', pid=pid, hwnd=hwnd, owned=owned, activation_seconds=time.monotonic() - started)
        if not owned:
            raise RuntimeError('Ownership unproven: no document action or Quit permitted')
        hwp.XHwpWindows.Item(0).Visible = True
        for name in NAMES:
            path = args.input_root / 'outputs' / (name + '.hwp')
            expected = json.loads((args.input_root / 'evidence' / (name + '-expected.json')).read_text(encoding='utf-8'))
            if not ('가상' in expected['findings'] or 'C1-LONG-' in expected['findings']):
                raise ValueError('Only declared synthetic C1 reports are accepted')
            report = Report(expected['title'], tuple(expected['general'].items()), expected['findings'], expected['actions'], expected['checks'], expected['document_title'])
            original = digest(path)
            hwp.Clear(1)
            event('open_start', name=name)
            tick = time.monotonic()
            opened = hwp.Open(str(path), 'HWP', 'readonly:true')
            open_seconds = time.monotonic() - tick
            if not opened:
                raise RuntimeError('Hancom Open returned false: ' + name)
            xml = hwp.GetTextFile('HWPML2X', '')
            verify_xml(xml, report)
            if name == 'C1_LONG' and not all('C1-LONG-%02d' % i in xml for i in range(1, 61)):
                raise AssertionError('Missing long-report marker')
            if digest(path) != original:
                raise AssertionError('Input HWP changed')
            row = {'name': name, 'open_seconds': round(open_seconds, 6), 'pages': int(hwp.PageCount), 'sha256': original, 'status': 'PASS'}
            results.append(row)
            event('open_complete', **row)
        write_json(output / 'results.json', {'result': 'PASS', 'opens': results, 'scope': 'Actual COM Open; synthetic final files read-only; content/format verified; no SaveAs or security prompt automation'})
    except BaseException:
        event('failure', traceback=traceback.format_exc())
        raise
    finally:
        if owned:
            hwp.Clear(1)
            hwp.Quit()
            event('owned_quit')
        pythoncom.CoUninitialize()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps-dir', type=Path, required=True)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3, choices=(3,))
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    args.deps_dir = args.deps_dir.resolve()
    args.input_root = args.input_root.resolve()
    args.output = args.output.resolve()
    if os.name != 'nt' or str(args.input_root).startswith('\\\\') or str(args.output).startswith('\\\\'):
        raise SystemExit('Local Windows synthetic test paths required')
    if args.child:
        return child(args)
    args.output.mkdir(parents=True, exist_ok=False)
    runtime = args.output / 'runtime-temp'
    runtime.mkdir()
    env = dict(os.environ, TEMP=str(runtime), TMP=str(runtime), PYTHONDONTWRITEBYTECODE='1')
    before = {name: digest(args.input_root / 'outputs' / (name + '.hwp')) for name in NAMES}
    runs = []
    for index in range(1, 4):
        target = args.output / ('trial-%02d' % index)
        target.mkdir()
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child', '--deps-dir', str(args.deps_dir), '--input-root', str(args.input_root), '--output', str(target)]
        with (target / 'console.log').open('x', encoding='utf-8') as log:
            proc = subprocess.Popen(command, stdout=log, stderr=log, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            tick = time.monotonic()
            warned = False
            while proc.poll() is None:
                elapsed = time.monotonic() - tick
                if elapsed > 60 and not warned:
                    write_json(target / 'watchdog-warning.json', {'elapsed_seconds': elapsed, 'child_pid': proc.pid, 'action': 'observe only; no retry/kill'})
                    warned = True
                if elapsed > 120:
                    write_json(args.output / 'summary.json', {'result': 'INCOMPLETE_RUNNING_CHILD', 'child_pid': proc.pid, 'completed_runs': runs, 'note': 'No automatic kill/retry; inspect ownership log and existing sessions before any cleanup'})
                    return 2
                time.sleep(.1)
        result_path = target / 'results.json'
        if proc.returncode or not result_path.exists():
            write_json(args.output / 'summary.json', {'result': 'FAIL', 'failed_trial': index, 'exit_code': proc.returncode, 'completed_runs': runs})
            return 1
        runs.append(json.loads(result_path.read_text(encoding='utf-8')))
        time.sleep(2)  # Allow normal owned Quit to finish; never terminate another process.
    after = {name: digest(args.input_root / 'outputs' / (name + '.hwp')) for name in NAMES}
    samples = [row['open_seconds'] for run in runs for row in run['opens']]
    summary = {'result': 'PASS' if before == after else 'FAIL_INPUT_CHANGED', 'runs': runs,
               'opens': len(samples), 'inputs_unchanged': before == after,
               'observed_open_seconds_including_user_approval': {'min': min(samples), 'median': statistics.median(samples), 'max': max(samples)},
               'interpretation': 'Elapsed COM call time includes manual Hancom file-access approval waiting. Not pure processing time, SLA, or performance improvement.'}
    write_json(args.output / 'summary.json', summary)
    print(json.dumps({key: summary[key] for key in ('result', 'opens', 'inputs_unchanged', 'observed_open_seconds_including_user_approval')}))
    return 0 if before == after else 1


if __name__ == '__main__':
    raise SystemExit(main())
