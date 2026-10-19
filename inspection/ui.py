import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from . import api, vault, exporter
from .core import Report, GENERAL, extract_pdf, evidenced_general, filename, destination

class App:
    def __init__(self,root):
        self.root=root
        self.plan=''
        self.pdf_path=''
        self.pdf_bytes=None
        self.busy=False
        self.connected=False
        self.last_saved=None
        self.saved_current=False
        self.mailbox=queue.Queue()
        self.edits=[]
        self.buttons=[]
        self.entries=[]
        root.title('AI 현장점검 결과서 · 0.1 검증판')
        root.geometry('1320x900')
        root.minsize(1060,720)
        root.configure(bg='#eef2f6')
        root.option_add('*Font',('맑은 고딕',10))
        style=ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame',background='#eef2f6')
        style.configure('TLabel',background='#eef2f6',foreground='#22354a')
        style.configure('TLabelframe',background='#eef2f6')
        style.configure('TLabelframe.Label',background='#eef2f6',foreground='#22354a')
        style.configure('TButton',padding=(10,6))
        style.configure('Primary.TButton',background='#174f82',foreground='white',font=('맑은 고딕',10,'bold'))
        outer=ttk.Frame(root,padding=16);outer.pack(fill='both',expand=True)
        header=ttk.Frame(outer);header.pack(fill='x')
        ttk.Label(header,text='AI 현장점검 결과서',font=('맑은 고딕',19,'bold')).pack(side='left')
        self.button(header,'API 설정',self.settings).pack(side='right')
        ttk.Label(outer,text='자료 입력 → 초안 작성·편집 → 승인 및 한글 저장   |   승인 전에는 결과파일을 만들지 않습니다.').pack(anchor='w',pady=(4,12))
        options=ttk.Frame(outer);options.pack(fill='x',pady=(0,10))
        options.columnconfigure(1,weight=2);options.columnconfigure(3,weight=2)
        self.title=tk.StringVar(value='현장점검 결과서')
        self.name=tk.StringVar()
        self.folder=tk.StringVar()
        ttk.Label(options,text='결과서 제목').grid(row=0,column=0,sticky='w',padx=(0,8))
        self.entry(options,self.title).grid(row=0,column=1,sticky='ew',padx=(0,14))
        ttk.Label(options,text='파일명 (.hwp)').grid(row=0,column=2,sticky='w',padx=(0,8))
        self.entry(options,self.name).grid(row=0,column=3,sticky='ew')
        ttk.Label(options,text='저장 폴더').grid(row=1,column=0,sticky='w',pady=(7,0))
        self.entry(options,self.folder).grid(row=1,column=1,columnspan=3,sticky='ew',pady=(7,0),padx=(0,100))
        self.button(options,'폴더 선택',self.choose_folder).grid(row=1,column=3,sticky='e',pady=(7,0))
        panes=ttk.Panedwindow(outer,orient='horizontal');panes.pack(fill='both',expand=True)
        left=ttk.Frame(panes,padding=(0,0,12,0));right=ttk.Frame(panes,padding=(10,0,0,0))
        panes.add(left,weight=4);panes.add(right,weight=7)
        left.columnconfigure(0,weight=1);left.rowconfigure(3,weight=1)
        pdfbar=ttk.Frame(left);pdfbar.grid(row=0,column=0,sticky='ew')
        ttk.Label(pdfbar,text='사업계획서 PDF',font=('맑은 고딕',11,'bold')).pack(side='left')
        self.button(pdfbar,'PDF 첨부',self.attach).pack(side='right')
        self.pdf_label=tk.StringVar(value='첨부된 PDF 없음 · 전체 PDF를 AI가 확인합니다')
        ttk.Label(left,textvariable=self.pdf_label,wraplength=400).grid(row=1,column=0,sticky='w',pady=(4,9))
        ttk.Label(left,text='회의록 · 현장 진행상황과 확인·안내 내용을 입력하세요',font=('맑은 고딕',10,'bold')).grid(row=2,column=0,sticky='w')
        self.minutes=self.textbox(left,3,height=8)
        meta=ttk.LabelFrame(left,text='일반현황 · 자료 확인값만 자동 채움',padding=8)
        meta.grid(row=4,column=0,sticky='ew',pady=(10,0));meta.columnconfigure(1,weight=1)
        self.general={}
        for i,(k,label) in enumerate(GENERAL.items()):
            self.general[k]=tk.StringVar()
            ttk.Label(meta,text=label).grid(row=i,column=0,sticky='w',padx=(0,8),pady=2)
            self.entry(meta,self.general[k]).grid(row=i,column=1,sticky='ew',pady=2)
        ttk.Label(left,text='빈 필수값은 승인 전에 입력합니다. 해당하지 않으면 ‘해당 없음’으로 확인하세요.',wraplength=410).grid(row=5,column=0,sticky='w',pady=(5,0))
        right.columnconfigure(0,weight=1)
        for row,weight in [(2,5),(4,2),(6,1)]:right.rowconfigure(row,weight=weight)
        draftbar=ttk.Frame(right);draftbar.grid(row=0,column=0,sticky='ew',pady=(0,5))
        ttk.Label(draftbar,text='직접 편집 가능한 초안',font=('맑은 고딕',12,'bold')).pack(side='left')
        self.button(draftbar,'초안 작성',self.draft,primary=True).pack(side='right')
        ttk.Label(right,text='현장 점검 / 확인 사항').grid(row=1,column=0,sticky='w')
        self.findings=self.textbox(right,2,height=9)
        ttk.Label(right,text='향후 조치요청 사항 · 회의록에 근거한 내용만 작성').grid(row=3,column=0,sticky='w',pady=(6,0))
        self.actions=self.textbox(right,4,height=4)
        ttk.Label(right,text='확인할 사항 · 본문과 분리').grid(row=5,column=0,sticky='w',pady=(6,0))
        self.checks=self.textbox(right,6,height=3)
        chat=ttk.Frame(right);chat.grid(row=7,column=0,sticky='ew',pady=(8,0));chat.columnconfigure(0,weight=1)
        self.chat=tk.StringVar()
        self.chat_entry=self.entry(chat,self.chat)
        self.chat_entry.grid(row=0,column=0,sticky='ew',padx=(0,6))
        self.chat_entry.bind('<Return>',lambda e:self.revise())
        self.button(chat,'채팅 수정',self.revise).grid(row=0,column=1)
        self.chat_info=tk.StringVar(value='수정 요청을 입력하세요. 원본 자료와 지금 편집한 초안을 함께 반영합니다.')
        ttk.Label(right,textvariable=self.chat_info,wraplength=650).grid(row=8,column=0,sticky='w',pady=(4,0))
        ttk.Label(outer,text='외부 전송: PDF 전체·회의록·현재 초안·수정 요청 → OpenAI API  |  PDF 이미지·텍스트 토큰별 과금 · ChatGPT 구독과 별도',wraplength=1240).pack(anchor='w',pady=(10,6))
        footer=ttk.Frame(outer);footer.pack(fill='x')
        self.status=tk.StringVar(value='자료를 입력해 주세요. 편집 내용은 메모리에만 유지됩니다.')
        ttk.Label(footer,textvariable=self.status,wraplength=760).pack(side='left',fill='x',expand=True)
        self.open_file=self.button(footer,'파일 열기',self.open_saved);self.open_file.pack(side='right',padx=4)
        self.open_folder=self.button(footer,'폴더 열기',self.open_saved_folder);self.open_folder.pack(side='right',padx=4)
        self.button(footer,'승인 및 한글 저장',self.approve,primary=True).pack(side='right',padx=4)
        self.open_file.configure(state='disabled');self.open_folder.configure(state='disabled')
        for v in [self.title,self.name,self.folder,*self.general.values()]:v.trace_add('write',lambda *a:self.changed())
        for text in self.edits:
            text.bind('<<Modified>>',lambda e:self.text_changed(e.widget))
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(120,self.poll)

    def entry(self,parent,var):
        e=ttk.Entry(parent,textvariable=var);self.entries.append(e);return e

    def button(self,parent,text,fn,primary=False):
        b=ttk.Button(parent,text=text,command=fn,style='Primary.TButton' if primary else 'TButton');self.buttons.append(b);return b

    def textbox(self,parent,row,height):
        f=ttk.Frame(parent);f.grid(row=row,column=0,sticky='nsew',pady=(3,0))
        t=tk.Text(f,wrap='word',undo=True,height=height,width=30,relief='solid',borderwidth=1,
            padx=9,pady=7,bg='white',fg='#172c42',insertbackground='#174f82')
        s=ttk.Scrollbar(f,command=t.yview);t.configure(yscrollcommand=s.set)
        t.pack(side='left',fill='both',expand=True);s.pack(side='right',fill='y')
        self.edits.append(t);return t

    def text_changed(self,t):
        if t.edit_modified():self.changed();t.edit_modified(False)

    def changed(self):
        self.saved_current=False
        if hasattr(self,'open_file') and self.last_saved:
            self.open_file.configure(state='disabled');self.open_folder.configure(state='disabled')
            if not self.busy:self.status.set('편집 내용이 변경됐습니다. 다시 승인·저장해야 변경 내용이 파일에 반영됩니다.')

    def get(self,t):return t.get('1.0','end-1c')

    def snapshot(self):
        return Report(self.title.get(),tuple((k,v.get()) for k,v in self.general.items()),
            self.get(self.findings),self.get(self.actions),self.get(self.checks))

    def lock(self,value):
        self.busy=value
        for e in self.entries+self.edits+self.buttons:e.configure(state='disabled' if value else 'normal')
        if not value and not self.saved_current:
            self.open_file.configure(state='disabled');self.open_folder.configure(state='disabled')

    def background(self,fn,done,status):
        if self.busy:return
        self.lock(True);self.status.set(status)
        def execute():
            try:self.mailbox.put((done,True,fn()))
            except Exception as e:self.mailbox.put((done,False,e))
        threading.Thread(target=execute,daemon=False).start()

    def poll(self):
        try:
            done,ok,result=self.mailbox.get_nowait()
            self.lock(False)
            if ok:done(result)
            else:
                self.status.set('처리에 실패했습니다. 입력·편집 내용은 유지됩니다.')
                messagebox.showerror('처리 실패',self.safe_error(result),parent=self.root)
        except queue.Empty:pass
        self.root.after(120,self.poll)

    def safe_error(self,e):
        if isinstance(e,(ValueError,RuntimeError,api.ApiFailure,PermissionError)):return str(e)
        return '작업을 완료하지 못했습니다. 파일·네트워크·접근 권한을 확인해 주세요. 입력 내용은 유지됩니다.'

    def choose_folder(self):
        p=filedialog.askdirectory(parent=self.root,title='저장 폴더 선택 · 로컬 또는 NAS')
        if p:self.folder.set(p)

    def attach(self):
        p=filedialog.askopenfilename(parent=self.root,title='사업계획서 PDF',filetypes=[('PDF','*.pdf')])
        if not p:return
        def done(result):
            self.plan,pages,self.pdf_bytes=result;self.pdf_path=p
            self.pdf_label.set(f'{Path(p).name} · {pages}쪽 · 작성 시 PDF 전체 전송')
            self.status.set('PDF를 읽었습니다. 회의록을 입력한 뒤 초안을 작성하세요.')
        self.background(lambda:extract_pdf(p),done,'PDF 구조와 일반현황 확인용 텍스트를 읽고 있습니다. 지금은 외부 전송하지 않습니다.')

    def ready(self):
        if not self.connected:
            messagebox.showinfo('API 연결 확인','API 설정에서 키를 저장하고 연결 확인을 먼저 해 주세요.',parent=self.root);return False
        if not self.plan or not self.get(self.minutes).strip():
            messagebox.showinfo('자료 확인','사업계획서 PDF와 회의록이 모두 필요합니다.',parent=self.root);return False
        return True

    def draft(self):
        if self.busy or not self.ready():return
        if self.get(self.findings).strip() and not messagebox.askyesno('초안 다시 작성','현재 편집 초안을 새 초안으로 바꿀까요? 기존 내용을 유지하며 고치려면 채팅 수정을 사용하세요.',parent=self.root):return
        self.ai('원본 자료에 근거하여 현장점검 결과서 초안을 작성해 주세요.',False)

    def revise(self):
        if self.busy or not self.ready():return
        if not self.get(self.findings).strip():
            messagebox.showinfo('초안 확인','먼저 초안을 작성하거나 직접 입력해 주세요.',parent=self.root);return
        if not self.chat.get().strip():return
        self.ai(self.chat.get().strip(),True)

    def ai(self,instruction,is_chat):
        current=self.snapshot().as_dict()
        plan=self.plan;minutes=self.get(self.minutes)
        def task():
            key=vault.read()
            if not key:raise ValueError('저장된 API 키가 없습니다.')
            return api.generate(key,plan,minutes,current,instruction,pdf_bytes=self.pdf_bytes)
        def done(data):
            result,usage=data
            for t,k in [(self.findings,'findings'),(self.actions,'actions'),(self.checks,'checks')]:
                t.delete('1.0','end');t.insert('1.0',result[k]);t.edit_modified(False)
            for k,v in evidenced_general(result['general'],plan,minutes).items():
                if not self.general[k].get().strip():self.general[k].set(v)
            self.changed()
            tokens=usage.get('total_tokens','확인 불가')
            self.status.set(f'초안 반영 완료 · {api.MODEL} · 이번 요청 {tokens} 토큰 · 아직 파일로 저장되지 않았습니다.')
            if is_chat:self.chat_info.set('마지막 수정: '+instruction[:100]);self.chat.set('')
        self.background(task,done,'OpenAI에서 작성 중입니다. 화면 입력은 잠시 잠기며 기존 내용은 유지됩니다.')

    def missing_dialog(self,missing):
        w=tk.Toplevel(self.root);w.title('승인 전 필수값 확인');w.transient(self.root);w.grab_set()
        f=ttk.Frame(w,padding=18);f.pack(fill='both',expand=True)
        ttk.Label(f,text='자료에서 확인되지 않은 필수값만 입력해 주세요.\n해당하지 않으면 ‘해당 없음’으로 확인하세요.').grid(row=0,column=0,columnspan=2,pady=(0,10))
        values={};accepted=[]
        for i,k in enumerate(missing,1):
            ttk.Label(f,text=GENERAL[k]).grid(row=i,column=0,sticky='w',padx=(0,10),pady=3)
            values[k]=tk.StringVar();ttk.Entry(f,textvariable=values[k],width=36).grid(row=i,column=1,pady=3)
        def accept():
            if any(not v.get().strip() for v in values.values()):
                messagebox.showinfo('입력 확인','빈 값을 모두 확인해 주세요.',parent=w);return
            for k,v in values.items():self.general[k].set(v.get().strip())
            accepted.append(True);w.destroy()
        ttk.Button(f,text='입력 확인 후 승인 저장',command=accept).grid(row=len(missing)+1,column=1,sticky='e',pady=(12,0))
        self.root.wait_window(w);return bool(accepted)

    def approve(self):
        if self.busy:return
        if not self.title.get().strip() or not self.get(self.findings).strip():
            messagebox.showinfo('입력 확인','결과서 제목과 현장 점검 본문을 입력해 주세요.',parent=self.root);return
        try:destination(self.folder.get(),self.name.get())
        except ValueError as e:messagebox.showerror('저장 설정',str(e),parent=self.root);return
        missing=[k for k in GENERAL if not self.general[k].get().strip()]
        if missing and not self.missing_dialog(missing):return
        snapshot=self.snapshot();folder=self.folder.get();name=self.name.get()
        def done(result):
            self.last_saved=result['path']
            self.saved_current=True
            self.open_file.configure(state='normal');self.open_folder.configure(state='normal')
            self.status.set(f'저장·한글 재열기 검증 완료 · {result["pages"]}쪽 · {result["path"]}')
        self.background(lambda:exporter.save(snapshot,folder,name,approved=True),done,
            '승인된 내용을 한글에 저장·재열기 검증 중입니다. 한글 접근 확인 창이 뜨면 직접 확인해 주세요.')

    def open_saved(self):
        if self.last_saved:
            try:os.startfile(self.last_saved)
            except OSError:messagebox.showerror('파일 열기','파일에 접근할 수 없습니다. 이동·삭제·NAS 연결을 확인해 주세요.',parent=self.root)

    def open_saved_folder(self):
        if self.last_saved:
            try:os.startfile(str(Path(self.last_saved).parent))
            except OSError:messagebox.showerror('폴더 열기','폴더에 접근할 수 없습니다. NAS 연결을 확인해 주세요.',parent=self.root)

    def settings(self):
        if self.busy:return
        w=tk.Toplevel(self.root);w.title('OpenAI API 설정');w.resizable(False,False);w.transient(self.root);w.grab_set()
        f=ttk.Frame(w,padding=18);f.pack()
        state=tk.StringVar(value='키는 현재 Windows 사용자 자격 증명 저장소에 보관합니다.')
        ttk.Label(f,text='OpenAI API 키',font=('맑은 고딕',11,'bold')).grid(row=0,column=0,columnspan=3,sticky='w')
        keyvar=tk.StringVar()
        try:exists=bool(vault.read())
        except Exception as e:messagebox.showerror('키 저장소',self.safe_error(e),parent=w);exists=False
        placeholder='••••••••' if exists else ''
        keyvar.set(placeholder)
        e=ttk.Entry(f,textvariable=keyvar,show='●',width=48);e.grid(row=1,column=0,columnspan=3,pady=8,sticky='ew')
        shown=tk.BooleanVar()
        ttk.Checkbutton(f,text='입력한 키 표시',variable=shown,command=lambda:e.configure(show='' if shown.get() else '●')).grid(row=2,column=0,columnspan=3,sticky='w')
        def store():
            if self.busy:return
            try:
                if keyvar.get()=='••••••••':return
                vault.save(keyvar.get());self.connected=False;keyvar.set('••••••••');shown.set(False);e.configure(show='●');state.set('키를 저장했습니다. 연결 확인을 눌러 주세요.')
            except Exception as ex:messagebox.showerror('키 저장',self.safe_error(ex),parent=w)
        def remove():
            if self.busy:return
            try:vault.delete();keyvar.set('');self.connected=False;state.set('키를 삭제했습니다.')
            except Exception as ex:messagebox.showerror('키 삭제',self.safe_error(ex),parent=w)
        def check():
            if self.busy:return
            # A newly typed key must be explicitly stored before connection testing.
            if keyvar.get() not in ('','••••••••'):
                messagebox.showinfo('키 저장','입력한 키를 먼저 저장해 주세요.',parent=w);return
            def task():
                key=vault.read()
                if not key:raise ValueError('먼저 API 키를 입력·저장해 주세요.')
                return api.connection(key)
            def done(usage):
                self.connected=True
                if w.winfo_exists():state.set(f'연결 확인 성공 · {api.MODEL} · {usage.get("total_tokens","-")} 토큰')
                self.status.set('API 모델 실제 연결 확인을 완료했습니다.')
            self.connected=False
            self.background(task,done,'API 모델 연결을 확인하고 있습니다. 소량의 API 비용이 발생합니다.')
        ttk.Button(f,text='키 저장·변경',command=store).grid(row=3,column=0,pady=8)
        ttk.Button(f,text='키 삭제',command=remove).grid(row=3,column=1,pady=8)
        ttk.Button(f,text='연결 확인',command=check).grid(row=3,column=2,pady=8)
        ttk.Label(f,textvariable=state,wraplength=430).grid(row=4,column=0,columnspan=3,sticky='w',pady=6)
        ttk.Label(f,text=f'기본 모델: {api.MODEL}\n전송: PDF 전체·회의록·현재 초안·수정 요청\nPDF 이미지·텍스트 토큰별 과금이며 ChatGPT 구독과 별도입니다.\n연결 확인도 소량 과금됩니다. 키는 소스·로그에 기록하지 않습니다.',wraplength=430).grid(row=5,column=0,columnspan=3,sticky='w',pady=6)
        w.protocol('WM_DELETE_WINDOW',lambda:None if self.busy else w.destroy())

    def close(self):
        if self.busy:
            messagebox.showinfo('처리 중','작업이 진행 중입니다. 한글 접근 확인 창을 확인하고 작업 완료 후 닫아 주세요.',parent=self.root);return
        if any(self.get(t).strip() for t in [self.minutes,self.findings]) and not messagebox.askyesno('프로그램 종료','저장하지 않은 편집 내용은 사라집니다. 종료할까요?',parent=self.root):return
        self.root.destroy()

def run():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:pass
    root=tk.Tk();App(root);root.mainloop()
