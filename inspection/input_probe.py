"""Explicit local-only UI attachment diagnostic; no API or report generation."""
def main():
    import sys,json,time,tempfile,hashlib
    from pathlib import Path
    import tkinter as tk
    from tkinter import messagebox
    from .ui import App
    from . import api
    source=Path(sys.argv[2]);output=Path(sys.argv[3]);start=time.perf_counter()
    before=hashlib.sha256(source.read_bytes()).hexdigest();errors=[];types=[];root=None;calls=[]
    request=api.request;showerror=messagebox.showerror
    def denied(*args,**kwargs):
        calls.append(True);raise AssertionError('Local diagnostic forbids API requests')
    try:
        api.request=denied;messagebox.showerror=lambda title,text,**kwargs:errors.append(text)
        with tempfile.TemporaryDirectory(prefix='inspection-local-check-') as folder:
            root=tk.Tk();root.withdraw();app=App(root,restore_api=False,preferences_path=Path(folder)/'preferences.json')
            safe=app.safe_error
            def capture(error):types.append(type(error).__name__);return safe(error)
            app.safe_error=capture
            app.minutes.insert('1.0','가상 보존 확인');app.findings.insert('1.0','가상 편집 보존 확인')
            app.load_pdf(str(source));deadline=time.monotonic()+120
            while (app.busy or not app.mailbox.empty()) and time.monotonic()<deadline:
                root.update();time.sleep(.02)
            root.update()
            result={'ok':not app.busy and not errors and app.pdf_path==str(source),'seconds':round(time.perf_counter()-start,3),
                'format':source.suffix.lower(),'units':app.pdf_page_count,'characters':len(app.plan),
                'images':len(app.pdf_bytes)//2 if isinstance(app.pdf_bytes,tuple) else 0,
                'original_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before,
                'input_preserved':app.get(app.minutes)=='가상 보존 확인' and app.get(app.findings)=='가상 편집 보존 확인',
                'api_calls':len(calls),'error_types':types,'errors':errors}
            root.destroy();root=None
    except Exception as error:
        result={'ok':False,'error_type':type(error).__name__,'api_calls':len(calls)}
    finally:
        api.request=request;messagebox.showerror=showerror
        if root is not None:root.destroy()
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
