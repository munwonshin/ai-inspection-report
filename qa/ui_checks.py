"""Actual Tk widgets and event loop; API/HWP calls mocked and labelled as such."""
from pathlib import Path
import sys,time
from unittest.mock import patch
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base.parent));sys.path.insert(0,str(base.parent/'tests'))
import tkinter as tk
from inspection.ui import App
from inspection import api
from test_core import fixture
root=tk.Tk();app=App(root,restore_api=False)
app.plan='[가상 사업계획서] 시험 설비의 상태 확인을 목표로 한다.'
app.api_plan=app.plan;app.pdf_path='synthetic-test.pdf'
app.minutes.insert('1.0','[가상 회의록] 가상 센서 시연을 확인했으며 성능시험은 예정임.')
app.connected=True
app.title.set('가상 UI 검증')
app.name.set('가상_UI_검증')
app.folder.set(r'D:\ai-inspection-report\verification')
for k,v in fixture().general:app.general[k].set(v)
app.findings.insert('1.0','[가상 자료] 직접 편집한 문장 & <보존>')
root.update()
def settle():
    until=time.monotonic()+20
    while app.busy and time.monotonic()<until:root.update();time.sleep(.03)
    root.update();assert not app.busy
before=app.snapshot()
calls=[]
def mocked_ai(key,plan,minutes,current,instruction,**kwargs):
    assert current['findings']==before.findings
    assert '가상' in plan and '예정' in minutes
    calls.append(current)
    return {'findings':current['findings']+'\n채팅으로 문체만 수정함.',
        'actions':'회의록에 기재된 조치요청 없음.','checks':'가상 확인 사항','general':{}},{'total_tokens':0}
with patch('inspection.ui.vault.read',return_value='TEST_KEY_ONLY'),patch('inspection.ui.api.generate',side_effect=mocked_ai):
    app.chat.set('직접 편집 내용을 유지하고 문체만 수정')
    app.revise();settle()
assert len(calls)==1 and before.findings in app.snapshot().findings
print('TK_EDIT_CHAT_CONTEXT_MOCK_API_OK',flush=True)
kept=app.snapshot()
with patch('inspection.ui.vault.read',return_value='TEST_KEY_ONLY'),patch('inspection.ui.api.generate',side_effect=api.ApiFailure('가상 API 오류')),patch('inspection.ui.messagebox.showerror'):
    app.chat.set('가상 오류 시험');app.revise();settle()
assert app.snapshot()==kept
print('TK_API_ERROR_PRESERVES_INPUT_MOCK_OK',flush=True)
with patch('inspection.ui.exporter.save',side_effect=RuntimeError('가상 NAS 연결 오류')),patch('inspection.ui.messagebox.showerror'):
    app.approve();settle()
assert app.snapshot()==kept
print('TK_SAVE_ERROR_PRESERVES_INPUT_MOCK_NAS_OK',flush=True)
app.folder.set(r'C:\Temp')
with patch('inspection.ui.exporter.save',return_value={'path':r'C:\Temp\가상_UI_검증.hwp','pages':1}) as save:
    app.approve();settle()
    assert save.call_args.kwargs['approved'] is True
    assert save.call_args.args[0]==kept
assert app.saved_current
app.findings.insert('end','\n추가 직접 편집');root.update()
assert not app.saved_current and app.open_file.instate(['disabled'])
print('TK_RETRY_APPROVED_SNAPSHOT_AND_DIRTY_STATE_MOCK_OK',flush=True)
root.destroy()
