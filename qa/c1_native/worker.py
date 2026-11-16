"""Test-only bootstrap: require new Hancom ownership, then run real worker."""
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from qa.c1_baseline.run_baseline import configure_dependencies
dll = configure_dependencies(Path(os.environ['C1_NATIVE_DEPS']))
from qa.c1_native.measure_open import hancom_pids
import win32com.client
import win32gui
import win32process

def deny(*a, **kw):
    raise RuntimeError('Network disabled in synthetic native test')
socket.socket.connect = deny
socket.getaddrinfo = deny
real_dispatch = win32com.client.DispatchEx

def guarded(progid, *args, **kwargs):
    before = hancom_pids()
    if before:
        raise RuntimeError('Existing Hancom session: activation refused')
    obj = real_dispatch(progid, *args, **kwargs)
    hwnd = int(obj.XHwpWindows.Item(0).WindowHandle)
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if not win32gui.IsWindow(hwnd) or pid in before or pid not in hancom_pids():
        raise RuntimeError('Ownership unproven: no document mutation or Quit')
    with (Path(os.environ['C1_NATIVE_EVIDENCE']) / 'com-ownership.jsonl').open('a', encoding='utf-8') as out:
        out.write(json.dumps({'pid': pid, 'hwnd': hwnd, 'before': before, 'time': time.time()}) + '\n')
    return obj

win32com.client.DispatchEx = guarded
sys.argv = [str(REPO / 'main.py'), *sys.argv[1:]]
runpy.run_path(str(REPO / 'main.py'), run_name='__main__')
