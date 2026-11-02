"""Real Tk reset checks with isolated preferences and fake credentials only."""
from pathlib import Path
import sys,tempfile,json,time,hashlib
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
from inspection import preferences

with tempfile.TemporaryDirectory(prefix='reset-check-') as folder:
 base=Path(folder);config=base/'preferences.json'
 preferences.save(config,{'inspector_org':'가상 고정 기관','inspector':'가상 고정 점검자'})
 original=base/'synthetic.hwp';original.write_bytes(b'synthetic original - untouched')
 saved=base/'approved.hwp';saved.write_bytes(b'synthetic saved result - untouched')
 root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False,preferences_path=config)
 try:
  app.connected=True;app.pdf_path=str(original);app.plan=app.api_plan='가상 자료';app.pdf_bytes=b'visual';app.original_pdf_bytes=b'original';app.pdf_page_count=7
  app.minutes.insert('1.0','가상 회의록');app.findings.insert('1.0','가상 직접 편집 초안');app.actions.insert('1.0','가상 조치')
  app.title.set('가상 저장명');app.folder.set(str(base));app.chat.set('가상 수정 요청')
  for key,value in app.general.items():value.set('가상 '+key)
  app.document_context_vars['program_year'].set('2026');app.document_context_vars['division'].set('일반분과')
  app.auto_general['project']='가상 자동값';app.general_evidence['project']={'page':1,'quote':'가상 인용'};app.general_issues['partner_org']='가상 미확인'
  app.sync_latest_report();assert app.messages and app.draft_history.versions
  app.toggle_general();app.toggle_editor();app.editor_view.select(1)
  app.last_saved=str(saved);app.saved_current=True;app.open_file.configure(state='normal');app.open_folder.configure(state='normal')
  app.pdf_progress.put((7,7));app.stream_queue.put('old delta');app.stream_json='old preview'
  before=(original.read_bytes(),saved.read_bytes());root.update()
  with patch('inspection.ui.vault.read') as read,patch('inspection.ui.vault.save') as key_save,patch('inspection.ui.vault.delete') as delete,patch('inspection.ui.api.generate') as generate,patch('inspection.ui.api.connection') as connect,patch('inspection.ui.exporter.save') as export,patch('inspection.ui.messagebox.askyesno') as confirm:
   app.reset_button.invoke();root.update()
   assert app.connected and not app.busy
   assert not any((app.plan,app.api_plan,app.pdf_path,app.pdf_bytes,app.original_pdf_bytes,app.pdf_page_count))
   assert not app.report_context and not app.auto_general and not app.general_evidence and not app.general_issues
   assert all(not v.get() for v in app.general.values()) and all(not v.get() for v in app.document_context_vars.values())
   assert all(not v.get() for v in app.pinned.values()) and preferences.load(config)=={}
   assert all(not app.get(w) for w in (app.minutes,app.findings,app.actions))
   for text in (app.minutes,app.findings,app.actions):
    try:text.edit_undo()
    except tk.TclError:pass
    assert app.get(text)=='','Undo resurrected reset input'
   assert not app.messages and not app.draft_history.versions
   assert not app.chat.get() and not app.folder.get() and app.title.get()=='현장점검 결과서'
   assert app.last_saved is None and not app.saved_current
   assert app.open_file.instate(['disabled']) and app.open_folder.instate(['disabled'])
   assert not app.general_expanded and not app.editor_open and app.editor_view.index(app.editor_view.select())==0
   assert (original.read_bytes(),saved.read_bytes())==before
   until=time.monotonic()+.6
   while time.monotonic()<until:root.update();time.sleep(.02)
   assert preferences.load(config)=={},'Old preference timer restored cleared pins'
   assert app.reset_workspace() and app.connected
   app.connected=False;assert app.reset_workspace() and not app.connected
   read.assert_not_called();key_save.assert_not_called();delete.assert_not_called();generate.assert_not_called();connect.assert_not_called();export.assert_not_called();confirm.assert_not_called()
  app.minutes.insert('1.0','가상 입력 보존');app.lock(True)
  assert app.reset_button.instate(['disabled']) and app.reset_workspace() is False
  assert app.get(app.minutes)=='가상 입력 보존';app.lock(False)
  with patch('inspection.ui.preferences.save',side_effect=OSError('synthetic failure')),patch('inspection.ui.messagebox.showerror') as error:
   assert app.reset_workspace() is False and app.get(app.minutes)=='가상 입력 보존';error.assert_called_once()
  app.reset_workspace();root.update()
  app.minutes.insert('1.0','새 가상 회의록');app.findings.insert('1.0','새 가상 초안');app.sync_latest_report()
  assert len(app.draft_history.versions)==1 and all('가상 직접 편집 초안' not in str(m) for m in app.messages)
  result={'one_button_reset':True,'api_and_connection_preserved':True,'no_api_or_vault_calls':True,'document_minutes_draft_chat_context_paths_cleared':True,'pins_cleared_persistently':True,'pending_preference_timer_cannot_restore_old_values':True,'undo_history_cleared':True,'original_and_saved_files_preserved':True,'busy_reset_blocked':True,'settings_failure_atomic':True,'new_workflow_after_reset':True}
  Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
 finally:root.destroy()
 # Persisted inspector fields must stay empty on a fresh application instance.
 root2=tk.Tk();root2.attributes('-alpha',0);app2=App(root2,restore_api=False,preferences_path=config)
 assert all(not app2.pinned[k].get() and not app2.general[k].get() for k in preferences.FIELDS)
 root2.destroy();print('RESET_REOPEN_PINS_EMPTY',flush=True)
