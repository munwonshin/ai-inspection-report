import unittest
from inspection.core import compose,verify_xml,parse_template,table_cell,spaced_body
from inspection.exporter import template_text
from tests.test_core import fixture
class BodySpacing(unittest.TestCase):
    def test_sentences_and_numbers(self):
        self.assertEqual(spaced_body('확인함. 예정임.'),'확인함.\n\n예정임.')
        self.assertEqual(spaced_body('수치 3.14를 확인함.\n\n• 후속 시험 예정임.'),'수치 3.14를 확인함.\n\n• 후속 시험 예정임.')
    def test_font_spacing_and_tamper(self):
        xml=compose(template_text(),fixture());verify_xml(xml,fixture())
        root,tables=parse_template(xml)
        chars={x.get('Id'):x for x in root.iter('CHARSHAPE')}
        for row in (1,2):
            for text in table_cell(tables[4],row,1).iter('TEXT'):
                self.assertEqual(chars[text.get('CharShape')].get('Height'),'1000')
        with self.assertRaises(ValueError):verify_xml(xml.replace('Height="1000"','Height="1100"'),fixture())
