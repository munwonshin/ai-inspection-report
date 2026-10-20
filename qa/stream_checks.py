"""Native Tk controller check with a deliberately delayed synthetic stream."""
import sys,time,json,threading
from pathlib import Path
from unittest.mock import patch
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base.parent))
import tkinter as tk
from inspection.ui import App
from inspection import api

root=tk.Tk();root.attributes('-alpha',0);app=App(root)
app.connected=True;app.pdf_path='synthetic.pdf';app.plan=app.api_plan='가상 사업계획: 설치 예정.'
app.minutes.insert('1.0','가상 회의록: 시연 화면 확인. 시험은 예정.')
app.title.set('가상_검수결과 (초안)');app.folder.set(str(base))
assert app.name is app.title
assert len([w for w in app.entries if str(w.cget('textvariable'))==str(app.title)])==1
body={'findings':'가상 기업은 설치 예정이라고 설명함.\n시연 화면을 확인함.','actions':'회의록에 기재된 조치요청 없음.','checks':'시험일 확인 필요.','general':{}}
seen=[]
def observe():
    if app.busy:
        seen.append(app.conversation.get('1.0','end'))
        assert app.approve_button.instate(['disabled'])
        root.after(75,observe)

def pump_until_idle():
    until=time.monotonic()+10
    while app.busy and time.monotonic()<until:
        root.update();seen.append(app.conversation.get('1.0','end'));time.sleep(.02)
    for _ in range(15):root.update();time.sleep(.02)
    assert not app.busy

def generate(*args,on_delta=None,**kwargs):
    text=json.dumps(body,ensure_ascii=False)
    for i in range(0,len(text),4):
        on_delta(text[i:i+4]);time.sleep(.055)
    return body,{'input_tokens':10,'output_tokens':20}

with patch('inspection.ui.vault.read',return_value='fake'),patch('inspection.ui.api.generate',side_effect=generate),patch('inspection.ui.exporter.save') as save:
    app.draft()
    assert app.busy and app.approve_button.instate(['disabled'])
    root.after(30,observe)
    assert '초 경과' in app.conversation.get('1.0','end')
    pump_until_idle()
    assert any('1초 경과' in x for x in seen)
    assert any('가상 기업은' in x and '시험일 확인 필요.' not in x for x in seen)
    assert all('"findings"' not in x and '"general"' not in x for x in seen)
    assert app.snapshot().findings==body['findings'];save.assert_not_called()
    before=app.snapshot()
    def fail(*args,on_delta=None,**kwargs):
        on_delta('{"findings":"가상 중단될 내용');time.sleep(.5)
        raise api.ApiFailure('가상 중단 시험')
    with patch('inspection.ui.api.generate',side_effect=fail),patch('inspection.ui.messagebox.showerror'):
        app.chat.set('가상 수정');app.send_chat();root.after(30,observe);pump_until_idle()
    assert app.snapshot()==before and app.pending_request is None
    assert app.messages[-1]['status']=='failed'
    assert '중단될 내용' not in app.conversation.get('1.0','end')
    assert app.ai_started is None;save.assert_not_called()
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
print('STREAM_WIDGET_CHECKS_OK: elapsed, incremental, title alias, approval lock, failure retention, no export',flush=True)
