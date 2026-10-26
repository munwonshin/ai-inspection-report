"""Synthetic attachment behavior and editable-title preservation."""
import sys,time,tempfile,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
from inspection.ui import App
from inspection import preferences

def settle(root,app):
    end=time.monotonic()+8
    while time.monotonic()<end:
        root.update();time.sleep(.01)
        if not app.busy:break
    assert not app.busy

with tempfile.TemporaryDirectory(prefix='division-') as folder:
    pref=Path(folder)/'settings.json';pref.write_text(json.dumps({'version':1,'pinned':{'visit_org':'가상 과거 방문기관','inspector_org':'가상 소속','inspector':'가상 점검자'}}),encoding='utf-8')
    root=tk.Tk();root.withdraw();app=App(root,restore_api=False,preferences_path=pref);app.connected=True
    assert 'visit_org' not in app.pinned and app.general['visit_org'].get()==''
    assert app.general['inspector_org'].get()=='가상 소속' and app.general['inspector'].get()=='가상 점검자'
    pins=[w for w in app.general_body.winfo_children() if isinstance(w,ttk.Checkbutton)]
    assert len(pins)==2
    doc=SimpleNamespace(local_text='가상',api_text='가상',visual_pdf=None,original_bytes=b'%PDF-SYNTHETIC',page_count=1)
    first={'project':'가상 과제','program_year':'2026','division':'소상공인분과'}
    with patch('inspection.ui.prepare_pdf',return_value=doc),patch('inspection.ui.vault.read',return_value='synthetic-key'),patch('inspection.ui.metadata.extract',return_value=(first,{})) as extract,patch('inspection.ui.exporter.save') as save:
        app.load_pdf('synthetic-a.pdf');settle(root,app)
        assert app.title.get()=='2026년 AI바우처 현장점검 결과 (소상공인분과)'
        assert all(k in extract.call_args.args[3] for k in ('program_year','division'))
        # Replacing PDF changes an untouched automatic title.
        with patch('inspection.ui.metadata.extract',return_value=({'program_year':'2025','division':'일반분과'},{})):
            app.load_pdf('synthetic-b.pdf');settle(root,app)
        assert app.title.get()=='2025년 AI바우처 현장점검 결과 (일반분과)'
        # A user title is never replaced by another PDF or explicit retry.
        app.title.set('가상 사용자 검수 제목')
        app.load_pdf('synthetic-c.pdf');settle(root,app)
        assert app.title.get()=='가상 사용자 검수 제목'
        app.remove_pdf();assert app.title.get()=='가상 사용자 검수 제목' and app.report_context=={}
        app.title.set('현장점검 결과서')
        with patch('inspection.ui.metadata.extract',return_value=({'program_year':'2026'},{})):
            app.load_pdf('synthetic-missing.pdf');settle(root,app)
        assert app.title.get()=='2026년 AI바우처 현장점검 결과' and '분과' in app.status.get()
        with patch('inspection.ui.metadata.extract',return_value=({'division':'소상공인분과'},{})):
            app.recognize_general(force=True);settle(root,app)
        assert app.title.get().endswith('(소상공인분과)')
        app.general['visit_date'].set('2026-10-16')
        assert dict(app.snapshot().general)['visit_date']=='2026년 10월 16일'
        save.assert_not_called()
    for timer in root.tk.call('after','info'):root.after_cancel(timer)
    root.destroy()
print('DIVISION_TITLE_PDF_REPLACEMENT_MANUAL_OVERRIDE_DATE_AND_TWO_PINS_OK',flush=True)
