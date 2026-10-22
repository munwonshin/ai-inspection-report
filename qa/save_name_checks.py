"""Native Tk approval boundary tests; HWP saving is mocked, no API request."""
from pathlib import Path
import sys,time
from unittest.mock import patch
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base.parent));sys.path.insert(0,str(base.parent/'tests'))
import tkinter as tk
from inspection.ui import App
from inspection.core import filename,destination
from test_core import fixture
root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False)
report=fixture()
for k,v in report.general:app.general[k].set(v)
app.findings.insert('1.0',report.findings);app.folder.set(r'D:\가상 저장 시험')
calls=[];errors=[]
def save(snapshot,folder,name,*,approved=False):
    assert approved is True
    calls.append((snapshot,filename(name)))
    return {'path':str(destination(folder,name)),'pages':1}
def settle():
    until=time.monotonic()+10
    while app.busy and time.monotonic()<until:root.update();time.sleep(.02)
    for _ in range(10):root.update();time.sleep(.02)
    assert not app.busy
with patch('inspection.ui.exporter.save',side_effect=save) as export,patch('inspection.ui.messagebox.showerror',side_effect=lambda title,text,**kw:errors.append(text)):
    for title in [' 가상_결과. ', '\u3000가상_결과\u00a0.\u3000', ' 가상_결과.HWP . ']:
        app.title.set(title);root.update()
        assert app.filename_hint.get()=='' and not app.filename_hint_label.winfo_ismapped()
        before=app.snapshot();app.approve();settle()
        assert calls[-1][0]==before and app.title.get()==title
        assert calls[-1][1]=='가상_결과.hwp' and not errors
    count=len(calls)
    for title in [' ... ','.hwp','CON','가상:결과']:
        app.title.set(title);root.update();app.approve();settle()
        assert len(calls)==count and app.title.get()==title
        assert app.filename_hint.get() and app.filename_hint_label.winfo_ismapped()
    assert len(errors)==4
    app.title.set(' 가상_결과. ');before=app.snapshot()
    with patch('inspection.ui.exporter.save',side_effect=RuntimeError('같은 이름의 파일이 있습니다. 덮어쓰지 않았습니다.')):
        app.approve();settle()
    assert app.snapshot()==before and not app.saved_current
    assert '같은 이름' in errors[-1]
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
print('SAVE_NAME_WIDGET_CHECKS_OK: 3 normalized approvals, 4 blocked names, collision retention; no actual HWP/API',flush=True)
