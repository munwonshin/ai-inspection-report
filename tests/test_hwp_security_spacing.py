import tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from inspection import exporter
from inspection.core import Report,GENERAL,compose,verify_xml,parse_template,table_cell,cell_text

def report():return Report('가상 저장 시험',tuple((k,'가상 값') for k in GENERAL),'• 가상 시연을 확인함.\n\n• 가상 시험은 예정임.','• 가상 보관 방법을 안내함.\n\n• 가상 일자는 미정임.','')

class SecuritySpacingTests(unittest.TestCase):
    def test_empty_paragraph_only_fixed_3pt(self):
        xml=compose(exporter.template_text(),report());verify_xml(xml,report());root,t=parse_template(xml)
        shapes={s.get('Id'):s for s in root.iter('PARASHAPE')}
        for row in (1,2):
            ps=table_cell(t[4],row,1).findall('./PARALIST/P');self.assertEqual(len(ps),3)
            self.assertEqual(cell_text(table_cell(t[4],row,1)),[report().findings,report().actions][row-1])
            self.assertEqual(shapes[ps[1].get('ParaShape')].find('PARAMARGIN').get('LineSpacing'),'300')
            self.assertEqual(shapes[ps[1].get('ParaShape')].find('PARAMARGIN').get('LineSpacingType'),'Fixed')
            self.assertNotEqual(ps[0].get('ParaShape'),ps[1].get('ParaShape'))

    def test_spacing_tamper_detected(self):
        xml=compose(exporter.template_text(),report()).replace('LineSpacing="300"','LineSpacing="400"')
        with self.assertRaises(ValueError):verify_xml(xml,report())

    def test_unapproved_export_before_com_or_io(self):
        with patch('inspection.exporter.tempfile.mkdtemp') as temporary,patch('win32com.client.DispatchEx') as dispatch:
            with self.assertRaises(PermissionError):exporter.worker({'approved':False})
            temporary.assert_not_called();dispatch.assert_not_called()

    def test_invalid_native_hwp_data_rejected(self):
        for value in ('<HWPML/>','SGVsbG8=','',None):
            with self.assertRaises(RuntimeError):exporter.native_hwp_bytes(value)

    def test_hwp_base64_with_line_breaks(self):
        import base64
        data=bytes.fromhex('D0CF11E0A1B11AE1')+b'synthetic bytes'
        text=base64.b64encode(data).decode();text=text[:8]+'\r\n'+text[8:]
        self.assertEqual(exporter.native_hwp_bytes(text),data)

    def test_export_never_calls_hancom_file_access_or_security_module(self):
        import base64
        data=bytes.fromhex('D0CF11E0A1B11AE1')+b'mocked transport only'
        xml=compose(exporter.template_text(),report());hwp=Mock();hwp.PageCount=1
        hwp.SetTextFile.return_value=True
        hwp.GetTextFile.side_effect=lambda fmt,opt:xml if fmt=='HWPML2X' else base64.b64encode(data).decode()
        with tempfile.TemporaryDirectory() as folder,patch('win32com.client.DispatchEx',return_value=hwp):
            result=exporter.worker({'approved':True,'report':report().as_dict(),'destination':str(Path(folder)/'synthetic.hwp')})
            self.assertEqual(Path(result['path']).read_bytes(),data)
        hwp.Open.assert_not_called();hwp.SaveAs.assert_not_called();hwp.RegisterModule.assert_not_called()
        self.assertIn('encoding="UTF-16"',hwp.SetTextFile.call_args_list[0].args[0])
        self.assertEqual(hwp.SetTextFile.call_args_list[1].args[1],'HWP')

if __name__=='__main__':unittest.main()
