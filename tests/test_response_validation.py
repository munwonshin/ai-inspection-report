import json,unittest
from unittest.mock import patch
from inspection import api

class ResponseValidationTests(unittest.TestCase):
    def test_malformed_general_rejected_before_ui_consumption(self):
        for record in [None,[],{'value':7,'evidence':'가상','source':'minutes'},
                {'value':'가상','evidence':None,'source':'minutes'},
                {'value':'가상','evidence':'가상','source':'guessed'},
                {'value':'가상','source':'minutes'}]:
            with self.subTest(record=record):
                body={'findings':'가상','actions':'가상','general':{'project':record}}
                with patch('inspection.api.request',return_value=(json.dumps(body),{})):
                    with self.assertRaises(api.ApiFailure):api.generate('fake','가상','가상',{},'작성')

    def test_top_level_shapes_rejected_as_api_failure(self):
        for body in [[],None,0,'가상']:
            with self.subTest(body=body),patch('inspection.api.request',return_value=(json.dumps(body),{})):
                with self.assertRaises(api.ApiFailure):api.generate('fake','가상','가상',{},'작성')

    def test_valid_evidence_preserves_exact_quote_and_value(self):
        record={'value':'가상 과제','evidence':'가상 과제의 목표','source':'plan'}
        body={'findings':'가상 설명함.','actions':'가상 예정임.','general':{'project':record}}
        with patch('inspection.api.request',return_value=(json.dumps(body),{})):
            result,_=api.generate('fake','가상 과제의 목표','가상 회의',{},'작성')
        self.assertEqual(result['general']['project'],record)
