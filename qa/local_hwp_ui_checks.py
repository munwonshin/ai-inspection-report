"""Read caller-specified HWP locally with all API/Hancom application calls forbidden."""
from pathlib import Path
import sys,time,tempfile,json,hashlib
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'tests')]
import tkinter as tk
from inspection.ui import App
from test_hwp_direct import compound,text,rec
source=Path(sys.argv[1]);before=hashlib.sha256(source.read_bytes()).digest();errors=[]
with tempfile.TemporaryDirectory(prefix='local-hwp-ui-') as folder:
    root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False,preferences_path=Path(folder)/'prefs.json')
    def settle():
        end=time.monotonic()+120
        while (app.busy or not app.mailbox.empty()) and time.monotonic()<end:root.update();time.sleep(.01)
        root.update();assert not app.busy
    try:
        with patch('inspection.ui.messagebox.showerror',side_effect=lambda *a,**kw:errors.append(a)),patch('inspection.api.request',side_effect=AssertionError('API forbidden')) as request,patch('win32com.client.DispatchEx',side_effect=AssertionError('Hancom forbidden')) as dispatch,patch('inspection.hwp_input.convert_pdf',side_effect=AssertionError('PDF conversion forbidden')) as convert:
            app.minutes.insert('1.0','가상 보존 회의록');app.findings.insert('1.0','가상 보존 초안')
            start=time.perf_counter();app.load_pdf(str(source));settle();seconds=time.perf_counter()-start
            assert not errors,errors
            assert app.pdf_path==str(source) and app.plan and isinstance(app.pdf_bytes,tuple)
            snapshot=(app.pdf_path,app.plan,app.original_pdf_bytes,app.pdf_bytes)
            bad=Path(folder)/'unsupported.hwp';bad.write_bytes(compound([text('가상')+rec(76,2,b'cer$cer$')]))
            app.load_pdf(str(bad));settle();assert errors
            assert snapshot==(app.pdf_path,app.plan,app.original_pdf_bytes,app.pdf_bytes)
            assert app.get(app.minutes)=='가상 보존 회의록' and app.get(app.findings)=='가상 보존 초안'
            request.assert_not_called();dispatch.assert_not_called();convert.assert_not_called()
            assert hashlib.sha256(source.read_bytes()).digest()==before
            proof={'local_attachment_seconds':round(seconds,3),'whole_text_characters':len(app.plan),'image_inputs':len(app.pdf_bytes)//2,
                'hancom_application_calls':0,'pdf_conversion_calls':0,'api_calls':0,'original_unchanged':True,
                'unsupported_preserves_attachment_and_draft':True,'no_report_generated':True}
            (R/'qa/local_hwp_ui_checks.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof),flush=True)
    finally:root.destroy()
