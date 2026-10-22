from pathlib import Path
import sys,time,json,hashlib
from unittest.mock import patch
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base.parent));sys.path.insert(0,str(base.parent/'tests'))
import tkinter as tk
from inspection.ui import App
from inspection import api
from test_core import fixture
root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False)
app.plan=app.api_plan='[가상 계획] 설치는 목표이며 실적이 아님.';app.pdf_path='synthetic.pdf';app.connected=True
app.minutes.insert('1.0','[가상 회의록] 시연 화면을 확인했으며 시험은 예정임.')
app.name.set('가상_채팅검증');app.folder.set(r'D:\ai-inspection-report\verification')
for k,v in fixture().general:app.general[k].set(v)
results=[];requests=[]
def settle():
    until=time.monotonic()+15
    while app.busy and time.monotonic()<until:root.update();time.sleep(.02)
    for _ in range(12):root.update();time.sleep(.015)
    assert not app.busy
def generate(key,plan,minutes,current,instruction,**kw):
    assert '가상 계획' in plan and '가상 회의록' in minutes
    requests.append((current,instruction,kw))
    return {'findings':'[가상 초안] 기업 설명과 직접 확인을 구분함.','actions':'안내: 가상 로그 보관을 안내함.','checks':'가상 시험일 미정.','general':{}},{'input_tokens':100,'output_tokens':50,'estimated_usd':.00005}
with patch('inspection.ui.vault.read',return_value='SYNTHETIC_TEST_KEY'),patch('inspection.ui.api.generate',side_effect=generate),patch('inspection.ui.exporter.save') as save:
    app.chat.set('가상 자료로 초안을 작성해 주세요.');app.send_chat();settle()
    assert len(requests)==1 and requests[0][2]['revision'] is False
    assert app.chat.get()=='' and len(app.messages)==2
    assert '최신 초안 · 1차' in app.conversation.get('1.0','end')
    assert app.conversation.cget('state')=='disabled'
    save.assert_not_called();results.append('initial_chat_creates_draft_without_save')
    app.toggle_editor();root.update();assert app.editor_open
    marker='직접 편집한 가상 검수 문장.'
    app.findings.insert('end','\n'+marker);root.update();app.toggle_editor();settle()
    assert marker in app.conversation.get('1.0','end')
    def revise(key,plan,minutes,current,instruction,**kw):
        assert marker in current['findings'] and kw['revision'] is True
        assert 'history' not in kw
        requests.append((current,instruction,kw))
        return {'findings':current['findings']+'\n가상 문체 수정 반영.','actions':current['actions'],'checks':current['checks'],'general':{}},{'input_tokens':110,'output_tokens':55}
    with patch('inspection.ui.api.generate',side_effect=revise):
        app.chat.set('직접 편집을 유지하고 가상 문체를 다듬어 주세요.');app.send_chat();settle()
    transcript=app.conversation.get('1.0','end')
    assert '이전 초안 · 1차' in transcript and '최신 초안 · 2차' in transcript
    assert len(app.messages)==4 and marker in app.snapshot().findings
    save.assert_not_called();results.append('direct_edit_and_revised_latest_draft_preserved')
    before=app.snapshot();before_messages=len(app.messages)
    with patch('inspection.ui.api.generate',side_effect=api.ApiFailure('가상 연결 오류')),patch('inspection.ui.messagebox.showerror'):
        app.chat.set('가상 오류 시험 요청');app.send_chat();settle()
    assert app.snapshot()==before and app.chat.get()=='가상 오류 시험 요청'
    assert app.messages[-1]['status']=='failed' and len(app.messages)==before_messages+1
    assert '이전 초안과 입력 내용은 유지됩니다' in app.conversation.get('1.0','end')
    save.assert_not_called();results.append('failed_chat_preserves_draft_request_and_history')
    with patch('inspection.ui.exporter.save',return_value={'path':r'D:\ai-inspection-report\verification\가상_채팅검증.hwp','pages':1}) as approved:
        app.approve();settle()
        assert approved.call_args.kwargs['approved'] is True
        assert approved.call_args.args[0]==before
        assert '나의 요청' not in approved.call_args.args[0].findings
    results.append('approval_exports_latest_report_only_mock_hwp')
    app.toggle_editor();app.findings.insert('end','\n저장 후 추가 편집');settle()
    assert not app.saved_current and app.open_file.instate(['disabled'])
    results.append('post_save_edit_requires_new_approval')
(base/'chat_checks.json').write_text(json.dumps({'passed':results,'actual_api':False,'actual_hwp':False},indent=2),encoding='utf-8')
print('CHAT_UI_CHECKS_OK '+json.dumps(results),flush=True)
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
