import base64,json,unittest
from unittest.mock import patch
from inspection import metadata,api

def entry(value,evidence,source='plan',page=2,reason=''):
    return dict(value=value,evidence=evidence,source=source,page=page,reason=reason)

class MetadataTests(unittest.TestCase):
    def test_scanned_or_split_table_evidence_is_retained(self):
        result=metadata.accepted_general({'project':entry('가상 AI 점검 사업','과제명: 가상 AI\n점검 사업')},3)
        self.assertEqual(result,{'project':'가상 AI 점검 사업'})
        self.assertEqual(result.evidence['project']['page'],2)

    def test_reject_mismatched_quote_page_and_source(self):
        data={'project':entry('다른 사업','과제명: 가상 계획'), 'lead_org':entry('가상 기관','가상 기관','minutes'),
            'partner_org':entry('가상 기관','가상 기관',page=9),'lead_person':entry('가상 책임자',''),
            'visit_date':entry('미지원 항목','미지원 항목')}
        result=metadata.accepted_general(data,3)
        self.assertEqual(result,{})
        self.assertIn('project',result.issues)

    def test_entire_original_bytes_sent_without_text_duplication(self):
        data={'project':entry('가상 사업','과제명: 가상 사업')};original=b'%PDF-ALL-ORIGINAL-PAGES'
        with patch('inspection.api.request',return_value=(json.dumps(data),{})) as call:
            result,usage=metadata.extract('fake',original,3,('project','visit_date'))
        payload=call.call_args.args[1];content=payload['input'][0]['content']
        self.assertFalse(payload['store']);self.assertEqual(payload['model'],api.MODEL)
        self.assertEqual(payload['text']['format']['schema']['required'],['project'])
        self.assertEqual(len(content),1);self.assertEqual(content[0]['type'],'input_file')
        self.assertEqual(base64.b64decode(content[0]['file_data'].split(',',1)[1]),original)
        self.assertEqual(result,{'project':'가상 사업'})

    def test_no_fields_no_request(self):
        with patch('inspection.api.request') as call:
            self.assertEqual(metadata.extract('fake',None,0,()),({},{}));call.assert_not_called()

    def test_malformed_response_rejected(self):
        for data in [[],{'project':None},{'wrong':{}},{'project':{'value':9}}, {'project':entry('가상','가상',page=True)}]:
            with self.subTest(data=data),patch('inspection.api.request',return_value=(json.dumps(data),{})):
                with self.assertRaises(api.ApiFailure):metadata.extract('fake',b'%PDF-TEST',3,('project',))

    def test_missing_value_reason_is_available_for_review(self):
        result=metadata.accepted_general({'lead_org':entry('','','none',0,'기관 역할 구분이 불명확함')},3)
        self.assertEqual(result,{})
        self.assertEqual(result.issues['lead_org'],'기관 역할 구분이 불명확함')

    def test_unicode_legal_company_symbol_matches_quote(self):
        result=metadata.accepted_general({'lead_org':entry('㈜가상','주관기관: (주)가상')},3)
        self.assertEqual(result,{'lead_org':'㈜가상'})
