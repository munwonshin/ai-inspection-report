"""Real Tk: document title context is editable and independent of file name."""
from pathlib import Path
import sys,json,tempfile,time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
from inspection.report_format import DIVISIONS
root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False);root.update()
try:
 app.title.set('[가상] 별도_저장파일명');app.findings.insert('1.0','가상 현장 확인함.')
 with patch('inspection.ui.exporter.save') as save,patch('inspection.ui.messagebox.showinfo') as notice:
  app.approve();root.update();save.assert_not_called();notice.assert_called_once()
  assert app.general_expanded and all(k in app.document_context_entries for k in ('program_year','division'))
 for division in DIVISIONS:
  app.document_context_vars['program_year'].set('2026');app.document_context_vars['division'].set(division)
  assert app.snapshot().document_title==f'2026년 AI바우처 현장점검 결과 ({division})'
  assert app.title.get()=='[가상] 별도_저장파일명'
 app.document_context_vars['program_year'].set('2025')
 assert app.snapshot().document_title.startswith('2025년')
 app.saved_current=True;app.last_saved='synthetic-previous.hwp'
 app.open_file.configure(state='normal');app.open_folder.configure(state='normal')
 app.document_context_vars['program_year'].set('2024')
 assert not app.saved_current and app.open_file.instate(['disabled']) and app.open_folder.instate(['disabled'])
 app.clear_plan_general();assert not app.report_context
 assert all(not var.get() for var in app.document_context_vars.values())
 assert app.title.get()=='[가상] 별도_저장파일명'
 app.connected=True;app.pdf_path='synthetic.pdf';app.original_pdf_bytes=b'%PDF-synthetic';app.pdf_page_count=1
 with patch('inspection.ui.vault.read',return_value='synthetic'),patch('inspection.ui.metadata.extract',return_value=({'program_year':'2025','division':'반도체분과'},{})):
  app.recognize_general();end=time.monotonic()+15
  while app.busy and time.monotonic()<end:root.update();time.sleep(.02)
  assert not app.busy
 assert app.document_context_vars['program_year'].get()=='2025'
 assert app.document_context_vars['division'].get()=='반도체분과'
 assert app.snapshot().document_title=='2025년 AI바우처 현장점검 결과 (반도체분과)'
 assert app.title.get()=='[가상] 별도_저장파일명'
 result={'file_and_document_title_separate':True,'four_divisions':True,'source_year_not_system_date':True,'missing_context_blocks_export':True,'editable_general_context':True,'document_replacement_clears_context':True,'recognized_pdf_context_reaches_document_title':True,'context_edit_invalidates_previous_save':True}
 Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
finally:root.destroy()
