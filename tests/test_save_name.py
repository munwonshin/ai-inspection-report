import unittest
from pathlib import Path
from unittest.mock import patch
from inspection.core import filename,destination
from inspection import exporter
from test_core import fixture

class SaveNameTests(unittest.TestCase):
    def test_outer_whitespace_and_trailing_dots(self):
        for raw in [' 가상_점검결과 ', '가상_점검결과.', '  가상_점검결과 ... ', '\u3000가상_점검결과\u00a0.\u3000']:
            with self.subTest(raw=raw):self.assertEqual(filename(raw),'가상_점검결과.hwp')

    def test_extension_and_spacing(self):
        for raw in [' 가상_점검결과.HWP ', '가상_점검결과 .hwp.', '가상_점검결과... .HWP . ']:
            with self.subTest(raw=raw):self.assertEqual(filename(raw),'가상_점검결과.hwp')

    def test_empty_after_cleanup_and_reserved_names(self):
        for raw in ['','   ',' ... ','.hwp',' .HWP . ',' CON . ','CON .txt',' nul.HWP. ']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):filename(raw)

    def test_valid_inner_characters_stay_unchanged(self):
        for raw in ['가상_결과 (검수)-1','2026.10.20_가상 결과','가상  결과','.가상_결과']:
            self.assertEqual(filename(raw),raw+'.hwp')

    def test_local_and_unc_use_identical_cleanup(self):
        for folder in [r'D:\가상 검사',r'\\서버\공유\가상 검사']:
            self.assertEqual(destination(folder,' 가상_결과. '),destination(folder,'가상_결과'))

    def test_cannot_hide_invalid_inner_characters(self):
        for char in '<>:"/\\|?*\x00\x1f':
            with self.subTest(char=char),self.assertRaises(ValueError):filename(' 가상'+char+'결과. ')

    def test_collision_uses_cleaned_name_before_com_or_staging(self):
        report=fixture();paths=[]
        payload={'approved':True,'report':report.as_dict(),'destination':r'D:\가상\ 가상_결과. .hwp '}
        with patch.object(Path,'is_dir',return_value=True),patch.object(Path,'exists',autospec=True,side_effect=lambda p:paths.append(p) or True),patch('inspection.exporter.template_text') as template,patch('inspection.exporter.tempfile.mkdtemp') as stage:
            with self.assertRaises(FileExistsError):exporter.worker(payload)
            self.assertEqual(paths,[Path(r'D:\가상\가상_결과.hwp')])
            template.assert_not_called();stage.assert_not_called()
