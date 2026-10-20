import io,tempfile,unittest
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject,NameObject,DictionaryObject
from inspection import api
from inspection.documents import prepare_pdf
from inspection.core import GENERAL

def make_pdf(path,visual=False):
    w=PdfWriter()
    for i in range(1,11):
        page=w.add_blank_page(595,842)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):w._add_object(font)})})
        stream=DecodedStreamObject();draw='0 0 30 30 re S ' if visual and i==10 else ''
        stream.set_data((draw+f'BT /F1 12 Tf 20 700 Td (Page {i:02d} unique retained text beyond eight pages.) Tj ET').encode())
        page[NameObject('/Contents')]=w._add_object(stream)
    w.write(path)

class OptimizationTests(unittest.TestCase):
    def test_all_ten_text_pages_retained_without_pdf_duplication(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pdf';make_pdf(p);doc=prepare_pdf(p)
            self.assertEqual(doc.page_count,10);self.assertIsNone(doc.visual_pdf)
            self.assertIn('Page 10',doc.api_text);self.assertIn('Page 10',doc.local_text)
            self.assertEqual(doc.api_text.count('unique retained'),10)

    def test_visual_page_kept_and_every_other_page_in_text(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pdf';make_pdf(p,True);doc=prepare_pdf(p)
            self.assertEqual(doc.visual_pages,(10,));self.assertEqual(len(PdfReader(io.BytesIO(doc.visual_pdf)).pages),1)
            self.assertEqual(doc.api_text.count('unique retained'),9)
            self.assertIn('1→10',doc.api_text);self.assertIn('Page 10',doc.local_text)

    def test_known_general_not_regenerated_revision_keeps_sources_and_edits(self):
        current={'general':{k:'사용자 확인값' for k in GENERAL},'findings':'직접 편집한 긴 본문','actions':'사용자 안내','checks':'사용자 확인'}
        p=api.build_payload('전체 원본','회의 기록',current,'문체 수정',revision=True)
        self.assertNotIn('general',p['text']['format']['schema']['properties'])
        self.assertIn('전체 원본',p['input'][0]['content'][0]['text'])
        self.assertIn('회의 기록',p['input'][0]['content'][0]['text'])
        self.assertIn('직접 편집한 긴 본문',p['input'][1]['content'])
        self.assertFalse(p['store']);self.assertNotIn('previous_response_id',p)

    def test_only_missing_metadata_requested(self):
        p=api.build_payload('계획','회의',{'general':{'lead_org':'확인값'}},'초안')
        fields=p['text']['format']['schema']['properties']['general']['properties']
        self.assertNotIn('lead_org',fields);self.assertIn('project',fields)

    def test_cost_cached_write_and_long_context(self):
        u={'input_tokens':1000,'output_tokens':100,'input_tokens_details':{'cached_tokens':200,'cache_write_tokens':300}}
        self.assertAlmostEqual(api.estimate_cost(u,'gpt-6-luna'),(.00005+.000002+.0000375+.00005))
        self.assertAlmostEqual(api.estimate_cost({'input_tokens':300000,'output_tokens':1000},'gpt-6-luna'),.06075)

    def test_long_edited_report_gets_larger_output_budget(self):
        p=api.build_payload('계획','회의',{'findings':'장문'*6000},'수정',revision=True)
        self.assertEqual(p['max_output_tokens'],24000)
        self.assertIn('장문'*6000,p['input'][1]['content'])

if __name__=='__main__':unittest.main()
