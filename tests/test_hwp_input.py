import json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from inspection import hwp_input,documents

SIGNATURE=bytes.fromhex('D0CF11E0A1B11AE1')

class HwpInputTests(unittest.TestCase):
    def test_rejects_wrong_extension_or_disguised_pdf_before_worker(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(hwp_input.subprocess,'run') as run:
            path=Path(folder)/'fake.hwp';path.write_bytes(b'%PDF-not-hwp')
            with self.assertRaises(ValueError):hwp_input.convert_pdf(path,lambda _:None)
            path=Path(folder)/'fake.hwpx';path.write_bytes(SIGNATURE)
            with self.assertRaises(ValueError):hwp_input.convert_pdf(path,lambda _:None)
            run.assert_not_called()

    def test_rejects_size_before_read(self):
        with patch.object(Path,'is_file',return_value=True),patch.object(Path,'stat',return_value=SimpleNamespace(st_size=hwp_input.MAX_BYTES+1)),patch.object(Path,'read_bytes') as read:
            with self.assertRaises(ValueError):hwp_input.validate_source('large.hwp')
            read.assert_not_called()

    def _simulate(self,callback,*,pages=2,consumer_error=False):
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'source.hwp';src.write_bytes(SIGNATURE+b'synthetic');original=src.read_bytes();jobs=[]
            def run(command,**kw):
                request=Path(command[-2]);jobs.append(request.parent)
                self.assertNotEqual(request.parent,src.parent)
                self.assertEqual(kw['timeout'],120)
                callback(request,Path(command[-1]));return SimpleNamespace(returncode=0)
            def consume(pdf):
                self.assertEqual(pdf.read_bytes(),b'%PDF-synthetic')
                if consumer_error:raise ValueError('consumer failed')
                return SimpleNamespace(page_count=pages)
            with patch.object(hwp_input.subprocess,'run',side_effect=run):
                try:return hwp_input.convert_pdf(src,consume)
                finally:
                    self.assertEqual(src.read_bytes(),original)
                    self.assertTrue(all(not p.exists() for p in jobs))

    def test_success_consumes_private_pdf_and_cleans_without_changing_original(self):
        def worker(req,res):
            self.assertIn('hwp',json.loads(req.read_text()))
            req.with_name('input.pdf').write_bytes(b'%PDF-synthetic');res.write_text(json.dumps({'ok':True,'pages':2}))
        self.assertEqual(self._simulate(worker).page_count,2)

    def test_worker_failure_cleans_private_inputs(self):
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            self._simulate(lambda req,res:res.write_text(json.dumps({'ok':False,'error':'synthetic failure'})))

    def test_timeout_preserves_original_and_cleans(self):
        def timeout(req,res):raise subprocess.TimeoutExpired('worker',120)
        with self.assertRaisesRegex(RuntimeError,'시간이 초과'):self._simulate(timeout)

    def test_pdf_page_loss_is_rejected(self):
        def worker(req,res):
            req.with_name('input.pdf').write_bytes(b'%PDF-synthetic');res.write_text(json.dumps({'ok':True,'pages':2}))
        with self.assertRaisesRegex(RuntimeError,'쪽수가 다릅니다'):self._simulate(worker,pages=1)

    def test_bad_pdf_and_consumer_failure_cleanup(self):
        def worker(req,res):
            req.with_name('input.pdf').write_bytes(b'%PDF-synthetic');res.write_text(json.dumps({'ok':True,'pages':2}))
        with self.assertRaisesRegex(ValueError,'consumer failed'):self._simulate(worker,consumer_error=True)
        with self.assertRaisesRegex(RuntimeError,'PDF 변환본'):self._simulate(lambda req,res:res.write_text(json.dumps({'ok':True,'pages':2})))

    def test_hwp_routes_converted_pdf_through_existing_preparation(self):
        expected=object()
        with patch('inspection.hwp_input.convert_pdf',side_effect=lambda p,c:c(Path('converted.pdf'))) as convert,patch('inspection.documents.prepare_pdf',return_value=expected) as prepare:
            self.assertIs(documents.prepare_hwp('source.hwp'),expected)
            convert.assert_called_once();prepare.assert_called_once_with(Path('converted.pdf'),progress=None)

if __name__=='__main__':unittest.main()
