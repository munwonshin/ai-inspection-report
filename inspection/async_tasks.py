"""Tk job dispatch/polling, retaining the existing generation and streaming gates."""
import queue,threading,time
from tkinter import messagebox
from .streaming import preview

class AsyncTasks:
    def background(self,fn,done,status):
        if self.busy:return
        self._job_sequence+=1;job=self._job_sequence;self._active_job=job
        self.lock(True);self.status.set(status)
        def execute():
            try:self.mailbox.put((job,done,True,fn()))
            except Exception as e:self.mailbox.put((job,done,False,e))
        threading.Thread(target=execute,daemon=False).start()

    def set_status(self,text):
        # Avoid firing Tk traces and rewriting labels on every idle animation tick.
        if self.status.get()!=text:self.status.set(text)

    def poll(self):
        if self.metadata_started is not None:
            self.set_status(f'일반현황 읽는 중 · {int(time.monotonic()-self.metadata_started)}초')
        if self.ai_started is not None and self.pending_request is not None:
            chunks=[]
            try:
                while True:chunks.append(self.stream_queue.get_nowait())
            except queue.Empty:pass
            if chunks:
                self.stream_json+="".join(chunks)
                self.stream_target=preview(self.stream_json)
            target=self.stream_target
            # Short paced batches follow actual network data; never invent text.
            gap=len(target)-len(self.stream_visible)
            self.stream_visible=target[:len(self.stream_visible)+max(1,min(500,gap//4))]
            self.set_status('')
            self.render_stream()
        latest=None
        try:
            while True:latest=self.pdf_progress.get_nowait()
        except queue.Empty:pass
        if latest is not None and self.busy:
            self.set_status(f'문서 읽는 중 · {latest[0]}/{latest[1]}')
        try:
            job,done,ok,result=self.mailbox.get_nowait()
            if job!=self._active_job:pass
            elif ok and self.ai_started is not None and self.stream_visible!=self.stream_target:
                # Keep the approval gate closed while the last received characters
                # drain, avoiding a final jump from a partial to the entire report.
                self.mailbox.put((job,done,ok,result))
            else:
                self._active_job=None
                self.ai_started=None
                self.lock(False)
                if ok:done(result)
                else:
                    if self.pending_request is not None:
                        self.pending_request['status']='failed';self.pending_request=None;self.render_conversation(follow=True)
                    self.set_status('처리에 실패했습니다. 입력·편집 내용은 유지됩니다.')
                    messagebox.showerror('처리 실패',self.safe_error(result),parent=self.root)
                # Editors/history own the report; release animation-only copies.
                self.stream_json="";self.stream_target="";self.stream_visible=""
                self._stream_rendered=None
        except queue.Empty:pass
        self.root.after(40 if self.ai_started is not None else 120,self.poll)

