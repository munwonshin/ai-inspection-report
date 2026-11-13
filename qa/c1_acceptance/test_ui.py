"""C1 X branches: real Tk/controller, synthetic external boundaries only."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from inspection import api
from qa.c1_baseline.run_baseline import ControllerCase, HERE, create_pdf
from qa.c1_acceptance.adapter import invoke_review_ui


class C1UIAcceptanceTests(unittest.TestCase):
    @contextmanager
    def controller(self, base=True):
        fixtures = json.loads((HERE / 'fixtures.json').read_text(encoding='utf-8'))
        case = json.loads((HERE / 'scenarios.json').read_text(encoding='utf-8'))['cases'][6]
        with tempfile.TemporaryDirectory(dir=os.environ['C1_TEST_TEMP']) as folder:
            controller = ControllerCase(fixtures, case, Path(folder), 'candidate', invoke_review_ui)
            try:
                if base:
                    controller.action({'action': 'base', 'profile': 'A'})
                yield controller
            finally:
                controller.close()

    def blocked(self, c):
        # Reset legitimately clears destination; restore a valid synthetic one
        # so the C1 gate, rather than the folder picker, is what is observed.
        if not c.app.folder.get():
            c.app.folder.set(str(c.default_output))
        before = c.app.snapshot()
        c.app.approve()
        c.settle()
        self.assertEqual(c.exports, [])
        self.assertEqual(c.app.snapshot(), before)
        self.assertEqual(c.dialogs[-1]['title'], '자료 재검수 필요')

    def reviewed(self, c):
        invoke_review_ui(c.app)
        c.settle()
        self.assertEqual(c.app.review_note.get(), '현재 자료 대조·검토 완료')

    def test_X01_partial_applied_blocked_and_error_never_clear_stale_source(self):
        for decision in ('applied', 'blocked', 'error'):
            with self.subTest(decision=decision), self.controller() as c:
                c.action({'action': 'attach', 'profile': 'B'})
                c.general('B')
                before = c.app.snapshot()
                response = {'findings': before.findings + ('\n가상 추가 표현임.' if decision == 'applied' else ''),
                            'actions': before.actions, 'decision': decision, 'notice': ''}
                effect = api.ApiFailure('Synthetic transport failure') if decision == 'error' else None
                with patch('inspection.ui.api.request', side_effect=effect,
                           return_value=(json.dumps(response, ensure_ascii=False), {})):
                    c.app.connected = True
                    c.app.ai('현장 확인 사항만 문체를 다듬어 주세요.', True)
                    c.settle()
                if decision != 'applied':
                    self.assertEqual(c.app.snapshot(), before)
                self.blocked(c)

    def test_X02_late_full_and_partial_responses_reject_source_and_edit_changes(self):
        for revision in (False, True):
            for mutation in ('source', 'body', 'reset', 'a_b_a'):
                with self.subTest(revision=revision, mutation=mutation), self.controller() as c:
                    pending = []
                    with patch.object(c.app, 'background', side_effect=lambda task, done, status: pending.append((task, done))):
                        c.app.ai('가상 수정 요청', revision)
                    self.assertEqual(len(pending), 1)
                    if mutation in ('source', 'a_b_a'):
                        c.action({'action': 'attach', 'profile': 'B'})
                        c.general('B')
                        if mutation == 'a_b_a':
                            c.action({'action': 'attach', 'profile': 'A'})
                            c.general('A')
                    elif mutation == 'body':
                        c.set_text(c.app.findings, '가상 최신 수동 본문임.')
                    else:
                        c.app.reset_workspace()
                        c.action({'action': 'minutes', 'profile': 'A'})
                        c.general('A')
                        c.action({'action': 'manual_draft', 'profile': 'A'})
                    before = c.app.snapshot()
                    pending[0][1](({'findings': '가상 오래된 응답임.', 'actions': '', 'checks': '', 'general': {}}, {}))
                    self.assertEqual(c.app.snapshot(), before)
                    self.blocked(c)

    def test_X02_late_metadata_rejects_manual_edit_source_and_reset(self):
        for mutation in ('manual', 'source', 'reset'):
            with self.subTest(mutation=mutation), self.controller() as c:
                c.app.general['project'].set('')
                c.app.connected = True
                pending = []
                with patch.object(c.app, 'background', side_effect=lambda task, done, status: pending.append((task, done))):
                    c.app.recognize_general(force=True)
                self.assertEqual(len(pending), 1)
                if mutation == 'source':
                    c.action({'action': 'attach', 'profile': 'B'})
                    c.general('B')
                elif mutation == 'reset':
                    c.app.reset_workspace()
                    c.general('A')
                    c.action({'action': 'manual_draft', 'profile': 'A'})
                else:
                    c.app.general['project'].set('가상 최신 수동 과제')
                before = c.app.snapshot()
                pending[0][1]({'data': ({'project': '가상 오래된 과제'}, {})})
                self.assertEqual(c.app.snapshot(), before)
                self.blocked(c)

    def test_X02_old_job_envelope_cannot_unlock_a_new_task(self):
        with self.controller() as c:
            release = threading.Event()
            completed = []
            c.app.background(lambda: release.wait(5), lambda result: completed.append(result), 'Synthetic pending job')
            try:
                c.app.mailbox.put((c.app._job_sequence - 1, lambda result: self.fail('Obsolete callback applied'), True, None))
                c.app.poll()
                self.assertTrue(c.app.busy)
                self.assertEqual(completed, [])
            finally:
                release.set()
                c.settle()
            self.assertEqual(completed, [True])

    def test_X03_review_cancel_preserves_and_blocks(self):
        with self.controller() as c:
            c.set_text(c.app.findings, '가상 수동 수정 본문임.')
            before = c.app.snapshot()
            with patch('inspection.ui.messagebox.askyesno', return_value=False):
                invoke_review_ui(c.app)
            self.assertEqual(c.app.snapshot(), before)
            self.blocked(c)

    def test_X03_post_review_body_general_and_context_changes_invalidate(self):
        for target in ('findings', 'actions', 'general', 'year', 'division'):
            with self.subTest(target=target), self.controller() as c:
                self.reviewed(c)
                if target in ('findings', 'actions'):
                    c.set_text(getattr(c.app, target), '가상 변경 본문임.')
                elif target == 'general':
                    c.app.general['lead_org'].set('가상 변경기관')
                else:
                    c.app.document_context_vars['program_year' if target == 'year' else 'division'].set('2025' if target == 'year' else '반도체분과')
                self.assertNotEqual(c.app.review_note.get(), '현재 자료 대조·검토 완료')
                self.blocked(c)

    def test_X03_mutation_during_confirmation_does_not_grant_review(self):
        with self.controller() as c:
            def edit_during_confirmation(*args, **kwargs):
                c.set_text(c.app.findings, '가상 확인 도중 변경임.')
                return True
            with patch('inspection.ui.messagebox.askyesno', side_effect=edit_during_confirmation):
                invoke_review_ui(c.app)
            self.blocked(c)

    def test_X04_required_dialog_cancel_and_complete_use_real_widgets(self):
        for accept in (False, True):
            with self.subTest(accept=accept), self.controller(base=False) as c:
                c.general('A')
                c.action({'action': 'manual_draft', 'profile': 'A'})
                c.app.general['lead_org'].set('')
                self.reviewed(c)
                def respond():
                    def descendants(widget):
                        result = []
                        for child in widget.winfo_children():
                            result.append(child)
                            result.extend(descendants(child))
                        return result
                    dialogs = [w for w in c.root.winfo_children() if w.winfo_class() == 'Toplevel' and w.title() == '승인 전 필수값 확인']
                    self.assertEqual(len(dialogs), 1)
                    children = descendants(dialogs[0])
                    if accept:
                        entry = next(w for w in children if w.winfo_class() == 'TEntry')
                        entry.insert(0, '가상 보완기관')
                    button = next(w for w in children if w.winfo_class() == 'TButton' and w.cget('text') == ('확인 후 승인·저장' if accept else '취소'))
                    button.invoke()
                c.root.after(80, respond)
                # Fail with callback evidence instead of hanging on a modal test.
                def watchdog():
                    for widget in c.root.winfo_children():
                        if widget.winfo_class() == 'Toplevel' and widget.title() == '승인 전 필수값 확인':
                            widget.destroy()
                c.root.after(2000, watchdog)
                c.app.approve()
                c.settle()
                self.assertEqual(c.exports, [])
                if accept:
                    self.assertEqual(c.app.general['lead_org'].get(), '가상 보완기관')
                    self.reviewed(c)
                    c.app.approve();c.settle()
                    self.assertEqual(len(c.exports), 1)
                else:
                    self.assertEqual(c.app.general['lead_org'].get(), '')

    def test_X05_reset_success_new_work_and_api_state_preserved(self):
        with self.controller() as c:
            c.app.connected = True
            self.reviewed(c)
            self.assertTrue(c.app.reset_workspace())
            self.assertTrue(c.app.connected)
            self.assertEqual(c.app.pdf_path, '')
            self.assertEqual(c.app.draft_history.versions, [])
            c.action({'action': 'minutes', 'profile': 'A'})
            c.general('A')
            c.action({'action': 'manual_draft', 'profile': 'A'})
            self.blocked(c)
            self.reviewed(c)
            c.app.approve();c.settle()
            self.assertEqual(len(c.exports), 1)

    def test_X05_busy_and_preferences_failure_preserve_work(self):
        with self.controller() as c:
            self.reviewed(c)
            before = c.app.snapshot()
            c.app.lock(True)
            self.assertFalse(c.app.reset_workspace())
            c.app.lock(False)
            self.assertEqual(c.app.snapshot(), before)
            with patch.object(c.app, 'preferences_enabled', True), patch('inspection.ui.preferences.save', side_effect=OSError('synthetic settings failure')):
                self.assertFalse(c.app.reset_workspace())
            self.assertEqual(c.app.snapshot(), before)
            self.assertEqual(c.app.review_note.get(), '현재 자료 대조·검토 완료')

    def test_X06_same_source_restore_requires_fresh_review(self):
        with self.controller() as c:
            self.reviewed(c)
            c.app.sync_latest_report()
            c.set_text(c.app.findings, '가상 최신 수동 수정임.')
            self.reviewed(c)
            c.app.chat.set('최초 초안으로 되돌려 주세요.')
            c.app.send_chat();c.settle()
            self.blocked(c)

    def test_X06_unknown_manual_draft_cannot_be_assumed_reviewed(self):
        with self.controller(base=False) as c:
            c.general('A')
            c.action({'action': 'manual_draft', 'profile': 'A'})
            self.blocked(c)

    def test_X07_line_endings_and_whitespace_have_different_policies(self):
        with self.controller() as c:
            c.set_text(c.app.minutes, '가상 문장\n다음 문장')
            self.reviewed(c)
            c.set_text(c.app.minutes, '가상 문장\r\n다음 문장')
            self.assertEqual(c.app.review_note.get(), '현재 자료 대조·검토 완료')
            c.set_text(c.app.minutes, '가상  문장\n다음 문장')
            self.blocked(c)

    def test_X07_external_file_change_does_not_mutate_loaded_snapshot(self):
        with self.controller() as c:
            self.reviewed(c)
            before = c.app.original_pdf_bytes
            Path(c.app.pdf_path).write_bytes(create_pdf(c.profiles['B']))
            c.settle()
            self.assertEqual(c.app.original_pdf_bytes, before)
            self.assertEqual(c.app.review_note.get(), '현재 자료 대조·검토 완료')
            c.app.approve();c.settle()
            self.assertEqual(len(c.exports), 1)

    def test_X08_unreviewed_gate_does_not_start_export_or_result_io(self):
        with self.controller() as c:
            c.set_text(c.app.findings, '가상 수동 수정임.')
            with patch('inspection.exporter.tempfile.TemporaryDirectory') as stage, patch('inspection.exporter.template_text') as template:
                self.blocked(c)
                stage.assert_not_called();template.assert_not_called()

    def test_X08_save_success_uses_reviewed_snapshot_and_failure_keeps_edits(self):
        for failure in (False, True):
            with self.subTest(failure=failure), self.controller() as c:
                self.reviewed(c)
                snapshot = c.app.snapshot()
                if failure:
                    with patch('inspection.ui.exporter.save', side_effect=RuntimeError('synthetic save failure')):
                        c.app.approve();c.settle()
                    self.assertFalse(c.app.saved_current)
                    self.assertTrue(c.app.open_file.instate(['disabled']))
                else:
                    c.app.approve();c.settle()
                    self.assertEqual(c.exports[0]['report'], snapshot.as_dict())
                    self.assertTrue(c.app.saved_current)
                    self.assertTrue(c.app.open_file.instate(['!disabled']))
                self.assertEqual(c.app.snapshot(), snapshot)

    def test_X08_failed_repeat_save_does_not_keep_success_indicator(self):
        with self.controller() as c:
            self.reviewed(c)
            c.app.approve();c.settle()
            self.assertTrue(c.app.saved_current)
            previous_path = c.app.last_saved
            before = c.app.snapshot()
            # No edit or filename trace between consecutive approval clicks.
            with patch('inspection.ui.exporter.save', side_effect=RuntimeError('same-name collision')):
                c.app.approve();c.settle()
            self.assertFalse(c.app.saved_current)
            self.assertTrue(c.app.open_file.instate(['disabled']))
            self.assertEqual(c.app.last_saved, previous_path)
            self.assertEqual(c.app.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
