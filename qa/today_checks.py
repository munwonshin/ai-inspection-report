"""Current local date highlighting and midnight/month/year transitions."""
import sys,time
from pathlib import Path
from datetime import date as real_date
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
from inspection.ui import App
from inspection.date_picker import DatePicker

class Clock(real_date):
    current=real_date(2026,10,23)
    @classmethod
    def today(cls):return cls.current

root=tk.Tk();app=App(root,restore_api=False);app.toggle_general();root.update()
picker=app.date_pickers[0]
errors=[];root.report_callback_exception=lambda *args:errors.append(str(args))
with patch('inspection.date_picker.date',Clock):
    app.general['visit_date'].set('2026-10-15');picker.open();root.update()
    def highlighted():return [d for d,b in picker.day_buttons.items() if b.cget('style')=='Today.Calendar.TButton']
    assert highlighted()==[23]
    style=ttk.Style(root)
    assert style.lookup('Today.Calendar.TButton','background')=='#2563EB'
    assert style.lookup('Today.Calendar.TButton','foreground')=='#FFFFFF'
    # Use the real event-loop timer; no restart, no click, and preserve input.
    Clock.current=real_date(2026,10,24)
    end=time.monotonic()+2.5
    while time.monotonic()<end and highlighted()!=[24]:root.update();time.sleep(.02)
    assert highlighted()==[24] and app.general['visit_date'].get()=='2026-10-15'
    picker.move(1);assert highlighted()==[]
    picker.move(-1);assert highlighted()==[24]
    Clock.current=real_date(2026,10,31);picker._refresh_today();assert highlighted()==[31]
    Clock.current=real_date(2026,11,1);picker._refresh_today();assert highlighted()==[]
    picker.move(1);assert highlighted()==[1]
    picker.year=2026;picker.month=12;picker.render()
    Clock.current=real_date(2026,12,31);picker._refresh_today();assert highlighted()==[31]
    Clock.current=real_date(2027,1,1);picker._refresh_today();assert highlighted()==[]
    picker.move(1);assert highlighted()==[1]
    picker.close();assert picker._today_timer is None
    picker.open();assert highlighted()==[] # Selected old month is still October.
    picker.today();assert app.general['visit_date'].get()=='2027-01-01' and picker._today_timer is None
    picker.open();assert highlighted()==[1]
    app.lock(True);assert picker.window is None and picker._today_timer is None
    app.lock(False)
# Destroy the existing approval-style parent while its inline calendar is open.
parent=tk.Toplevel(root);host=ttk.Frame(parent);host.pack()
variable=tk.StringVar();entry=ttk.Entry(host,textvariable=variable);entry.grid(row=0,column=0)
embedded=DatePicker(entry,variable);embedded.open();root.update()
assert embedded._today_timer is not None
parent.destroy();root.update()
assert embedded._today_timer is None
# Actual PC date also highlights without the virtual-clock override.
app.general['visit_date'].set('');picker.open();root.update()
current=real_date.today()
assert picker.day_buttons[current.day].cget('style')=='Today.Calendar.TButton'
picker.close()
assert not errors,errors
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
print('TODAY_BLUE_REAL_TIMER_MONTH_YEAR_PRESERVATION_OK',flush=True)
