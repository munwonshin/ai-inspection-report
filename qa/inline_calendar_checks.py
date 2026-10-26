"""Embedded placement and one-click dates; no API/vault/HWP calls."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
from inspection.report_format import visit_date

def pump(root):
    end=time.monotonic()+.12
    while time.monotonic()<end:root.update();time.sleep(.01)

rows=[]
for scaling in [None,2.0]:
    root=tk.Tk()
    if scaling:root.tk.call('tk','scaling',scaling)
    app=App(root,restore_api=False)
    errors=[];root.report_callback_exception=lambda *args:errors.append(str(args))
    for width,height in [(1320,880),(1060,720)]:
        root.geometry(f'{width}x{height}');pump(root)
        if not app.general_expanded:app.toggle_general();pump(root)
        picker=app.date_pickers[0]
        app.reveal_general(picker.entry);pump(root)
        before=set(root.winfo_children())
        picker.entry.event_generate('<ButtonRelease-1>',x=4,y=4);pump(root)
        panel=picker.window
        assert panel is not None and not isinstance(panel,tk.Toplevel)
        assert panel.winfo_toplevel()==root
        assert set(root.winfo_children())==before,'New top-level window created'
        anchor=app.calendar_anchor;host=app.calendar_host
        assert panel.winfo_y()+panel.winfo_height()<=anchor.winfo_y(), 'Not above composer'
        assert panel.winfo_x()>=0 and panel.winfo_y()>=0
        assert panel.winfo_x()+panel.winfo_width()<=host.winfo_width()
        picker.year=2026;picker.month=3;picker.render();picker.position();pump(root)
        assert panel.winfo_y()+panel.winfo_height()<=anchor.winfo_y(), 'Six-week month overlaps composer'
        picker.year=2024;picker.month=2;picker.render();picker.position();pump(root)
        # Native button press/release, exactly one date click with no OK step.
        button=picker.day_buttons[29]
        button.event_generate('<Enter>');button.event_generate('<Button-1>',x=5,y=5)
        button.event_generate('<ButtonRelease-1>',x=5,y=5);pump(root)
        assert app.general['visit_date'].get()=='2024년 2월 29일' and picker.window is None
        assert not errors,errors
        rows.append({'geometry':[width,height],'scaling':float(root.tk.call('tk','scaling')),'embedded':True,'above_composer':True,'one_click':True})
    for timer in root.tk.call('after','info'):root.after_cancel(timer)
    root.destroy()
print('EMBEDDED_CALENDAR_CHECKS_OK '+json.dumps(rows),flush=True)

