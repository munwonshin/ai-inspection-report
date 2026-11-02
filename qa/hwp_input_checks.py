"""Real Tk/DnD controller checks; HWP conversion/API/output are mocked."""
from pathlib import Path
import sys,tempfile,time,json
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tkinterdnd2 import TkinterDnD
from inspection.ui import App
from inspection.documents import PreparedDocument
root=TkinterDnD.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False);root.update()
def settle():
 end=time.monotonic()+20
 while app.busy and time.monotonic()<end:root.update();time.sleep(.01)
 root.update();assert not app.busy
def event(*paths):return SimpleNamespace(data=root.tk.call('format','%s',root.tk.call('list',*paths)))
pdf=PreparedDocument('가상 계획서 전체 내용','가상 계획서 전체 내용',b'%PDF-visual',2,(1,2),b'%PDF-original-converted')
errors=[]
try:
 with tempfile.TemporaryDirectory() as folder:
  hwp=Path(folder)/'가상 계획서 {검증} (1).HWP';hwp.write_bytes(bytes.fromhex('D0CF11E0A1B11AE1'))
  with patch('inspection.ui.prepare_hwp',return_value=pdf) as convert,patch('inspection.ui.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('inspection.ui.api.generate') as generate,patch('inspection.ui.exporter.save') as save,patch.object(app,'recognize_general') as recognize:
   app.connected=True
   app.minutes.insert('1.0','가상 회의록 보존');app.findings.insert('1.0','가상 검수 초안 보존')
   minutes=app.get(app.minutes);body=app.get(app.findings)
   assert app.pdf_drop(event(str(hwp)))=='copy';settle()
   convert.assert_called_once();recognize.assert_called_once()
   assert app.pdf_path==str(hwp) and 'HWP 변환 2쪽' in app.pdf_label.get()
   assert app.original_pdf_bytes==pdf.original_bytes and app.pdf_bytes==pdf.visual_pdf
   before=(app.pdf_path,app.plan,app.api_plan,app.original_pdf_bytes)
   with patch('inspection.ui.prepare_hwp',side_effect=RuntimeError('가상 변환 실패')):
    app.load_pdf('broken.hwp');settle()
   assert errors and before==(app.pdf_path,app.plan,app.api_plan,app.original_pdf_bytes)
   assert app.get(app.minutes)==minutes and app.get(app.findings)==body
   for paths in [('unsupported.hwpx',),(str(hwp),'second.pdf')]:assert app.pdf_drop(event(*paths))=='refuse_drop'
   app.busy=True;assert app.pdf_drop(event(str(hwp)))=='refuse_drop';app.remove_pdf();assert app.pdf_path==str(hwp);app.busy=False
   with patch('inspection.ui.filedialog.askopenfilename',return_value=str(hwp)) as chooser:
    app.attach();settle();types=chooser.call_args.kwargs['filetypes'];assert '*.pdf *.hwp' in str(types)
   app.remove_pdf();root.update();assert app.pdf_path=='' and app.original_pdf_bytes is None
   assert hwp.is_file() and app.get(app.minutes)==minutes and app.get(app.findings)==body
   app.pdf_drop(event(str(hwp)));settle();assert app.pdf_path==str(hwp)
   generate.assert_not_called();save.assert_not_called()
 result={'native_tkdnd':True,'hwp_button_and_drop':True,'uppercase_unicode_paths':True,'converted_pdf_retained_for_metadata_and_ai':True,'failed_replacement_preserves_inputs':True,'busy_and_unsupported_blocked':True,'remove_and_reattach':True,'api_calls':0,'report_outputs':0}
 Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
finally:root.destroy()
