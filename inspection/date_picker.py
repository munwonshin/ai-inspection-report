"""A small native Tk calendar; the entry remains usable with a keyboard."""
import calendar
from datetime import date
import tkinter as tk
from tkinter import ttk

class DatePicker:
    def __init__(self, entry, variable):
        self.entry, self.variable, self.window = entry, variable, None
        entry.bind('<ButtonRelease-1>', self.open, add='+')
        entry.bind('<Alt-Down>', self.open, add='+')

    def close(self, event=None):
        if self.window is not None:
            window, self.window = self.window, None
            if window.winfo_exists():
                window.destroy()

    def open(self, event=None):
        if str(self.entry.cget('state')) == 'disabled':
            return
        if self.window is not None and self.window.winfo_exists():
            return 'break' if event and event.type == tk.EventType.KeyPress else None
        try:
            selected = date.fromisoformat(self.variable.get().strip())
        except ValueError:
            selected = date.today()
        self.year, self.month, self.selected = selected.year, selected.month, selected
        self.window = tk.Toplevel(self.entry)
        self.window.title('방문일자 선택')
        self.window.resizable(False, False)
        self.window.transient(self.entry.winfo_toplevel())
        self.window.bind('<Escape>', self.close)
        self.window.bind('<FocusOut>', self._focus_out)
        self.body = ttk.Frame(self.window, padding=12)
        self.body.pack(fill='both', expand=True)
        self.render()
        self.window.update_idletasks()
        x = min(self.entry.winfo_rootx(), self.window.winfo_screenwidth()-self.window.winfo_reqwidth())
        y = self.entry.winfo_rooty()+self.entry.winfo_height()+3
        if y+self.window.winfo_reqheight() > self.window.winfo_screenheight()-40:
            y = self.entry.winfo_rooty()-self.window.winfo_reqheight()-3
        self.window.geometry(f'+{max(0,x)}+{max(0,y)}')
        self.day_buttons.get(selected.day, self.today_button).focus_set()
        return 'break' if event and event.type == tk.EventType.KeyPress else None

    def _focus_out(self, event):
        if self.window is not None:
            self.window.after_idle(self._check_focus)

    def _check_focus(self):
        if self.window is not None and self.window.winfo_exists():
            focus = self.window.focus_get()
            if focus is None or focus.winfo_toplevel() != self.window:
                self.close()

    def move(self, delta):
        index = self.year*12+self.month-1+delta
        year, month = divmod(index, 12)
        if 1 <= year <= 9999:
            self.year, self.month = year, month+1
            self.render()
            self.day_buttons.get(1, self.today_button).focus_set()

    def choose(self, day):
        self.variable.set(date(self.year,self.month,day).isoformat())
        self.close()
        self.entry.focus_set()

    def today(self):
        self.variable.set(date.today().isoformat())
        self.close()
        self.entry.focus_set()

    def render(self):
        for child in self.body.winfo_children():
            child.destroy()
        ttk.Button(self.body,text='‹',width=3,command=lambda:self.move(-1)).grid(row=0,column=0)
        ttk.Label(self.body,text=f'{self.year}년 {self.month}월',anchor='center').grid(row=0,column=1,columnspan=5,sticky='ew')
        ttk.Button(self.body,text='›',width=3,command=lambda:self.move(1)).grid(row=0,column=6)
        for column, label in enumerate('월화수목금토일'):
            ttk.Label(self.body,text=label,anchor='center').grid(row=1,column=column,pady=8)
        self.day_buttons = {}
        for row, week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(self.year,self.month),2):
            for column, day in enumerate(week):
                if day:
                    b=ttk.Button(self.body,text=str(day),width=3,command=lambda d=day:self.choose(d))
                    b.grid(row=row,column=column,padx=1,pady=1)
                    self.day_buttons[day]=b
        self.today_button=ttk.Button(self.body,text='오늘',command=self.today)
        self.today_button.grid(row=8,column=0,columnspan=3,sticky='ew',pady=(8,0))
        ttk.Button(self.body,text='닫기',command=self.close).grid(row=8,column=4,columnspan=3,sticky='ew',pady=(8,0))
