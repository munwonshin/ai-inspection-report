"""Malformed API evidence must fail before edited widgets change; network mocked."""
import sys,json,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
root=tk.Tk();root.attributes('-alpha',0);errors=[];callbacks=[]
root.report_callback_exception=lambda *a:callbacks.append(str(a[1]))
app=App(root,restore_api=False);app.connected=True;app.pdf_path='synthetic.pdf';app.plan=app.api_plan='가상 근거'
app.minutes.insert('1.0','가상 근거');app.findings.insert('1.0','직접 편집한 가상 원문.');app.actions.insert('1.0','가상 후속 원문.')
root.update();before=app.snapshot()
def settle():
    end=time.monotonic()+15
    while app.busy and time.monotonic()<end:root.update();time.sleep(.02)
    for _ in range(15):root.update();time.sleep(.01)
    assert not app.busy and not callbacks,callbacks
bad={'findings':'교체되면 안 되는 가상 본문','actions':'가상','general':{'project':{'value':7,'evidence':'가상 근거','source':'minutes'}}}
with patch('inspection.ui.vault.read',return_value='FAKE'),patch('inspection.api.request',return_value=(json.dumps(bad),{})),patch('inspection.ui.messagebox.showerror',side_effect=lambda *a,**kw:errors.append(a)),patch('inspection.ui.exporter.save') as export:
    app.chat.set('가상 수정 요청');app.submit_chat();settle()
    assert errors and app.snapshot()==before and app.chat.get()=='가상 수정 요청' and app.activity.get()==''
    good={'findings':before.findings+'\n정상 가상 수정함.','actions':before.actions,'decision':'applied','notice':''}
    with patch('inspection.api.request',return_value=(json.dumps(good),{})):app.submit_chat();settle()
    assert '정상 가상 수정함.' in app.get(app.findings);export.assert_not_called()
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
print('MALFORMED_RESPONSE_UI_PRESERVATION_AND_RETRY_OK',flush=True)
