import json,unittest
from unittest.mock import patch
from inspection import metadata,api

def entry(value,evidence,source='plan'):return dict(value=value,evidence=evidence,source=source)

class MetadataTests(unittest.TestCase):
    def test_exact_and_wrapped_evidence(self):
        text='과제명: 가상 AI\n점검 사업\n주관기관: 가상 기관'
        result=metadata.accepted_general({'project':entry('가상 AI 점검 사업','과제명: 가상 AI 점검 사업'), 'lead_org':entry('가상 기관','주관기관: 가상 기관')},text)
        self.assertEqual(result,{'project':'가상 AI 점검 사업','lead_org':'가상 기관'})

    def test_reject_unverified_and_visit_inference(self):
        text='과제명: 가상 계획'
        data={'project':entry('다른 사업','과제명: 가상 계획'),'lead_org':entry('가상 계획','과제명: 가상 계획','minutes'),'partner_org':entry('가상 계획',''), 'visit_date':entry('가상 계획',text)}
        self.assertEqual(metadata.accepted_general(data,text),{})

    def test_only_requested_missing_plan_fields_sent(self):
        data={'project':entry('가상 사업','과제명: 가상 사업')}
        with patch('inspection.api.request',return_value=(json.dumps(data),{'input_tokens':10})) as call:
            result,usage=metadata.extract('fake','과제명: 가상 사업','과제명: 가상 사업',b'%PDF-TEST',('project','visit_date'))
        payload=call.call_args.args[1]
        self.assertFalse(payload['store']);self.assertEqual(payload['model'],api.MODEL)
        self.assertEqual(payload['text']['format']['schema']['required'],['project'])
        self.assertEqual(payload['input'][0]['content'][0]['type'],'input_file')
        self.assertEqual(result,{'project':'가상 사업'})

    def test_no_fields_no_request(self):
        with patch('inspection.api.request') as call:self.assertEqual(metadata.extract('fake','','',fields=()),({},{}));call.assert_not_called()

    def test_malformed_response_rejected(self):
        for data in [[],{'project':None},{'wrong':{}},{'project':{'value':9}}]:
            with self.subTest(data=data),patch('inspection.api.request',return_value=(json.dumps(data),{})):
                with self.assertRaises(api.ApiFailure):metadata.extract('fake','가상','가상',fields=('project',))
