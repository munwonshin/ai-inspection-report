"""Quiet main UI and disclosure placement; all network/export/vault calls mocked."""
from pathlib import Path
import sys,time,json
from unittest.mock import patch
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base.parent))
import tkinter as tk
from tkinter import ttk
from inspection.ui import App
root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False)
app.connected=True;app.pdf_path='synthetic.pdf';app.plan=app.api_plan='[가상 계획] 상태 점검.'
app.minutes.insert('1.0','[가상 회의록] 화면을 확인함. 시험은 예정임.')
results=[]
def settle():
    end=time.monotonic()+12
    while app.busy and time.monotonic()<end:root.update();time.sleep(.02)
    for _ in range(10):root.update();time.sleep(.01)
    assert not app.busy
def labels(parent):
    text=[]
    for w in parent.winfo_children():
        if isinstance(w,tk.Toplevel):continue
        if isinstance(w,(ttk.Label,tk.Label)) and w.winfo_ismapped():
            variable=str(w.cget('textvariable'))
            text.append(str(root.getvar(variable)) if variable else str(w.cget('text')))
        text.extend(labels(w))
    return text
def generate(*args,**kwargs):
    return {'findings':'• 가상 화면을 확인함.','actions':'• 가상 시험은 예정임.','checks':'','general':{}},{'input_tokens':123456789,'output_tokens':987654321,'estimated_usd':42.42}
with patch('inspection.ui.vault.read',return_value='SYNTHETIC_KEY'),patch('inspection.ui.api.generate',side_effect=generate),patch('inspection.ui.exporter.save') as export:
    app.draft();settle()
    transcript=app.conversation.get('1.0','end')
    assert '원본 자료에 근거하여' not in transcript and '나의 요청' not in transcript
    assert app.messages[0]['visible'] is False
    assert '가상 화면' in transcript;results.append('automatic_prompt_hidden_report_preserved')
    app.chat.set('문단을 간단히 정리해 주세요.');app.submit_chat();settle()
    transcript=app.conversation.get('1.0','end')
    assert '문단을 간단히 정리해 주세요.' in transcript and '나의 요청' not in transcript
    results.append('typed_request_visible_without_role_label')
    visible='\n'.join(labels(root))+transcript
    for word in ['저장 대상','저장대상','최신 초안','미저장 초안','토큰','추가 과금','파일 생성 없음','123456789','987654321','42.42']:
        assert word not in visible,word
    assert not hasattr(app,'state_badge') and not hasattr(app,'draft_hint')
    assert app.activity.get()=='';export.assert_not_called()
    results.append('main_metadata_usage_and_footer_absent_no_export')
with patch('inspection.ui.vault.read',return_value=None):
    app.settings();root.update()
    dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
    dialog.attributes('-alpha',0)
    setting_text='\n'.join(str(w.cget('text')) for panel in dialog.winfo_children() for w in panel.winfo_children() if isinstance(w,ttk.Label))
    assert all(word in setting_text for word in ['OpenAI','과금','전송','Windows'])
    assert '토큰' not in setting_text
    dialog.destroy();results.append('data_and_cost_disclosure_in_settings_only')
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
(base/'quiet_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('QUIET_MAIN_UI_CHECKS_OK',json.dumps(results),flush=True)
