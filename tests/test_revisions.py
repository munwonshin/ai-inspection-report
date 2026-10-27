import unittest,copy
from inspection.core import Report
from inspection.revisions import DraftHistory,restore_intent,validate_revision

class RevisionChecks(unittest.TestCase):
    def setUp(self):
        self.before={'findings':'• [가상 검증 자료] 센서 3대 설명함.\n\n• 검수 메모: 확인하지 않았음.','actions':'• 시험 예정임.'}
    def result(self,**kw):return dict(self.before,decision='applied',notice='',**kw)
    def test_blocked_never_replaces_any_body(self):
        r=validate_revision({'findings':'임의 삭제','actions':'99% 완료','decision':'blocked','notice':'자료에 없는 성과는 반영할 수 없습니다.'},self.before,'99% 성과 추가')
        self.assertEqual(r['findings'],self.before['findings']);self.assertEqual(r['actions'],self.before['actions']);self.assertTrue(r['_blocked']);self.assertIn('성과',r['_notice'])
    def test_unrequested_marker_loss_keeps_whole_draft(self):
        data=self.result();data['findings']=data['findings'].replace('검수 메모: ','')
        r=validate_revision(data,self.before,'전체를 간결하게 정리해 주세요.')
        self.assertTrue(r['_blocked']);self.assertEqual(r['findings'],self.before['findings'])
    def test_synthetic_marker_is_preserved(self):
        data=self.result();data['findings']=data['findings'].replace('[가상 검증 자료] ','')
        self.assertTrue(validate_revision(data,self.before,'간결하게 해주세요.').get('_blocked'))
    def test_explicit_memo_delete_is_allowed(self):
        data=self.result();data['findings']=data['findings'].split('\n\n')[0]
        self.assertNotIn('_blocked',validate_revision(data,self.before,'검수 메모 문단만 삭제해 주세요.'))
    def test_numbering_does_not_look_like_memo_change(self):
        data=self.result();data['findings']=data['findings'].replace('• [','1. [').replace('• 검수','2. 검수')
        self.assertNotIn('_blocked',validate_revision(data,self.before,'번호로 바꿔 주세요.'))
    def test_explicit_style_can_change_memo_ending(self):
        data=self.result();data['findings']=data['findings'].replace('않았음.','않았습니다.')
        self.assertNotIn('_blocked',validate_revision(data,self.before,'현장 사항만 존댓말 문체로 바꾸세요.'))
    def test_scope_guard_prevents_unrelated_section_changes(self):
        data=self.result();data['actions']='관계없는 변경'
        self.assertTrue(validate_revision(data,self.before,'현장 확인 사항만 간결하게 정리해 주세요.').get('_blocked'))
    def test_history_exact_repeated_undo_and_manual_edit(self):
        h=DraftHistory();a=Report('제목',(),'원본\n\n검수 메모: A','후속','');b=Report('제목',(),'수정 B','후속','');d=Report('제목',(),'직접 편집 C','후속','')
        h.record(a);h.record(b)
        self.assertEqual(h.restore(d),b);self.assertEqual(h.restore(b),a);self.assertIsNone(h.restore(a))
    def test_history_keeps_current_metadata_and_scoped_other_body(self):
        h=DraftHistory();a=Report('옛 제목',(),'과거','옛 향후','');b=Report('현재 제목',(),'현재','현재 향후','')
        h.record(a)
        r=h.restore(b,fields=('findings',));self.assertEqual((r.title,r.findings,r.actions),('현재 제목','과거','현재 향후'))
    def test_restore_intent_rejects_mixed_edits(self):
        self.assertIsNotNone(restore_intent('방금 수정한 내용을 수정 전으로 되돌려 주세요.'))
        self.assertIsNone(restore_intent('이전으로 되돌리고 문체도 바꾸세요.'))
        self.assertEqual(restore_intent('현장 점검 내용을 수정 전으로 되돌리고 향후 사항은 그대로 유지해 주세요.')['fields'],('findings',))
    def test_invalid_revision_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):validate_revision({'findings':'본문','actions':'후속'},self.before,'수정')
