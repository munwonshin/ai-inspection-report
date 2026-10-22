import json,unittest
from unittest.mock import patch
from inspection import api,exporter
from inspection.core import Report,GENERAL,compose,parse_template,table_cell,cell_text,verify_xml
from inspection.streaming import preview

class FollowupTests(unittest.TestCase):
    def test_two_body_fields_without_confirmation_section(self):
        self.assertEqual(set(api.schema([])['properties']),{'findings','actions'})
        self.assertEqual(set(api.schema([])['required']),{'findings','actions'})

    def test_legacy_confirmation_and_manual_edits_survive_current_context(self):
        current={'findings':'직접 편집함.','actions':'보관 방법을 안내함.','checks':'일정 확인 필요함.'}
        payload=api.build_payload('배경 목표','회의 기록',current,'문체 수정',revision=True)
        transmitted=json.loads(payload['input'][1]['content'].split(':',1)[1])
        self.assertEqual(transmitted['actions'],'보관 방법을 안내함.\n\n일정 확인 필요함.')
        self.assertNotIn('checks',transmitted)
        self.assertEqual(current['checks'],'일정 확인 필요함.')

    def test_unified_followup_exactly_reaches_template_without_added_headings(self):
        text='로그 양식을 안내함.\n\n제출을 요청함. 일정 확인 필요함.'
        report=Report('가상 시험',tuple((k,'가상 값') for k in GENERAL),'가상 설명임.',text,'')
        xml=compose(exporter.template_text(),report);verify_xml(xml,report)
        _,tables=parse_template(xml)
        self.assertEqual(cell_text(table_cell(tables[4],2,1)),text)
        self.assertNotIn('확인할 사항',cell_text(table_cell(tables[4],2,1)))

    def test_legacy_confirmation_export_keeps_text_without_section_label(self):
        report=Report('가상 시험',tuple((k,'가상 값') for k in GENERAL),'가상 설명임.','가상 안내함.','가상 일정 확인 필요함.')
        _,tables=parse_template(compose(exporter.template_text(),report))
        self.assertEqual(cell_text(table_cell(tables[4],2,1)),'가상 안내함.\n\n가상 일정 확인 필요함.')

    def test_new_response_without_checks_is_accepted_and_invalid_body_rejected(self):
        for actions,valid in [('가상 안내함.',True),(None,False)]:
            body={'findings':'가상 설명임.','actions':actions}
            with patch('inspection.api.request',return_value=(json.dumps(body),{})):
                if valid:
                    result,_=api.generate('fake','가상 계획','가상 회의',{},'작성')
                    self.assertEqual(result['checks'],'')
                else:
                    with self.assertRaises(api.ApiFailure):api.generate('fake','가상 계획','가상 회의',{},'작성')

    def test_stream_has_only_two_headings_for_new_schema(self):
        text=json.dumps({'findings':'가상 설명함.','actions':'가상 안내함. 일정 확인 필요함.'},ensure_ascii=False)
        result=preview(text)
        self.assertIn('향후 조치요청 사항\n가상 안내함. 일정 확인 필요함.',result)
        self.assertNotIn('확인할 사항',result)

if __name__=='__main__':unittest.main()
