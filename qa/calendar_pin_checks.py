"""Native Tk tests, synthetic local settings, no real vault/API/report output."""
import sys,time,tempfile,json
from pathlib import Path
from datetime import date
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
from inspection import preferences

def pump(root,seconds=.08):
    end=time.monotonic()+seconds
    while time.monotonic()<end:root.update();time.sleep(.01)

def dispose(root):
    for timer in root.tk.call('after','info'):root.after_cancel(timer)
    root.destroy()

checks=[]
with tempfile.TemporaryDirectory(prefix='calendar-pins-') as folder:
    path=Path(folder)/'profile'/'preferences.json'
    root=tk.Tk();app=App(root,restore_api=False,preferences_path=path);pump(root)
    app.toggle_general();pump(root)
    picker=app.date_pickers[0]
    picker.entry.event_generate('<ButtonRelease-1>',x=5,y=5);pump(root)
    assert picker.window and picker.window.winfo_exists()
    picker.year=2024;picker.month=2;picker.render();assert 29 in picker.day_buttons
    picker.day_buttons[29].invoke();assert app.general['visit_date'].get()=='2024-02-29' and picker.window is None
    checks.append('entry_click_leap_day')
    picker.open();picker.year=2025;picker.month=12;picker.move(1);assert (picker.year,picker.month)==(2026,1)
    picker.move(-1);assert (picker.year,picker.month)==(2025,12)
    picker.close();assert app.general['visit_date'].get()=='2024-02-29'
    picker.open();picker.today();assert app.general['visit_date'].get()==date.today().isoformat()
    checks.append('month_year_navigation_cancel_today')
    picker.open();pump(root);picker.window.event_generate('<Escape>');pump(root)
    assert picker.window is None
    picker.open();pump(root);app.chat_entry.focus_force();pump(root)
    assert picker.window is None
    errors=[];root.report_callback_exception=lambda *args:errors.append(str(args))
    def complete_missing():
        modal=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        frame=modal.winfo_children()[0]
        entry=next(w for w in frame.winfo_children() if isinstance(w,tk.ttk.Entry))
        entry.event_generate('<ButtonRelease-1>',x=5,y=5);root.update_idletasks()
        popup=next(w for w in entry.winfo_children() if isinstance(w,tk.Toplevel))
        body=popup.winfo_children()[0]
        next(w for w in body.winfo_children() if isinstance(w,tk.ttk.Button) and w.cget('text')=='21').invoke()
        next(w for w in frame.winfo_children() if isinstance(w,tk.ttk.Button) and '승인' in w.cget('text')).invoke()
    root.after(200,complete_missing)
    assert app.missing_dialog(['visit_date'])
    assert app.general['visit_date'].get().endswith('-21') and not errors
    checks.append('escape_outside_focus_and_approval_missing_date_calendar')

    values={'visit_org':'가상 방문기관','inspector_org':'가상 점검기관','inspector':'가상 점검자'}
    for k,v in values.items():app.general[k].set(v);app.pinned[k].set(True)
    app.persist_preferences()
    app.general['inspector'].set('가상 수정 점검자');pump(root,.6)
    assert preferences.load(path)['inspector']=='가상 수정 점검자'
    app.general['project'].set('기억하지 않을 가상 과제')
    app.close();root=tk.Tk();app=App(root,restore_api=False,preferences_path=path);pump(root)
    assert app.general['inspector'].get()=='가상 수정 점검자'
    assert all(app.pinned[k].get() for k in values)
    assert app.general['project'].get()=='' and app.general['visit_date'].get()==''
    checks.append('pinned_values_restore_and_edits_persist_only_manual_fields')
    app.pinned['inspector'].set(False);app.persist_preferences()
    assert app.general['inspector'].get()=='가상 수정 점검자'
    app.general['visit_org'].set('가상 새 방문기관');app.persist_preferences()
    dispose(root);root=tk.Tk();app=App(root,restore_api=False,preferences_path=path);pump(root)
    assert app.general['inspector'].get()=='' and not app.pinned['inspector'].get()
    assert app.general['visit_org'].get()=='가상 새 방문기관'
    checks.append('unpin_retains_current_only_and_restart_clears')
    app.general['visit_date'].set('2026-10-23')
    app.general['inspector'].set('가상 승인 점검자');app.pinned['inspector'].set(True)
    # Approval uses the exact current form, not the previous stored value.
    assert dict(app.snapshot().general)['inspector']=='가상 승인 점검자'
    picker=app.date_pickers[0];picker.open();app.lock(True);assert picker.window is None
    app.lock(False)
    app.general['inspector_org'].set('가상 실패 시 보존 기관')
    with patch('inspection.ui.preferences.save',side_effect=PermissionError('synthetic')):
        app.persist_preferences();assert '유지' in app.status.get()
    assert app.general['inspector'].get()=='가상 승인 점검자'
    checks.append('busy_closes_calendar_snapshot_current_and_save_error_retains')
    dispose(root)
    # Corrupted preferences recover without writing at startup.
    path.write_text('{bad',encoding='utf-8');root=tk.Tk();app=App(root,restore_api=False,preferences_path=path);pump(root)
    assert '불러오지 못' in app.status.get() and path.read_text(encoding='utf-8')=='{bad'
    dispose(root)
    checks.append('invalid_settings_safe_startup')
print('CALENDAR_PIN_CHECKS_OK '+json.dumps(checks),flush=True)

