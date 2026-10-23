"""Windows tick indicator, with real Tk selection and isolated settings."""
import sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
from inspection.ui import App
from inspection import preferences

def dispose(root):
    for timer in root.tk.call('after','info'):root.after_cancel(timer)
    root.destroy()

with tempfile.TemporaryDirectory(prefix='pin-tick-') as folder:
    path=Path(folder)/'preferences.json'
    root=tk.Tk();app=App(root,restore_api=False,preferences_path=path)
    app.toggle_general();root.update()
    style=ttk.Style(root)
    assert 'Pin.indicator' in style.element_names()
    assert 'Pin.indicator' in str(style.layout('Pin.TCheckbutton'))
    pins=[w for w in app.general_body.winfo_children() if isinstance(w,ttk.Checkbutton)]
    assert len(pins)==3 and all(w.cget('style')=='Pin.TCheckbutton' for w in pins)
    for key,pin in zip(preferences.FIELDS,pins):
        app.general[key].set('가상 '+key)
        pin.invoke();assert app.pinned[key].get() and pin.instate(['selected'])
    assert len(preferences.load(path))==3
    # Native selection persists when processing disables and re-enables controls.
    app.lock(True);assert all(w.instate(['selected','disabled']) for w in pins)
    app.lock(False);assert all(w.instate(['selected','!disabled']) for w in pins)
    pins[2].focus_force();root.update();pins[2].event_generate('<KeyPress-space>');pins[2].event_generate('<KeyRelease-space>');root.update()
    assert not app.pinned['inspector'].get() and not pins[2].instate(['selected'])
    pins[2].invoke();assert app.pinned['inspector'].get()
    dispose(root)
    root=tk.Tk();app=App(root,restore_api=False,preferences_path=path);root.update()
    pins=[w for w in app.general_body.winfo_children() if isinstance(w,ttk.Checkbutton)]
    assert all(w.instate(['selected']) for w in pins)
    for pin in pins:pin.invoke()
    assert preferences.load(path)=={}
    dispose(root)
print('NATIVE_WINDOWS_PIN_TICK_AND_PERSISTENCE_OK',flush=True)
