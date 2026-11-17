"""Explicit frozen-EXE synthetic diagnostic. Never used by normal startup.

Uses the bundled App and real frozen exporter worker. No AI or credential access.
Native file-access security approval remains a user action, never automated.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hwp_pids():
    import win32process
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=(wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    found=[]
    for pid in win32process.EnumProcesses():
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:continue
        try:
            n=wintypes.DWORD(32768);name=ctypes.create_unicode_buffer(n.value)
            if kernel.QueryFullProcessImageNameW(handle,0,name,ctypes.byref(n)) and Path(name.value).name.lower()=='hwp.exe':found.append(pid)
        finally:kernel.CloseHandle(handle)
    return found


def test_root(value):
    raw=Path(value)
    if not raw.is_absolute() or str(raw).startswith('\\\\'):raise ValueError('Local absolute test root required')
    for p in (raw,*raw.parents):
        if p.is_symlink() or p.is_junction():raise ValueError('No symlinks/junctions in test path')
    root=raw.resolve()
    fixture=json.loads((root/'inputs/fixture.json').read_text(encoding='utf-8'))
    if fixture.get('classification')!='SYNTHETIC_ONLY_NO_REAL_COMPANY_OR_PERSON':raise ValueError('Synthetic fixture required')
    return root,fixture


def deny(*args,**kwargs):
    raise RuntimeError('External API/credential access prohibited in frozen synthetic check')


def owned_hwp(log):
    import win32com.client,win32gui,win32process
    before=hwp_pids()
    if before:raise RuntimeError('Existing Hancom session: no activation performed')
    obj=win32com.client.DispatchEx('HWPFrame.HwpObject')
    hwnd=int(obj.XHwpWindows.Item(0).WindowHandle)
    _,pid=win32process.GetWindowThreadProcessId(hwnd)
    owned=bool(win32gui.IsWindow(hwnd) and pid not in before and pid in hwp_pids())
    with log.open('a',encoding='utf-8') as out:out.write(json.dumps({'pid':pid,'hwnd':hwnd,'before':before,'owned':owned})+'\n')
    if not owned:raise RuntimeError('COM ownership unproven: no mutation or Quit')
    return obj


def install_worker_guard():
    """Test-only wrapper; the actual exporter worker remains unchanged."""
    root,_=test_root(os.environ['AIR_C1_FROZEN_PROBE'])
    import win32com.client,win32gui,win32process
    original=win32com.client.DispatchEx
    def guarded(progid,*args,**kwargs):
        before=hwp_pids()
        if before:raise RuntimeError('Existing Hancom session: frozen worker refused')
        obj=original(progid,*args,**kwargs)
        hwnd=int(obj.XHwpWindows.Item(0).WindowHandle);_,pid=win32process.GetWindowThreadProcessId(hwnd)
        owned=bool(win32gui.IsWindow(hwnd) and pid not in before and pid in hwp_pids())
        with (root/'evidence/worker-ownership.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps({'pid':pid,'hwnd':hwnd,'before':before,'owned':owned})+'\n')
        if not owned:raise RuntimeError('COM ownership unproven: no mutation or Quit')
        mode=os.environ.get('AIR_R028_FAULT','')
        if mode:
            class Fault:
                def __getattr__(self,name):return getattr(obj,name)
                def SetTextFile(self,text,fmt,opt):
                    if fmt=='HWP':
                        if mode=='stall':time.sleep(90)
                        if mode=='failure':return False
                    return obj.SetTextFile(text,fmt,opt)
            return Fault()
        return obj
    win32com.client.DispatchEx=guarded
    socket.socket.connect=deny;socket.getaddrinfo=deny


def main():
    if not getattr(sys,'frozen',False):raise RuntimeError('This check requires the real bundled EXE')
    root,fixture=test_root(sys.argv[2]);response=Path(sys.argv[3]).resolve()
    if not response.is_relative_to(root/'evidence') or response.exists():raise ValueError('New response in evidence folder required')
    def early_error(kind,value,tb):
        if not response.exists():
            with response.open('x',encoding='utf-8') as out:json.dump({'result':'FAIL','frozen':True,'error':kind.__name__+': '+str(value)},out,ensure_ascii=False)
    sys.excepthook=early_error
    if list((root/'outputs').iterdir()):raise ValueError('Empty output folder required')
    if hwp_pids():raise RuntimeError('Existing Hancom session: check not started')
    os.environ['AIR_C1_FROZEN_PROBE']=str(root)
    os.environ['TEMP']=os.environ['TMP']=str(root/'runtime-temp')
    import tempfile
    tempfile.tempdir=str(root/'runtime-temp')
    socket.socket.connect=deny;socket.getaddrinfo=deny
    from unittest.mock import patch
    from contextlib import ExitStack
    from tkinterdnd2 import TkinterDnD
    from .ui import App
    from . import exporter,ui,vault,review
    from .core import Report,verify_xml
    from .desktop_shortcut import VERSION
    tk=TkinterDnD.Tk();tk.withdraw()
    app=App(tk,restore_api=False,restore_preferences=False)
    app.folder.set(str(root/'outputs'))
    for entry in app.entries:
        if 'textvariable' in entry.keys() and str(entry.cget('textvariable'))==str(app.folder):entry.configure(show='●')
    stack=ExitStack();notices=[];exports=[];expected={};cases={};reopened=[]
    actual_save=exporter.save
    def record(kind,**values):
        with (root/'evidence/events.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps({'event':kind,'time':time.time(),**values},ensure_ascii=False)+'\n')
    def save(report,folder,name,*,approved=False):
        if Path(folder).resolve()!=root/'outputs':raise ValueError('Test destination escaped root')
        exports.append(name);return actual_save(report,folder,name,approved=approved,
            timeout=20 if os.environ.get('AIR_R028_FAULT')=='stall' else 120)
    stack.enter_context(patch.object(exporter,'save',side_effect=save))
    stack.enter_context(patch.object(vault,'read',side_effect=deny))
    stack.enter_context(patch.object(ui.api,'request',side_effect=deny))
    for method in ('showinfo','showwarning','showerror'):
        stack.enter_context(patch.object(ui.messagebox,method,side_effect=lambda title,msg,**kw:notices.append({'title':title,'message':msg}) or 'ok'))
    stack.enter_context(patch.object(ui.messagebox,'askyesno',return_value=True))
    def text(widget,value):
        widget.delete('1.0','end');widget.insert('1.0',value);widget.edit_modified(True);tk.update()
    def general(profile):
        for k,v in fixture['profiles'][profile]['general'].items():app.general[k].set(v)
        app.document_context_vars['program_year'].set(fixture['program_year']);app.document_context_vars['division'].set(fixture['division'])
        text(app.minutes,fixture['profiles'][profile]['minutes'])
    def body(profile):
        text(app.findings,fixture['profiles'][profile]['findings']);text(app.actions,fixture['profiles'][profile]['actions'])
    def hashes():return {p.name:digest(p) for p in (root/'outputs').iterdir() if p.is_file()}
    def reviewed():
        app.review_button.invoke();tk.update()
        if app.review_note.get()!='현재 자료 대조·검토 완료':raise AssertionError('Review UI did not complete')
    def approve(name):
        app.name.set(name);tk.update();expected[name]=app.snapshot();app.approve_button.invoke()
    def saved(name):
        if not app.saved_current or not (root/'outputs'/(name+'.hwp')).is_file():raise AssertionError('Actual frozen save failed: '+str(notices))
        if app.snapshot()!=expected[name]:raise AssertionError('Approved body changed during save')
        cases[name]='PASS';record('saved',name=name,sha256=digest(root/'outputs'/(name+'.hwp')))
    memo={}
    def a_ready():general('A');body('A');reviewed();approve('C1_A')
    def a_saved():saved('C1_A');memo['a']=hashes();memo['body']=app.get(app.findings);app.load_pdf(str(root/'inputs/plan_B.pdf'))
    def b_changed():
        general('B')
        if app.get(app.findings)!=memo['body']:raise AssertionError('Source change erased existing body')
        memo['entries']=len(exports);app.name.set('C1_BLOCKED');app.approve_button.invoke()
        if len(exports)!=memo['entries'] or hashes()!=memo['a'] or notices[-1]['title']!='자료 재검수 필요':raise AssertionError('Unreviewed save not blocked by C1')
        cases['B_unreviewed_block']='PASS';record('unreviewed_blocked',body_preserved=True)
        body('B');reviewed();approve('C1_B')
    def b_saved():
        saved('C1_B');memo['protected']=hashes();memo['report']=app.snapshot();app.approve_button.invoke()
    def duplicate():
        if hashes()!=memo['protected'] or app.snapshot()!=memo['report'] or app.saved_current or not app.open_file.instate(['disabled']):raise AssertionError('Duplicate save/file/status protection failed')
        if not any('같은 이름' in n['message'] for n in notices):raise AssertionError('Duplicate reason missing')
        cases['duplicate_and_failure_state']='PASS';approve('C1_RENAMED')
    def renamed():
        saved('C1_RENAMED');memo['protected']=hashes()
        text(app.findings,'\n'.join('C1-LONG-%02d 합성 검수 문단 %02d: 장치 7대 관련 가상 내용입니다. 본문과 서식, 문단 순서가 모두 보존되어야 합니다.'%(i,i) for i in range(1,61)))
        reviewed();approve('C1_LONG')
    def long_saved():
        saved('C1_LONG')
        if any(hashes().get(n)!=v for n,v in memo['protected'].items()):raise AssertionError('Previously saved output changed')
        memo['protected']=hashes();os.environ['AIR_R028_FAULT']='stall';approve('C1_TIMEOUT')
    def timeout_done():
        if app.saved_current or hashes()!=memo['protected'] or hwp_pids():raise AssertionError('Timeout cleanup failed')
        if app.snapshot()!=expected['C1_TIMEOUT'] or not any('제한 시간' in n['message'] for n in notices):raise AssertionError('Timeout lost edits or reason')
        if list((root/'outputs').glob('*.tmp')):raise AssertionError('Timeout left staged output')
        cases['timeout_cleanup']='PASS';os.environ.pop('AIR_R028_FAULT',None);approve('C1_TIMEOUT')
    def timeout_retried():
        saved('C1_TIMEOUT');memo['protected']=hashes();os.environ['AIR_R028_FAULT']='failure';approve('C1_RECOVERY')
    def failure_done():
        if app.saved_current or hashes()!=memo['protected'] or app.snapshot()!=expected['C1_RECOVERY']:raise AssertionError('Failure protection failed')
        cases['failure_protection']='PASS';os.environ.pop('AIR_R028_FAULT',None);approve('C1_RECOVERY')
    def failure_retried():
        saved('C1_RECOVERY')
        record('awaiting_native_open_user_approval',note='User must approve synthetic file access; no automatic approval or performance timing claim')
    def wait_workers():
        current=set(hwp_pids());rows=[json.loads(s) for s in (root/'evidence/worker-ownership.jsonl').read_text().splitlines()]
        known={r['pid'] for r in rows if r['owned']}
        if current-known:raise RuntimeError('Unrelated Hancom process appeared: no Open or termination')
        if current:
            memo.setdefault('quit_wait',time.monotonic())
            if time.monotonic()-memo['quit_wait']>15:raise RuntimeError('Owned worker has not quit; do not kill/retry')
            return False
    def open_outputs():
        import pythoncom
        pythoncom.CoInitialize();hwp=None
        try:
            hwp=owned_hwp(root/'evidence/open-ownership.jsonl');hwp.XHwpWindows.Item(0).Visible=True
            for name in ('C1_A','C1_B','C1_RENAMED','C1_LONG','C1_TIMEOUT','C1_RECOVERY'):
                path=root/'outputs'/(name+'.hwp');before=digest(path);record('open_start',name=name)
                if not hwp.Open(str(path),'HWP','readonly:true'):raise AssertionError('Real frozen Open returned false')
                xml=hwp.GetTextFile('HWPML2X','');verify_xml(xml,expected[name])
                if name=='C1_LONG' and not all('C1-LONG-%02d'%i in xml for i in range(1,61)):raise AssertionError('Missing long marker')
                if digest(path)!=before:raise AssertionError('Open changed existing file')
                reopened.append({'name':name,'pages':int(hwp.PageCount),'sha256':before,'status':'PASS'})
                record('open_pass',**reopened[-1]);hwp.Clear(1)
        finally:
            if hwp is not None:hwp.Clear(1);hwp.Quit()
            pythoncom.CoUninitialize()
    bundled={name:Path(module.__file__).resolve().is_relative_to(Path(sys._MEIPASS).resolve()) for name,module in (('ui',ui),('exporter',exporter),('review',review))}
    if not all(bundled.values()):raise RuntimeError('Diagnostic loaded a module outside the EXE bundle')
    result={'version':VERSION,'frozen':True,'bundled_modules':bundled,'exe_sha256':digest(sys.executable),'cases':cases,'reopened':reopened,'AI_calls':0,'credentials_read':0,'security_approval':'left to user when prompted, never automated','test_dialog_replies':'mocked; actual App buttons and worker/COM used'}
    finished=False
    def finish(ok,error=None):
        nonlocal finished
        if finished:return
        finished=True
        result.update(result='PASS' if ok else 'FAIL',error=error,outputs=hashes(),export_entries=len(exports))
        with response.open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
        record('finished',result=result['result'])
        stack.close()
        for timer in tk.tk.call('after','info'):tk.after_cancel(timer)
        tk.destroy()
    tk.report_callback_exception=lambda exc,value,tb:finish(False,str(value))
    steps=[lambda:app.load_pdf(str(root/'inputs/plan_A.pdf')),a_ready,a_saved,b_changed,b_saved,duplicate,renamed,long_saved,timeout_done,timeout_retried,failure_done,failure_retried,wait_workers,open_outputs]
    index=0
    def drive():
        nonlocal index
        if app.busy:tk.after(100,drive);return
        try:
            if index==len(steps):finish(True);return
            if steps[index]() is not False:index+=1
            tk.after(100,drive)
        except Exception as e:finish(False,type(e).__name__+': '+str(e))
    tk.deiconify();tk.after(300,drive);tk.mainloop()
    if result.get('result')!='PASS':raise SystemExit(1)
