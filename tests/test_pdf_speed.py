import io,sys,unittest,tempfile,importlib.util
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject,NameObject,DictionaryObject,NumberObject
from inspection.documents import prepare_pdf
from pypdf._font import Font

spec=importlib.util.spec_from_file_location('pdf_baseline',Path(__file__).resolve().parents[1]/'qa'/'pdf_baseline.py')
baseline=importlib.util.module_from_spec(spec);sys.modules[spec.name]=baseline;spec.loader.exec_module(baseline)

def shared_font_pdf(path,label='synthetic',visual=False):
    writer=PdfWriter()
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    reference=writer._add_object(font)
    for i in range(10):
        page=writer.add_blank_page(595,842)
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):reference})})
        stream=DecodedStreamObject()
        stream.set_data((f'BT /F1 12 Tf 20 700 Td ({label} unique page {i+1:02d} complete evidence text.) Tj ET'+(' 0 0 20 20 re S' if visual and i==9 else '')).encode())
        page[NameObject('/Contents')]=writer._add_object(stream)
    writer.write(path)

class PdfSpeedTests(unittest.TestCase):
    def test_exact_fields_equal_and_shared_font_parsed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'shared.pdf';shared_font_pdf(path,visual=True)
            old=baseline.prepare_pdf(path)
            with patch.object(Font,'from_font_resource',wraps=Font.from_font_resource) as factory:
                new=prepare_pdf(path);self.assertEqual(factory.call_count,1)
            self.assertEqual(vars(old),vars(new))
            self.assertIn('page 10',new.local_text);self.assertEqual(new.visual_pages,(10,))

    def test_font_cache_never_crosses_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a.pdf';b=Path(tmp)/'b.pdf'
            shared_font_pdf(a,'FIRST');shared_font_pdf(b,'SECOND')
            with patch.object(Font,'from_font_resource',wraps=Font.from_font_resource) as factory:
                prepare_pdf(a);second=prepare_pdf(b);self.assertEqual(factory.call_count,2)
            self.assertNotIn('FIRST',second.local_text);self.assertIn('SECOND',second.local_text)

    def test_adapter_failure_and_other_version_use_public_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fallback.pdf';shared_font_pdf(path,visual=True)
            old=vars(baseline.prepare_pdf(path))
            with patch('inspection.documents.layout_text_and_operations',side_effect=RuntimeError('synthetic adapter failure')):
                self.assertEqual(old,vars(prepare_pdf(path)))
            with patch('pypdf.__version__','future'):
                self.assertEqual(old,vars(prepare_pdf(path)))

    def test_progress_covers_all_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'progress.pdf';shared_font_pdf(path)
            events=[];prepare_pdf(path,progress=lambda i,n:events.append((i,n)))
            self.assertEqual(events,[(i,10) for i in range(11)])

    def test_blank_rotated_page_keeps_original_visual_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'visual.pdf';writer=PdfWriter()
            page=writer.add_blank_page(595,842);page[NameObject('/Rotate')]=NumberObject(90)
            writer.write(path)
            self.assertEqual(vars(baseline.prepare_pdf(path)),vars(prepare_pdf(path)))
