"""User approval and immutable review snapshot to the exporter boundary."""
from tkinter import messagebox
from . import exporter
from .core import destination,GENERAL
from .report_format import valid_document_context

class SaveFlow:
    def approve(self):
        if self.busy:return
        if not self.title.get().strip() or not self.get(self.findings).strip():
            messagebox.showinfo('입력 확인','저장 파일명과 현장 점검 본문을 입력해 주세요.',parent=self.root);return
        if not valid_document_context(self.report_context.get('program_year',''),self.report_context.get('division','')):
            if not self.general_expanded:self.toggle_general()
            key='program_year' if not valid_document_context(self.report_context.get('program_year',''),'일반분과') else 'division'
            entry=self.document_context_entries[key];self.root.update_idletasks();self.reveal_general(entry);entry.focus_set()
            messagebox.showinfo('문서 제목 확인','일반현황에서 사업연도와 분과를 확인해 주세요. 문서 제목은 이 값으로 생성하며 저장 파일명과 분리합니다.',parent=self.root);return
        # Pick a destination only when needed; cancellation leaves all inputs intact.
        if not self.folder.get().strip():
            self.choose_folder()
            if not self.folder.get().strip():return
        try:destination(self.folder.get(),self.name.get())
        except ValueError as e:messagebox.showerror('저장 설정',str(e),parent=self.root);return
        missing=[k for k in GENERAL if not self.general[k].get().strip()]
        if missing and not self.missing_dialog(missing):return
        self.refresh_review()
        if not self.review_state.allowed:
            messagebox.showinfo('자료 재검수 필요',self.review_state.reason+' 현재 자료 대조·검토 완료를 선택한 뒤 승인해 주세요.',parent=self.root);return
        self.sync_latest_report();self.render_conversation()
        snapshot=self.snapshot();folder=self.folder.get();name=self.name.get()
        approval_token=self.review_state.token
        # A failed repeat save must not retain the previous attempt's success UI.
        # Keep the report and last successful path; only done() may mark success.
        self.saved_current=False
        self.open_file.configure(state='disabled');self.open_folder.configure(state='disabled')
        def done(result):
            self.last_saved=result['path']
            self.saved_current=True
            self.open_file.configure(state='normal');self.open_folder.configure(state='normal')
            self.status.set('저장했습니다.')
        def task():
            if approval_token!=self.review_state.token or not self.review_state.allowed:
                raise ValueError('승인 대상이 변경되었습니다. 현재 자료를 다시 재검수해 주세요.')
            return exporter.save(snapshot,folder,name,approved=True)
        self.background(task,done,
            '한글 파일을 저장하고 있습니다.')

