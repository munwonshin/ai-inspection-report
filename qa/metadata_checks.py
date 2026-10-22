"""Synthetic native Tk attachment/metadata tests. API and HWP calls mocked."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys,time,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
from inspection import api
root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False);app.connected=True
app.minutes.insert('1.0','가상 회의록 보존');app.findings.insert('1.0','가상 직접 편집 보존')
app.general['lead_person'].set('직접 입력한 가상 책임자')
doc=SimpleNamespace(local_text='가상 계획',api_text='가상 계획',visual_pdf=None,original_bytes=b'%PDF-SYNTHETIC',page_count=1)
rows=[]
def settle():
    until=time.monotonic()+15
    while time.monotonic()<until:
        root.update();time.sleep(.02)
        if not app.busy:
            root.update()
            if not app.busy:break
    assert not app.busy
with patch('inspection.ui.prepare_pdf',return_value=doc),patch('inspection.ui.vault.read',return_value='fake'),patch('inspection.ui.metadata.extract',return_value=({'project':'가상 과제 A','lead_org':'가상 주관 A','partner_org':'가상 참여 A'},{})) as extract,patch('inspection.ui.api.generate') as draft,patch('inspection.ui.exporter.save') as save:
    app.load_pdf('synthetic-a.pdf');settle()
    assert app.general['project'].get()=='가상 과제 A'
    assert app.general['lead_person'].get()=='직접 입력한 가상 책임자'
    assert 'lead_person' not in extract.call_args.args[3]
    assert extract.call_args.args[1]==doc.original_bytes
    assert all(not app.general[k].get() for k in ['visit_date','visit_org','inspector_org','inspector'])
    assert extract.call_count==1;app.recognize_general();assert extract.call_count==1
    rows.append('attach_without_minutes_or_draft_populates_plan_fields_once')
    app.general['lead_org'].set('수동 수정한 주관 기관')
    with patch('inspection.ui.metadata.extract',return_value=({'project':'가상 과제 B','partner_org':'가상 참여 B'},{})):
        app.load_pdf('synthetic-b.pdf');settle()
    assert app.general['project'].get()=='가상 과제 B' and app.general['partner_org'].get()=='가상 참여 B'
    assert app.general['lead_org'].get()=='수동 수정한 주관 기관'
    rows.append('replace_clears_prior_auto_values_and_preserves_manual_edits')
    app.remove_pdf()
    assert not app.general['project'].get() and not app.general['partner_org'].get()
    assert app.general['lead_org'].get()=='수동 수정한 주관 기관'
    assert app.get(app.minutes)=='가상 회의록 보존' and app.get(app.findings)=='가상 직접 편집 보존'
    rows.append('remove_clears_only_auto_fields_and_preserves_draft_minutes_manual')
    with patch('inspection.ui.metadata.extract',side_effect=api.ApiFailure('가상 연결 오류')):
        app.load_pdf('synthetic-c.pdf');settle()
    assert app.pdf_path=='synthetic-c.pdf' and '인식 실패' in app.status.get() and not app.general_scanned
    assert app.general['lead_org'].get()=='수동 수정한 주관 기관'
    rows.append('metadata_failure_retains_attachment_and_inputs')
    with patch('inspection.ui.metadata.extract',return_value=({'project':'가상 재시도'},{})):
        app.recognize_general(force=True);settle()
    assert app.general['project'].get()=='가상 재시도'
    rows.append('explicit_retry_fills_only_missing')
    app.connected=False;app.load_pdf('synthetic-d.pdf');settle()
    assert not app.general['project'].get() and not app.general_scanned
    app.connected=True;app.recognize_general();settle()
    assert app.general['project'].get()=='가상 과제 A'
    rows.append('attachment_before_connection_can_resume_after_connection')
    app.general_evidence['project']={'page':1,'quote':'과제명: 가상 과제 A'}
    entry=next(w for w in app.entries if str(w.cget('textvariable'))==str(app.general['project']))
    app.reveal_general_evidence('project',entry)
    assert '원본 PDF 1쪽' in app.general_evidence_note.get()
    app.general['project'].set('직접 수정한 과제')
    assert 'project' not in app.general_evidence and '직접 수정됨' in app.general_evidence_note.get()
    app.remove_pdf()
    assert app.original_pdf_bytes is None and app.pdf_page_count==0
    assert app.general['project'].get()=='직접 수정한 과제'
    rows.append('evidence_view_manual_edit_invalidation_and_original_bytes_cleared')
    draft.assert_not_called();save.assert_not_called()
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
print('METADATA_WIDGET_CHECKS_OK '+json.dumps(rows),flush=True)
