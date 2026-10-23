"""An embedded calendar card, with no native popup window."""
import calendar
from datetime import date
import tkinter as tk
from tkinter import ttk

class DatePicker:
    def __init__(self, entry, variable, *, host=None, anchor=None):
        self.entry, self.variable, self.window = entry, variable, None
        self.host, self.anchor = host, anchor
        self._today_timer=None;self._today_seen=None;self._clock_root=entry.winfo_toplevel()
        self._outside_binding=None;self._resize_binding=None;self._escape_binding=None
        entry.bind('<ButtonRelease-1>', self.open, add='+')
        entry.bind('<Alt-Down>', self.open, add='+')

    def close(self, event=None):
        self._cancel_today_timer()
        if self.window is not None:
            window, self.window = self.window, None
            if window.winfo_exists():window.destroy()
        top=self.entry.winfo_toplevel()
        if self._outside_binding:
            top.unbind('<Button-1>',self._outside_binding);self._outside_binding=None
        if self._escape_binding:
            top.unbind('<Escape>',self._escape_binding);self._escape_binding=None
        if self._resize_binding:
            self.container.unbind('<Configure>',self._resize_binding);self._resize_binding=None

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
        self.container=self.host() if callable(self.host) else self.host
        self.target=self.anchor() if callable(self.anchor) else self.anchor
        if self.container is None:self.container=self.entry.master
        self.window = tk.Frame(self.container,bg='#FFFFFF',highlightbackground='#C9DDD9',highlightthickness=1)
        self.window.bind('<Escape>', self.close)
        self.window.bind('<Destroy>',lambda e:self._cancel_today_timer() if e.widget==self.window else None)
        self.body = ttk.Frame(self.window, padding=8)
        self.body.pack(fill='both', expand=True)
        style=ttk.Style(self.window)
        style.configure('Calendar.TButton',font=('맑은 고딕',9),padding=(3,1))
        style.configure('Calendar.TLabel',font=('맑은 고딕',9))
        style.configure('Today.Calendar.TButton',background='#2563EB',foreground='#FFFFFF',focuscolor='#BFDBFE')
        style.map('Today.Calendar.TButton',background=[('pressed','#1E40AF'),('active','#1D4ED8'),('!disabled','#2563EB')],
                  foreground=[('!disabled','#FFFFFF')])
        self.render()
        self.container.update_idletasks()
        if self.target is None:
            # The existing required-fields dialog expands inline below its date entry.
            self.window.grid(row=self.entry.grid_info()['row']+1,column=0,columnspan=2,sticky='ew',pady=6)
        else:
            self.position()
            self._resize_binding=self.container.bind('<Configure>',lambda e:self.position(),add='+')
        self._outside_binding=self.entry.winfo_toplevel().bind('<Button-1>',self._outside,add='+')
        self._escape_binding=self.entry.winfo_toplevel().bind('<Escape>',self.close,add='+')
        self.day_buttons.get(selected.day, self.today_button).focus_set()
        self._refresh_today()
        return 'break' if event and event.type == tk.EventType.KeyPress else None

    def _cancel_today_timer(self):
        if self._today_timer is not None:
            try:self._clock_root.after_cancel(self._today_timer)
            except tk.TclError:pass
            self._today_timer=None

    def _refresh_today(self):
        self._cancel_today_timer()
        if self.window is None or not self.window.winfo_exists():return
        current=date.today()
        if current!=self._today_seen:self._mark_today(current)
        self._today_timer=self._clock_root.after(1000,self._refresh_today)

    def _mark_today(self,current):
        self._today_seen=current
        for day,button in self.day_buttons.items():
            is_today=(self.year,self.month,day)==(current.year,current.month,current.day)
            button.configure(style='Today.Calendar.TButton' if is_today else 'Calendar.TButton')

    def position(self):
        if self.window is None or not self.window.winfo_exists():return
        self.window.update_idletasks()
        available=max(1,self.target.winfo_y()-6)
        style=ttk.Style(self.window)
        for size in (9,8,7):
            style.configure('Calendar.TButton',font=('맑은 고딕',size))
            style.configure('Calendar.TLabel',font=('맑은 고딕',size))
            self.window.update_idletasks()
            if self.window.winfo_reqheight()<=available:break
        width=self.window.winfo_reqwidth();height=self.window.winfo_reqheight()
        x=max(0,min(self.target.winfo_x(),self.container.winfo_width()-width))
        y=max(0,self.target.winfo_y()-height-6)
        self.window.place(x=x,y=y,bordermode='ignore')
        self.window.lift()

    def _outside(self,event):
        if self.window is None:return
        if event.widget==self.entry or str(event.widget).startswith(str(self.window)):return
        self.close()

    def move(self, delta):
        index = self.year*12+self.month-1+delta
        year, month = divmod(index, 12)
        if 1 <= year <= 9999:
            self.year, self.month = year, month+1
            self.render()
            if self.target is not None:self.position()
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
        ttk.Button(self.body,style='Calendar.TButton',text='‹',width=3,command=lambda:self.move(-1)).grid(row=0,column=0)
        ttk.Label(self.body,style='Calendar.TLabel',text=f'{self.year}년 {self.month}월',anchor='center').grid(row=0,column=1,columnspan=5,sticky='ew')
        ttk.Button(self.body,style='Calendar.TButton',text='›',width=3,command=lambda:self.move(1)).grid(row=0,column=6)
        for column, label in enumerate('월화수목금토일'):
            ttk.Label(self.body,style='Calendar.TLabel',text=label,anchor='center').grid(row=1,column=column,pady=3)
        self.day_buttons = {}
        for row, week in enumerate(calendar.Calendar(firstweekday=0).monthdayscalendar(self.year,self.month),2):
            for column, day in enumerate(week):
                if day:
                    b=ttk.Button(self.body,style='Calendar.TButton',text=str(day),width=3,command=lambda d=day:self.choose(d))
                    b.grid(row=row,column=column,padx=1,pady=1)
                    self.day_buttons[day]=b
        self._mark_today(date.today())
        self.today_button=ttk.Button(self.body,style='Calendar.TButton',text='오늘',command=self.today)
        self.today_button.grid(row=8,column=0,columnspan=3,sticky='ew',pady=(8,0))
        ttk.Button(self.body,style='Calendar.TButton',text='닫기',command=self.close).grid(row=8,column=4,columnspan=3,sticky='ew',pady=(8,0))

