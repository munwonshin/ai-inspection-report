from dataclasses import replace
from copy import deepcopy
import unittest
import xml.etree.ElementTree as ET
from inspection.core import Report,GENERAL,compose,parse_template,table_cell,cell_text,verify_xml
from inspection.exporter import template_text
from inspection.report_format import DIVISIONS,report_title,valid_document_context,canonical_division

def fixture(division='일반분과',year='2026'):
    g={k:'가상 값' for k in GENERAL};g['visit_date']='2026-11-02'
    return Report('[가상] 저장용_다른파일명',tuple(g.items()),'• 가상 현장 확인함.','• 가상 예정 사항임.','',report_title(year,division))

class ReportHeaderTests(unittest.TestCase):
    def test_annex_banner_removed_and_document_title_not_filename(self):
        report=fixture();xml=compose(template_text(),report);root,ts=parse_template(xml)
        self.assertIsNone(ts[1]);self.assertNotIn('별첨2',''.join(root.itertext()))
        self.assertEqual(cell_text(table_cell(ts[2],0,0)),'2026년 AI바우처 현장점검 결과 (일반분과)')
        self.assertNotIn(report.title,''.join(root.itertext()))
        self.assertEqual(report.as_dict()['title'],'[가상] 저장용_다른파일명')
        self.assertEqual(report.as_dict()['document_title'],report.document_title)
        self.assertEqual(len(list(root.iter('TABLE'))),5)
        verify_xml(xml,report)

    def test_all_four_divisions_and_source_year(self):
        for division in DIVISIONS:
            report=fixture(division,'2025');xml=compose(template_text(),report)
            _,ts=parse_template(xml)
            self.assertEqual(cell_text(table_cell(ts[2],0,0)),f'2025년 AI바우처 현장점검 결과 ({division})')
            verify_xml(xml,report)

    def test_missing_invalid_year_or_division_not_invented(self):
        for year,division in [('', '일반분과'),('2026',''),('26','일반분과'),('2026','임의분과')]:
            self.assertFalse(valid_document_context(year,division))
        for value in ['일반','일반 분과','일반분과']:
            self.assertEqual(canonical_division(value),'일반분과')
            self.assertTrue(valid_document_context('2026',value))

    def test_reintroduced_banner_and_wrong_title_are_rejected(self):
        report=fixture();xml=compose(template_text(),report)
        with self.assertRaises(ValueError):verify_xml(xml.replace(report.document_title,'가상 파일명 오염'),report)
        root,_=parse_template(xml);original,_=parse_template(template_text())
        banner=next(p for p in original.findall('./BODY/SECTION/P') if any('별첨2' in (c.text or '') for c in p.iter('CHAR')))
        root.find('./BODY/SECTION').insert(1,deepcopy(banner))
        with self.assertRaisesRegex(ValueError,'별첨 머리글'):verify_xml(ET.tostring(root,encoding='unicode'),report)

    def test_empty_page_header_table_optional_after_hancom_roundtrip(self):
        report=fixture();root,_=parse_template(compose(template_text(),report))
        parents={child:parent for parent in root.iter() for child in parent}
        for header in list(root.iter('HEADER')):parents[header].remove(header)
        xml=ET.tostring(root,encoding='unicode');self.assertEqual(len(list(root.iter('TABLE'))),4)
        verify_xml(xml,report)

if __name__=='__main__':unittest.main()
