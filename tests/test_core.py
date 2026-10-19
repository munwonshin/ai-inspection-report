import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from inspection.core import *
from inspection import exporter,api

def fixture(long=False):
    general={k:'가상 '+label for k,label in GENERAL.items()}
    general['visit_date']='2026년 10월 19일'
    text='[명확한 가상 검증 자료]\n기업 설명: 가상 센서의 시연을 설명함.\n확인된 사실: 회의록에 시연 확인 기록이 있음.\n예정 사항: 성능시험은 예정이며 실적이 아님.\n직접 편집 보존 A & B <검수>.'
    if long:text+='\n'+'\n'.join(f'{i:03d}. 가상 장문 검증 문단입니다. 기업 설명과 확인 사실을 구분하고 예정 사항을 실적으로 기록하지 않습니다.' for i in range(1,91))
    return Report('가상 검증용 현장점검 결과서',tuple(general.items()),text,
        '회의록에 기재된 조치요청 없음.','가상 시험일은 자료에서 확인되지 않음.')

class CoreTests(unittest.TestCase):
    def test_approval_gate_before_any_io(self):
        with patch('inspection.exporter.tempfile.TemporaryDirectory') as tmp,patch('inspection.exporter.template_text') as template:
            with self.assertRaises(PermissionError):exporter.save(fixture(),'Z:\\unreachable','name')
            tmp.assert_not_called();template.assert_not_called()

    def test_invalid_names(self):
        for s in ['../a','a/b','a\\b','CON','nul.txt','COM¹','LPT9','a:stream','a?b','a.',' a','a ','','x\nname']:
            with self.subTest(s=s),self.assertRaises(ValueError):filename(s)

    def test_valid_names_and_no_double_extension(self):
        self.assertEqual(filename('가상 결과서'),'가상 결과서.hwp')
        self.assertEqual(filename('결과.HWP'),'결과.hwp')

    def test_path_forms(self):
        for f in ['relative','C:relative','\\root','\\\\?\\C:\\x']:
            with self.assertRaises(ValueError):destination(f,'a')
        self.assertEqual(str(destination('Z:\\시험','a')).lower(),'z:\\시험\\a.hwp')
        self.assertIn('서버',str(destination('\\\\서버\\공유\\시험','a')))

    def test_exact_source_evidence_only(self):
        accepted=evidenced_general({'lead_org':{'value':'가상회사','evidence':'주관기관: 가상회사','source':'plan'},
            'project':{'value':'허위','evidence':'없는 근거','source':'minutes'}},'주관기관: 가상회사','')
        self.assertEqual(accepted,{'lead_org':'가상회사'})

    def test_roundtrip_and_signature_cell(self):
        report=fixture();xml=compose(exporter.template_text(),report)
        verify_xml(xml,report)
        root,t=parse_template(xml)
        self.assertEqual(cell_text(table_cell(t[5],1,4)),'(인)')
        self.assertEqual(len(t),6)
        self.assertFalse(list(root.iter('SCRIPTCODE')))
        self.assertIn('&amp;',xml)
        self.assertIn('&lt;검수&gt;',xml)

    def test_long_body_is_not_truncated(self):
        report=fixture(True);xml=compose(exporter.template_text(),report)
        verify_xml(xml,report)
        root,t=parse_template(xml)
        self.assertIn('090.',cell_text(table_cell(t[4],1,1)))
        self.assertEqual(t[4].get('PageBreak'),'Cell')
        self.assertEqual(t[4].find('./SHAPEOBJECT/POSITION').get('TreatAsChar'),'false')

    def test_tamper_detection(self):
        report=fixture();xml=compose(exporter.template_text(),report)
        with self.assertRaises(ValueError):verify_xml(xml.replace('직접 편집 보존','다른 내용'),report)

    def test_general_missing(self):
        self.assertEqual(len(Report('',(),'','','').missing()),len(GENERAL))

    def test_api_context_includes_current_edits(self):
        current=fixture().as_dict()
        response={'findings':'가상 수정','actions':'근거 없음','checks':'','general':{}}
        with patch('inspection.api.request',return_value=(json.dumps(response),{})) as request:
            api.generate('TEST_KEY_NEVER_REAL','가상 계획','가상 회의록',current,'가상 수정 요청')
            payload=request.call_args.args[1]
            self.assertFalse(payload['store'])
            self.assertNotIn('tools',payload)
            self.assertIn('직접 편집 보존',payload['input'][1]['content'])
            self.assertIn('source_plan_local_quote_check_text',payload['input'][1]['content'])

    def test_full_pdf_in_request_without_files_upload(self):
        response={'findings':'가상 수정','actions':'근거 없음','checks':'','general':{}}
        with patch('inspection.api.request',return_value=(json.dumps(response),{})) as request:
            api.generate('TEST_KEY','가상 계획','가상 회의록',fixture().as_dict(),'가상 요청',pdf_bytes=b'%PDF-FAKE-TEST')
            parts=request.call_args.args[1]['input'][1]['content']
            self.assertEqual(parts[0]['type'],'input_file')
            self.assertTrue(parts[0]['file_data'].startswith('data:application/pdf;base64,'))
            self.assertIn('직접 편집 보존',parts[1]['text'])

    def test_api_errors_do_not_return_provider_payload(self):
        import urllib.error
        error=urllib.error.HTTPError(api.ENDPOINT,401,'SECRET_SHOULD_NOT_APPEAR',{},None)
        with patch('urllib.request.urlopen',side_effect=error):
            with self.assertRaises(api.ApiFailure) as exc:api.request('TEST_KEY',{})
            self.assertNotIn('SECRET',str(exc.exception))

    def test_incomplete_api_response_rejected(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('urllib.request.urlopen',return_value=response),patch('json.load',return_value={'status':'incomplete'}):
            with self.assertRaises(api.ApiFailure):api.request('TEST_KEY',{})

    def test_snapshot_is_immutable(self):
        report=fixture()
        with self.assertRaises(Exception):report.findings='changed'

if __name__=='__main__':unittest.main()
