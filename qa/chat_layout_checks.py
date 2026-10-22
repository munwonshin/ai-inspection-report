from pathlib import Path
import sys,time,json,ctypes
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base.parent))
try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:pass
import tkinter as tk
from inspection.ui import App
def pump(root):
    until=time.monotonic()+.18
    while time.monotonic()<until:root.update();time.sleep(.01)
def inside(w,p):
    x=w.winfo_rootx()-p.winfo_rootx();y=w.winfo_rooty()-p.winfo_rooty()
    return min(x,y)>=-2 and x+w.winfo_width()<=p.winfo_width()+2 and y+w.winfo_height()<=p.winfo_height()+2
rows=[]
for scaling in [None,2.0]:
    root=tk.Tk();root.attributes('-alpha',0)
    if scaling:root.tk.call('tk','scaling',scaling)
    app=App(root,restore_api=False)
    # Check the attachment-present layout, including its conditional × button.
    # The empty/hidden and cleared states are covered by pdf_drop_checks.py.
    app.pdf_path=r'C:\가상 화면배치 시험.pdf'
    app.pdf_label.set('가상 화면배치 시험.pdf\n1쪽 · 첨부 완료')
    app.refresh_state();pump(root)
    for width,height in [(1320,880),(1060,720)]:
        root.geometry(f'{width}x{height}');pump(root)
        for general in [False,True]:
            if app.general_expanded!=general:app.toggle_general();pump(root)
            for mode in ['chat','findings','actions']:
                if app.editor_open!=(mode!='chat'):app.toggle_editor();pump(root)
                if mode!='chat':app.editor_view.select(['findings','actions'].index(mode));pump(root)
                failures=[]
                widgets=app.buttons+[app.minutes]+([app.conversation] if mode=='chat' else [getattr(app,mode)])
                for w in widgets:
                    if general and str(w).startswith(str(app.input_panel)+'.'):continue
                    if not general and str(w).startswith(str(app.general_panel)+'.'):continue
                    if not w.winfo_ismapped():failures.append({'control':str(w),'reason':'unmapped'});continue
                    parent=w.master
                    while parent:
                        if not inside(w,parent):
                            failures.append({'control':str(w),'text':w.cget('text') if isinstance(w,tk.ttk.Button) else 'text',
                                'reason':'clipped','parent':str(parent),'bottom':w.winfo_rooty()-parent.winfo_rooty()+w.winfo_height(),'parent_height':parent.winfo_height()});break
                        parent=parent.master
                rows.append({'geometry':[root.winfo_width(),root.winfo_height()],'scaling':float(root.tk.call('tk','scaling')),'general':general,'mode':mode,'failures':failures})
    for timer in root.tk.call('after','info'):root.after_cancel(timer)
    root.destroy()
(base/'chat_layout_checks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
failed=[r for r in rows if r['failures']]
print(json.dumps({'cases':len(rows),'failed':failed},ensure_ascii=True),flush=True)
assert not failed
