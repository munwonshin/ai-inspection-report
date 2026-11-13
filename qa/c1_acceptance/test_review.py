import unittest
from dataclasses import replace
from inspection.core import Report
from inspection.documents import PreparedDocument
from inspection.review import ReviewState, prepared_identity


class ReviewUnitTests(unittest.TestCase):
    def setUp(self):
        self.report = Report('filename', (('project', 'synthetic'),), 'body', 'actions', '', '2026 일반분과')
        self.state = ReviewState()
        self.state.observe('A', 'minutes', self.report)

    def test_file_name_does_not_invalidate_review(self):
        self.state.accept('REVIEWED')
        self.state.observe('A', 'minutes', replace(self.report, title='other filename'))
        self.assertTrue(self.state.allowed)

    def test_all_report_content_and_context_invalidate(self):
        for change in ({'findings': 'new body'}, {'actions': 'new action'},
                       {'general': (('project', 'other'),)}, {'document_title': '2025 일반분과'}):
            with self.subTest(change=change):
                state = ReviewState()
                state.observe('A', 'minutes', self.report)
                state.accept('REVIEWED')
                state.observe('A', 'minutes', replace(self.report, **change))
                self.assertFalse(state.allowed)

    def test_line_endings_only_are_normalized(self):
        self.state.observe('A', 'a\r\nb\r', self.report)
        self.state.accept('REVIEWED')
        self.state.observe('A', 'a\nb\n', self.report)
        self.assertTrue(self.state.allowed)
        self.state.observe('A', 'a \nb\n', self.report)
        self.assertFalse(self.state.allowed)

    def test_a_b_a_does_not_revalidate_old_response(self):
        old = self.state.token
        self.state.accept('CURRENT')
        self.state.observe('B', 'minutes', self.report)
        self.state.observe('A', 'minutes', self.report)
        self.assertNotEqual(old, self.state.token)
        self.assertFalse(self.state.allowed)

    def test_reset_does_not_revalidate_old_response(self):
        old = self.state.token
        self.state.reset()
        self.state.observe('A', 'minutes', self.report)
        self.assertNotEqual(old, self.state.token)
        self.assertFalse(self.state.allowed)

    def test_explicit_restore_invalidates_identical_content_and_old_response(self):
        old = self.state.token
        self.state.accept('REVIEWED')
        self.state.invalidate('restored')
        self.assertNotEqual(old, self.state.token)
        self.assertFalse(self.state.allowed)

    def test_reverting_an_edit_does_not_restore_review(self):
        self.state.accept('REVIEWED')
        self.state.observe('A', 'minutes', replace(self.report, findings='new'))
        self.state.observe('A', 'minutes', self.report)
        self.assertFalse(self.state.allowed)

    def test_processed_identity_covers_all_input_fields(self):
        doc = PreparedDocument('local', 'api', b'%PDF-A', 1, (1,), b'%PDF-A')
        key = prepared_identity(doc)
        for change in ({'local_text': 'other'}, {'api_text': 'other'}, {'visual_pdf': b'%PDF-B'},
                       {'page_count': 2}, {'visual_pages': ()}, {'original_bytes': b'%PDF-B'}):
            with self.subTest(change=change):
                self.assertNotEqual(key, prepared_identity(replace(doc, **change)))
        self.assertEqual(key, prepared_identity(replace(doc)))

    def test_image_packet_identity_is_order_independent_for_dict_keys(self):
        a = PreparedDocument('a', 'a', ({'type': 'input_image', 'image_url': 'synthetic'},), 1, (), b'HWP-TEXT\x00a')
        b = replace(a, visual_pdf=({'image_url': 'synthetic', 'type': 'input_image'},))
        self.assertEqual(prepared_identity(a), prepared_identity(b))


if __name__ == '__main__':
    unittest.main()
