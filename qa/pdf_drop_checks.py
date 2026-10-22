"""Native TkDND integration; only synthetic local PDF, no API or HWP output."""
from pathlib import Path
import sys,tempfile,time,json
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tkinterdnd2 import TkinterDnD
from pypdf import PdfWriter
from inspection.ui import App

root=TkinterDnD.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False);root.update()
assert root.tk.call('package','provide','tkdnd')
assert app.pdf_surface.dnd_bind('<<Drop>>')
assert all(w.dnd_bind('<<Drop>>') for w in app.pdf_surface.winfo_children())
def settle():
    until=time.monotonic()+30
    while app.busy and time.monotonic()<until:root.update();time.sleep(.02)
    root.update();assert not app.busy
def event(*paths):
    data=root.tk.call('format','%s',root.tk.call('list',*paths))
    return SimpleNamespace(data=data)
with tempfile.TemporaryDirectory(prefix='inspection-pdf-drop-') as tmp:
    p=Path(tmp)/'가상 사업계획서 {검증} (1).PDF'
    writer=PdfWriter();writer.add_blank_page(595,842);writer.write(p)
    errors=[]
    with patch('inspection.ui.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('inspection.ui.metadata.extract',return_value=({},{})),patch('inspection.ui.vault.read',return_value='fake'):
        assert app.pdf_drop(event(str(p)))=='copy';settle()
        assert app.pdf_path==str(p) and '첨부 완료' in app.pdf_label.get()
        before=(app.pdf_path,app.plan,app.api_plan,app.pdf_bytes)
        for paths in [(),('bad.txt',),(str(p),str(p)),('{broken',)]:
            assert app.pdf_drop(event(*paths))=='refuse_drop'
            assert (app.pdf_path,app.plan,app.api_plan,app.pdf_bytes)==before
        assert app.pdf_drop(SimpleNamespace(data='{broken'))=='refuse_drop'
        app.busy=True
        assert app.pdf_drop(event(str(p)))=='refuse_drop'
        app.busy=False
        bad=Path(tmp)/'가상 손상.pdf';bad.write_text('not a pdf',encoding='utf-8')
        app.pdf_drop(event(str(bad)));settle();assert errors
        assert (app.pdf_path,app.plan,app.api_plan,app.pdf_bytes)==before
        with patch('inspection.ui.filedialog.askopenfilename',return_value=str(p)) as chooser:
            app.attach();settle();chooser.assert_called_once()
        assert app.pdf_path==str(p)
        app.minutes.insert('1.0','가상 회의록 보존')
        app.findings.insert('1.0','가상 직접 편집 초안 보존')
        report=app.snapshot();minutes=app.get(app.minutes)
        root.update();assert app.remove_pdf_button.winfo_ismapped()
        app.lock(True);assert app.remove_pdf_button.instate(['disabled'])
        app.remove_pdf();assert app.pdf_path==str(p)
        app.lock(False)
        with patch('inspection.ui.api.generate') as generate,patch('inspection.ui.exporter.save') as save:
            app.remove_pdf_button.invoke();root.update()
            assert (app.pdf_path,app.plan,app.api_plan,app.pdf_bytes)==('','','',None)
            assert app.snapshot()==report and app.get(app.minutes)==minutes
            assert not app.remove_pdf_button.winfo_ismapped() and p.is_file()
            app.connected=True
            with patch('inspection.ui.messagebox.showinfo'):
                assert app.ready() is False
            generate.assert_not_called();save.assert_not_called()
        assert app.pdf_drop(event(str(p)))=='copy';settle()
        assert app.pdf_path==str(p) and app.remove_pdf_button.winfo_ismapped()
result={'native_tkdnd_loaded':True,'all_pdf_card_children_registered':True,'unicode_spaces_braces_uppercase_pdf':True,'multiple_non_pdf_invalid_data_rejected':True,'busy_drop_blocked':True,'corrupt_pdf_preserves_previous':True,'button_same_reader':True,'remove_clears_all_pdf_payloads':True,'remove_preserves_minutes_draft_and_original_file':True,'remove_blocked_while_busy':True,'reattach_after_remove':True,'no_generation_without_attachment':True,'api_calls':0,'hwp_saves':0}
app.lock(True)
for i in range(101):app.pdf_progress.put((i,100))
app.poll()
assert app.busy and '100/100쪽' in app.status.get()
assert app.remove_pdf_button.instate(['disabled'])
app.lock(False)
result['progress_queue_drained_without_unlocking']=True
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
root.destroy();print('PDF_DROP_CHECKS_OK',flush=True)
