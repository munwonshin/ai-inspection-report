"""Real Tk workflow routing; API, folder dialog and export are mocked."""
from pathlib import Path
import sys,time,json
from unittest.mock import patch
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base.parent));sys.path.insert(0,str(base.parent/'tests'))
import tkinter as tk
from inspection.ui import App
from test_core import fixture
root=tk.Tk();root.attributes('-alpha',0)
app=App(root,restore_api=False)
app.connected=True;app.pdf_path='synthetic.pdf';app.plan=app.api_plan='[가상] 사업계획'
app.minutes.insert('1.0','[가상] 시연을 확인함. 시험은 예정임.')
for k,v in fixture().general:app.general[k].set(v)
results=[];requests=[]
def settle():
    end=time.monotonic()+15
    while app.busy and time.monotonic()<end:root.update();time.sleep(.02)
    for _ in range(8):root.update();time.sleep(.015)
    assert not app.busy
def generate(key,plan,minutes,current,instruction,**kw):
    requests.append({'current':current,'instruction':instruction,'revision':kw['revision']})
    return {'findings':'• 가상 시연을 확인함.','actions':'• 가상 시험은 예정임.','checks':'','general':{}},{}
with patch('inspection.ui.vault.read',return_value='SYNTHETIC_KEY'),patch('inspection.ui.api.generate',side_effect=generate),patch('inspection.ui.exporter.save') as save:
    assert app.chat_button.cget('text')=='초안 작성'
    app.chat_button.invoke();settle()
    assert len(requests)==1 and not requests[0]['revision']
    save.assert_not_called();results.append('single_composer_blank_starts_draft_without_save')
    assert app.chat_button.cget('text')=='다시 작성'
    with patch('inspection.ui.messagebox.askyesno',return_value=False):app.chat_button.invoke()
    assert len(requests)==1;results.append('blank_composer_regeneration_requires_confirmation')
    app.toggle_editor();app.findings.insert('end','\n직접 편집한 가상 문장.');root.update()
    app.chat.set('직접 편집한 문장을 유지해 주세요.')
    assert app.chat_button.cget('text')=='수정 반영 ↑'
    app.chat_button.invoke();settle()
    assert requests[-1]['revision'] and '직접 편집한 가상 문장.' in requests[-1]['current']['findings']
    assert app.chat.get()=='';save.assert_not_called()
    results.append('same_composer_revises_latest_direct_edit_without_save')
    before=app.snapshot()
    with patch.object(app,'choose_folder'):app.approve()
    save.assert_not_called();assert app.snapshot()==before
    results.append('approval_folder_cancel_keeps_input_and_does_not_export')
    save.return_value={'path':r'C:\synthetic\가상.hwp','pages':1}
    with patch.object(app,'choose_folder',side_effect=lambda:app.folder.set(r'C:\synthetic')):app.approve();settle()
    assert save.call_count==1 and save.call_args.kwargs['approved']
    assert save.call_args.args[0]==before
    results.append('approval_picks_missing_folder_and_exports_latest_snapshot_once')
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
(base/'workflow_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKFLOW_MOCK_CHECKS_OK',json.dumps(results),flush=True)
