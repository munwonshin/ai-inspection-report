import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from inspection import metadata,preferences
from inspection.report_format import visit_date,parse_visit_date,report_title
from inspection.core import Report,GENERAL,targets

def record(value,quote,page=1):return {'value':value,'evidence':quote,'page':page,'source':'plan','reason':''}

class DivisionDateChecks(unittest.TestCase):
    def test_year_division_require_quote_and_page(self):
        data={'program_year':record('2026','2026년 AI바우처 지원사업'), 'division':record('소상공인 분과','해당 분과: 소상공인 분과')}
        values=metadata.accepted_general(data,2)
        self.assertEqual(values,{'program_year':'2026','division':'소상공인분과'})
        for raw in ['소상공인','소상공인분과']:
            split=metadata.accepted_general({'division':record(raw,'분과: 소상공인')},1)
            self.assertEqual(split['division'],'소상공인분과')
        self.assertEqual(report_title(values['program_year'],values['division']),'2026년 AI바우처 현장점검 결과 (소상공인분과)')
        for key,item in [('program_year',record('2026','2025년 지원사업')),('division',record('일반분과','소상공인분과')),('division',record('일반분과','일반분과',page=99))]:
            self.assertNotIn(key,metadata.accepted_general({key:item},2))

    def test_missing_or_invalid_facts_are_not_invented(self):
        self.assertEqual(report_title('','일반분과'),'AI바우처 현장점검 결과 (일반분과)')
        self.assertEqual(report_title('2025',''),'2025년 AI바우처 현장점검 결과')
        for item in [record('소상공인','소상공인'),record('일반/악성분과','일반/악성분과')]:
            self.assertNotIn('division',metadata.accepted_general({'division':item},1))
        self.assertNotIn('program_year',metadata.accepted_general({'program_year':record('26','26년')},1))

    def test_title_fields_are_extracted_with_general_in_one_original_pdf_call(self):
        fields=('project',)+metadata.TITLE_FIELDS
        data={'project':record('가상 사업','과제명: 가상 사업'),'program_year':record('2026','2026년 지원사업'),'division':record('소상공인분과','소상공인분과 수행계획서')}
        with patch('inspection.api.request',return_value=(json.dumps(data),{})) as request:
            values,_=metadata.extract('synthetic',b'%PDF-SYNTHETIC',1,fields)
        self.assertEqual(len(request.call_args.args[1]['input'][0]['content']),1)
        self.assertEqual(request.call_args.args[1]['text']['format']['schema']['required'],list(fields))
        self.assertEqual(values['division'],'소상공인분과')

    def test_visit_date_matches_form_without_inventing_unknown_dates(self):
        for value in ['2026-10-16','2026년 10월 16일','26년 10월 16일','2026.10.16.']:
            self.assertEqual(visit_date(value),'2026년 10월 16일')
        self.assertEqual(visit_date('2024-02-29'),'2024년 2월 29일')
        self.assertIsNone(parse_visit_date('2026-02-30'))
        self.assertEqual(visit_date('방문일 미정'),'방문일 미정')
        general={k:'가상' for k in GENERAL};general['visit_date']='2026-10-16'
        report=Report('가상 제목',tuple(general.items()),'가상 확인','가상 예정','')
        self.assertIn((5,0,1,'2026년 10월 16일'),targets([],report))

    def test_old_visit_org_pin_migrates_without_losing_inspector_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'preferences.json'
            path.write_text(json.dumps({'version':1,'pinned':{'visit_org':'가상 과거 방문기관','inspector_org':'가상 소속','inspector':'가상 점검자'}}),encoding='utf-8')
            self.assertEqual(preferences.load(path),{'inspector_org':'가상 소속','inspector':'가상 점검자'})
            self.assertNotIn('visit_org',json.loads(path.read_text(encoding='utf-8'))['pinned'])
