import os
import queue
import threading
import time
from .streaming import preview
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from . import api, vault, exporter, metadata
from .core import Report, GENERAL, evidenced_general, filename, destination
from .documents import prepare_pdf

BG='#F3F5FA'
WHITE='#FFFFFF'
INK='#1E2B43'
MUTED='#6F7E95'
LINE='#E1E7F0'
FIELD='#FAFBFE'
BLUE='#405EE8'

class App:
    def __init__(self,root):
        self.root=root
        self.plan='';self.api_plan='';self.pdf_path='';self.pdf_bytes=None
        self.busy=False;self.connected=False;self.last_saved=None;self.saved_current=False
        self.mailbox=queue.Queue();self.pdf_progress=queue.SimpleQueue();self.edits=[];self.buttons=[];self.entries=[]
        self.general_expanded=False
        self.auto_general={};self._auto_write=False;self.general_scanned=False;self.document_revision=0;self.metadata_started=None
        self.editor_open=False;self.messages=[];self.revision=0;self.pending_request=None;self._conversation_timer=None
        self.title=tk.StringVar(value='현장점검 결과서')
        self.name=self.title;self.folder=tk.StringVar()
        self.ai_started=None;self.stream_queue=queue.SimpleQueue();self.stream_json="";self.stream_visible=""
        self.general={k:tk.StringVar() for k in GENERAL}
        self.status=tk.StringVar(value='PDF와 회의록을 입력한 뒤 초안을 작성하세요.')
        self.pdf_label=tk.StringVar(value='PDF 파일을 첨부해 주세요 · 최대 30MB')
        self.chat=tk.StringVar()
        self.chat_info=tk.StringVar(value='원본 자료와 현재 편집한 초안을 함께 반영합니다.')
        root.title('AI 현장점검 결과서 · 0.3.7')
        root.geometry('1320x880');root.minsize(1060,720)
        root.configure(bg=BG)
        self.configure_styles()

        outer=ttk.Frame(root,padding=(20,16,20,12));outer.pack(fill='both',expand=True)
        outer.columnconfigure(0,weight=1);outer.rowconfigure(1,weight=1)
        header=ttk.Frame(outer);header.grid(row=0,column=0,sticky='ew',pady=(0,14))
        logo=tk.Canvas(header,width=42,height=42,bg=BG,highlightthickness=0)
        logo.pack(side='left',padx=(0,12))
        logo.create_polygon(10,0,32,0,42,0,42,10,42,32,42,42,32,42,10,42,0,42,0,32,0,10,0,0,smooth=True,fill=BLUE)
        logo.create_text(21,21,text='AI',fill=WHITE,font=('Segoe UI',13,'bold'))
        brand=ttk.Frame(header);brand.pack(side='left')
        ttk.Label(brand,text='AI 현장점검 결과서',style='Brand.TLabel').pack(anchor='w')
        ttk.Label(brand,text='자료 입력  →  AI와 초안 작성  →  승인·저장',style='Subtle.TLabel').pack(anchor='w',pady=(2,0))
        self.button(header,'API 설정',self.settings,style='White.TButton').pack(side='right')
        self.connection_badge=tk.Label(header,text='●  API 연결 확인 필요',font=('맑은 고딕',9),bg=BG,fg=MUTED)
        self.connection_badge.pack(side='right',padx=(10,14))

        self.workspace=ttk.Panedwindow(outer,orient='horizontal')
        self.workspace.grid(row=1,column=0,sticky='nsew')
        left_card=self.card(self.workspace);right_card=self.card(self.workspace)
        left_card.configure(width=360);left_card.pack_propagate(False)
        right_card.configure(width=800);right_card.pack_propagate(False)
        self.workspace.add(left_card,weight=3);self.workspace.add(right_card,weight=7)
        left=ttk.Frame(left_card,style='Card.TFrame',padding=14)
        left.pack(fill='both',expand=True);self.left_content=left
        left.columnconfigure(0,weight=1);left.rowconfigure(1,weight=1,minsize=80)
        self.left_heading=self.heading(left,'01','자료 입력')
        self.left_heading.grid(row=0,column=0,sticky='ew',pady=(0,12))
        self.input_panel=ttk.Frame(left,style='Card.TFrame');self.input_panel.grid(row=1,column=0,sticky='nsew')
        self.input_panel.columnconfigure(0,weight=1);self.input_panel.rowconfigure(3,weight=1,minsize=60)
        pdf=tk.Frame(self.input_panel,bg='#F5F7FD',highlightbackground=LINE,highlightthickness=1)
        self.pdf_surface=pdf
        pdf.grid(row=0,column=0,sticky='ew',pady=(0,12));pdf.columnconfigure(0,weight=1)
        ttk.Label(pdf,text='사업계획서 PDF',style='FieldTitle.TLabel').grid(row=0,column=0,sticky='w',padx=12,pady=(10,0))
        pdf.rowconfigure(0,minsize=30)
        self.remove_pdf_button=self.button(pdf,'×',self.remove_pdf,style='Text.TButton')
        self.remove_pdf_button.configure(width=2,padding=(0,0),takefocus=True)
        self.remove_pdf_button.grid(row=0,column=1,sticky='ne',padx=(6,10),pady=(4,0))
        self.remove_pdf_button.grid_remove()
        self.button(pdf,'PDF 첨부',self.attach,style='Quiet.TButton').grid(row=1,column=1,padx=(6,10),pady=(0,8))
        self.pdf_caption=tk.Label(pdf,textvariable=self.pdf_label,bg='#F5F7FD',fg=MUTED,font=('맑은 고딕',9),anchor='w',justify='left',wraplength=200,height=2)
        self.pdf_caption.grid(row=1,column=0,sticky='ew',padx=(12,4),pady=(3,8))
        pdf.bind('<Configure>',lambda e:self.pdf_caption.configure(wraplength=max(100,e.width-110)))
        self.enable_pdf_drop()
        ttk.Label(self.input_panel,text='회의록',style='FieldLabel.TLabel').grid(row=1,column=0,sticky='w',pady=(0,6))
        self.minutes_hint=ttk.Label(self.input_panel,text='기업 설명·직접 확인·예정·안내를 구분해 입력하세요.',style='Hint.TLabel',wraplength=300)
        self.minutes_hint.grid(row=2,column=0,sticky='w',pady=(0,7))
        self.minutes=self.textbox(self.input_panel,3,height=7)
        self.meta_toggle=self.button(left,'일반현황 · 0/9 확인됨    확인하기  →',self.toggle_general,style='Meta.TButton')
        self.meta_toggle.grid(row=2,column=0,sticky='ew',pady=(12,0))
        self.general_panel=ttk.Frame(left,style='Card.TFrame')
        self.general_panel.grid(row=1,column=0,sticky='nsew');self.general_panel.columnconfigure(0,weight=1);self.general_panel.rowconfigure(0,weight=1)
        self.general_canvas=tk.Canvas(self.general_panel,bg=WHITE,height=210,highlightthickness=0)
        self.general_canvas.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(self.general_panel,orient='vertical',command=self.general_canvas.yview)
        scroll.grid(row=0,column=1,sticky='ns',padx=(5,0))
        self.general_canvas.configure(yscrollcommand=scroll.set)
        self.general_body=ttk.Frame(self.general_canvas,style='Card.TFrame');self.general_body.columnconfigure(1,weight=1)
        self.general_window=self.general_canvas.create_window(0,0,window=self.general_body,anchor='nw')
        self.general_body.bind('<Configure>',lambda e:self.general_canvas.configure(scrollregion=self.general_canvas.bbox('all')))
        self.general_canvas.bind('<Configure>',lambda e:self.general_canvas.itemconfigure(self.general_window,width=e.width))
        for i,(k,label) in enumerate(GENERAL.items()):
            ttk.Label(self.general_body,text=label,style='Hint.TLabel').grid(row=i,column=0,sticky='w',padx=(0,8),pady=3)
            entry=self.entry(self.general_body,self.general[k],compact=True)
            entry.grid(row=i,column=1,sticky='ew',pady=3)
            entry.bind('<FocusIn>',lambda e:self.reveal_general(e.widget))
        for widget in [self.general_canvas,*self.general_body.winfo_children()]:
            widget.bind('<MouseWheel>',self.scroll_general)
        ttk.Label(self.general_panel,text='자료 확인값만 자동 입력 · 빈 필수값은 승인 전에 확인',style='Hint.TLabel',wraplength=340).grid(row=1,column=0,columnspan=2,sticky='w',pady=(6,0))
        self.button(self.general_panel,'AI로 일반현황 다시 읽기',lambda:self.recognize_general(force=True),style='Quiet.TButton').grid(row=2,column=0,columnspan=2,sticky='ew',pady=(6,0))
        self.general_panel.grid_remove()
        left.bind('<Configure>',lambda e:self.fit_general())

        right=ttk.Frame(right_card,style='Card.TFrame',padding=14);right.pack(fill='both',expand=True)
        right.columnconfigure(0,weight=1);right.rowconfigure(2,weight=1,minsize=80)
        draftbar=self.heading(right,'02','AI와 초안 작성')
        draftbar.grid(row=0,column=0,sticky='ew',pady=(0,8))
        self.editor_button=self.button(draftbar,'직접 편집',self.toggle_editor,style='Quiet.TButton')
        self.editor_button.pack(side='right',padx=(8,0))
        self.button(draftbar,'초안 작성',self.draft,primary=True).pack(side='right')
        self.draft_hint=tk.StringVar(value='초안 작성 후 원하는 수정을 채팅으로 요청하세요.')
        ttk.Label(right,textvariable=self.draft_hint,style='Hint.TLabel',wraplength=700).grid(row=1,column=0,sticky='w',pady=(0,8))
        area=ttk.Frame(right,style='Card.TFrame');area.grid(row=2,column=0,sticky='nsew');area.columnconfigure(0,weight=1);area.rowconfigure(0,weight=1)
        self.chat_view=tk.Frame(area,bg=FIELD,highlightbackground=LINE,highlightthickness=1)
        self.chat_view.grid(row=0,column=0,sticky='nsew')
        self.conversation=tk.Text(self.chat_view,wrap='word',state='disabled',width=20,height=10,relief='flat',borderwidth=0,
            bg=FIELD,fg=INK,font=('맑은 고딕',10),padx=18,pady=16,spacing1=3,spacing3=7,selectbackground='#DBE4FF',cursor='arrow')
        scroll=ttk.Scrollbar(self.chat_view,command=self.conversation.yview)
        self.conversation.configure(yscrollcommand=scroll.set)
        self.conversation.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.conversation.tag_configure('welcome',font=('맑은 고딕',14,'bold'),foreground=INK,spacing1=12,spacing3=14)
        self.conversation.tag_configure('hint',font=('맑은 고딕',9),foreground=MUTED,spacing3=16)
        self.conversation.tag_configure('user_head',font=('맑은 고딕',9,'bold'),foreground=BLUE,justify='right',spacing1=16,spacing3=4)
        self.conversation.tag_configure('user',background='#EDF1FF',foreground='#334DB7',lmargin1=48,lmargin2=48,rmargin=8,spacing1=8,spacing3=14)
        self.conversation.tag_configure('report_head',font=('맑은 고딕',10,'bold'),foreground=BLUE,spacing1=16,spacing3=8)
        self.conversation.tag_configure('old_head',font=('맑은 고딕',9,'bold'),foreground=MUTED,spacing1=16,spacing3=8)
        self.conversation.tag_configure('section',font=('맑은 고딕',9,'bold'),foreground='#53647E',spacing1=9,spacing3=5)
        self.conversation.tag_configure('body',lmargin1=2,lmargin2=2,rmargin=10,spacing1=2,spacing3=10)
        self.conversation.tag_configure('error',font=('맑은 고딕',9),foreground='#AD4A56',spacing3=12)
        self.editor_view=ttk.Notebook(area)
        self.editor_view.grid(row=0,column=0,sticky='nsew')
        for key,label in [('findings','현장 점검·확인'),('actions','안내·조치요청'),('checks','확인할 사항')]:
            tab=ttk.Frame(self.editor_view,style='Card.TFrame',padding=(0,8,0,0));tab.columnconfigure(0,weight=1);tab.rowconfigure(0,weight=1)
            self.editor_view.add(tab,text=label)
            setattr(self,key,self.textbox(tab,0,height=8))
        self.editor_view.grid_remove()
        chat=tk.Frame(right,bg='#F5F7FD',highlightbackground=LINE,highlightthickness=1)
        chat.grid(row=3,column=0,sticky='ew',pady=(10,0));chat.columnconfigure(0,weight=1)
        self.chat_title=ttk.Label(chat,text='수정할 내용을 입력하세요',style='FieldTitle.TLabel')
        self.chat_title.grid(row=0,column=0,sticky='w',padx=12,pady=(9,5))
        self.chat_entry=self.entry(chat,self.chat);self.chat_entry.grid(row=1,column=0,sticky='ew',padx=(12,6),pady=(0,7))
        self.chat_entry.bind('<Return>',lambda e:self.send_chat())
        self.chat_button=self.button(chat,'보내기',self.send_chat,primary=True)
        self.chat_button.grid(row=1,column=1,padx=(0,12),pady=(0,7))
        self.chat_note=tk.Label(chat,textvariable=self.chat_info,font=('맑은 고딕',9),bg='#F5F7FD',fg=MUTED,anchor='w',justify='left',wraplength=700)
        self.chat_note.grid(row=2,column=0,columnspan=2,sticky='ew',padx=12,pady=(0,9))
        chat.bind('<Configure>',lambda e:self.chat_note.configure(wraplength=max(250,e.width-24)))
        right.bind('<Configure>',lambda e:self.fit_editor(e.height))

        save_card=self.card(outer);save_card.grid(row=2,column=0,sticky='ew',pady=(12,0))
        save=ttk.Frame(save_card,style='Card.TFrame',padding=(14,11,14,10));save.pack(fill='both',expand=True)
        save.columnconfigure(0,weight=1)
        save_header=self.heading(save,'03','승인 후 저장',small=True);save_header.grid(row=0,column=0,sticky='ew',pady=(0,9))
        self.state_badge=tk.Label(save_header,text='작성 전',bg='#EFF2F7',fg=MUTED,font=('맑은 고딕',9,'bold'),padx=9,pady=3)
        self.state_badge.pack(side='right')
        fields=ttk.Frame(save,style='Card.TFrame');fields.grid(row=1,column=0,sticky='ew')
        for col,weight,size in [(0,3,240),(1,4,300)]:fields.columnconfigure(col,weight=weight,minsize=size)
        for col,label,var in [(0,'결과서 제목 · 저장 파일명으로 사용',self.title)]:
            group=ttk.Frame(fields,style='Card.TFrame',padding=(0,0,12,0));group.grid(row=0,column=col,sticky='ew');group.columnconfigure(0,weight=1)
            ttk.Label(group,text=label,style='Hint.TLabel').grid(row=0,column=0,sticky='w',pady=(0,4))
            self.entry(group,var).grid(row=1,column=0,sticky='ew')
            self.filename_hint=tk.StringVar()
            hint=ttk.Label(group,textvariable=self.filename_hint,style='Hint.TLabel',width=1,wraplength=280)
            hint.grid(row=2,column=0,sticky='ew',pady=(3,0))
            hint.bind('<Configure>',lambda e:e.widget.configure(wraplength=max(160,e.width)))
        location=ttk.Frame(fields,style='Card.TFrame',padding=(0,0,14,0));location.grid(row=0,column=1,sticky='ew');location.columnconfigure(0,weight=1)
        ttk.Label(location,text='저장 위치 · 로컬 / NAS',style='Hint.TLabel').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,4))
        self.entry(location,self.folder).grid(row=1,column=0,sticky='ew',padx=(0,6))
        self.button(location,'폴더 선택',self.choose_folder,style='Quiet.TButton').grid(row=1,column=1)
        self.approve_button=self.button(fields,'승인 및 한글 저장',self.approve,primary=True)
        self.approve_button.grid(row=0,column=2,sticky='se')
        progress_track=tk.Frame(save,height=3,bg='#EDF1F7');progress_track.grid(row=2,column=0,sticky='ew',pady=(10,8));progress_track.pack_propagate(False)
        self.progress=ttk.Progressbar(progress_track,style='Thin.Horizontal.TProgressbar',mode='determinate',maximum=100)
        self.progress.pack(fill='both',expand=True)
        footer=ttk.Frame(save,style='Card.TFrame');footer.grid(row=3,column=0,sticky='ew');footer.columnconfigure(0,weight=1)
        self.status_label=ttk.Label(footer,textvariable=self.status,style='Hint.TLabel',wraplength=800,justify='left')
        self.status_label.grid(row=0,column=0,sticky='w',padx=(0,12))
        self.open_file=self.button(footer,'파일 열기',self.open_saved,style='Text.TButton');self.open_file.grid(row=0,column=1,padx=(0,8))
        self.open_folder=self.button(footer,'폴더 열기',self.open_saved_folder,style='Text.TButton');self.open_folder.grid(row=0,column=2)
        footer.bind('<Configure>',lambda e:self.status_label.configure(wraplength=max(250,e.width-200)))
        self.open_file.configure(state='disabled');self.open_folder.configure(state='disabled')
        ttk.Label(outer,text='PDF 첨부 시 일반현황 AI 인식으로 OpenAI 전송·추가 과금 · 초안 작성 시 PDF·회의록·현재 초안·요청 전송 · ChatGPT 구독과 별도 · 승인 전 파일 생성 없음',style='Legal.TLabel',wraplength=1250).grid(row=3,column=0,sticky='w',pady=(7,0))

        for v in [self.title,self.folder,*self.general.values()]:v.trace_add('write',lambda *a:self.changed())
        for k,v in self.general.items():v.trace_add('write',lambda *a,key=k:self.general_edited(key))
        for text in self.edits:text.bind('<<Modified>>',lambda e:self.text_changed(e.widget))
        self.status.trace_add('write',lambda *a:self.refresh_state())
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(120,self.poll);root.after_idle(self.initial_sash)
        self.refresh_state();self.render_conversation()

    def initial_sash(self):
        width=self.workspace.winfo_width()
        if width<600:self.root.after(50,self.initial_sash);return
        self.workspace.sashpos(0,int(width*.33))

    def configure_styles(self):
        style=ttk.Style();style.theme_use('clam')
        style.configure('.',font=('맑은 고딕',10))
        style.configure('TFrame',background=BG)
        style.configure('Card.TFrame',background=WHITE)
        style.configure('TLabel',background=BG,foreground=INK)
        style.configure('Brand.TLabel',font=('맑은 고딕',17,'bold'))
        style.configure('Subtle.TLabel',font=('맑은 고딕',9),foreground=MUTED)
        style.configure('Card.TLabel',background=WHITE,foreground=INK)
        style.configure('Section.TLabel',background=WHITE,foreground=INK,font=('맑은 고딕',12,'bold'))
        style.configure('Step.TLabel',background=WHITE,foreground=BLUE,font=('Segoe UI',10,'bold'))
        style.configure('FieldLabel.TLabel',background=WHITE,foreground=INK,font=('맑은 고딕',9,'bold'))
        style.configure('Hint.TLabel',background=WHITE,foreground=MUTED,font=('맑은 고딕',9))
        style.configure('FieldTitle.TLabel',background='#F5F7FD',foreground=INK,font=('맑은 고딕',9,'bold'))
        style.configure('Legal.TLabel',background=BG,foreground=MUTED,font=('맑은 고딕',8))
        style.configure('TEntry',fieldbackground=FIELD,foreground=INK,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,insertcolor=BLUE,padding=(9,7),borderwidth=1)
        style.map('TEntry',bordercolor=[('focus',BLUE)],lightcolor=[('focus',BLUE)],darkcolor=[('focus',BLUE)],fieldbackground=[('disabled','#F2F4F8')])
        style.configure('Compact.TEntry',padding=(7,4),font=('맑은 고딕',9))
        style.configure('TButton',padding=(12,7),background='#EDF1F8',foreground=INK,borderwidth=0,relief='flat',focusthickness=1,focuscolor=BLUE)
        style.map('TButton',background=[('disabled','#F1F3F8'),('pressed','#DCE3F1'),('active','#E3E9F4')],foreground=[('disabled','#9AA6B9')])
        style.configure('Primary.TButton',background=BLUE,foreground=WHITE,font=('맑은 고딕',10,'bold'),padding=(16,8),focuscolor='#AFBEFF')
        style.map('Primary.TButton',background=[('disabled','#C5CEF2'),('pressed','#2D45B5'),('active','#3451D7')],foreground=[('disabled','#F4F6FF'),('!disabled',WHITE)])
        style.configure('Quiet.TButton',background='#EAF0FD',foreground='#3652C6',padding=(10,7),font=('맑은 고딕',9,'bold'))
        style.configure('White.TButton',background=WHITE,padding=(14,8))
        style.configure('Meta.TButton',background='#F5F7FC',foreground='#53647E',anchor='w',padding=(11,9),font=('맑은 고딕',9,'bold'))
        style.configure('Text.TButton',background=WHITE,foreground='#53647E',padding=(7,3),font=('맑은 고딕',9))
        style.configure('Danger.TButton',background='#FFF0F3',foreground='#AF3D56')
        style.configure('Vertical.TScrollbar',background='#CAD3E3',troughcolor=FIELD,borderwidth=0,arrowsize=10)
        style.configure('Thin.Horizontal.TProgressbar',background=BLUE,troughcolor='#EDF1F7',borderwidth=0,thickness=3)
        style.configure('TPanedwindow',background=BG)
        style.configure('Sash',sashthickness=12,background=BG)
        style.configure('TNotebook',background=WHITE,borderwidth=0)
        style.configure('TNotebook.Tab',padding=(12,7),font=('맑은 고딕',9),background='#EDF1F8',foreground=MUTED)
        style.map('TNotebook.Tab',background=[('selected',WHITE)],foreground=[('selected',BLUE)])
        style.configure('TCheckbutton',background=WHITE,foreground=INK)

    def card(self,parent):
        return tk.Frame(parent,bg=WHITE,highlightbackground=LINE,highlightthickness=1,bd=0)

    def heading(self,parent,step,title,small=False):
        f=ttk.Frame(parent,style='Card.TFrame')
        ttk.Label(f,text=step,style='Step.TLabel').pack(side='left',padx=(0,9))
        ttk.Label(f,text=title,style='FieldLabel.TLabel' if small else 'Section.TLabel').pack(side='left')
        return f

    def entry(self,parent,var,compact=False):
        e=ttk.Entry(parent,textvariable=var,style='Compact.TEntry' if compact else 'TEntry',font=('맑은 고딕',9 if compact else 10))
        self.entries.append(e);return e

    def button(self,parent,text,fn,primary=False,style=None):
        b=ttk.Button(parent,text=text,command=fn,style=style or ('Primary.TButton' if primary else 'TButton'))
        self.buttons.append(b);return b

    def textbox(self,parent,row,height):
        f=tk.Frame(parent,bg=FIELD,highlightbackground=LINE,highlightcolor=BLUE,highlightthickness=1,bd=0)
        f.grid(row=row,column=0,sticky='nsew')
        t=tk.Text(f,wrap='word',undo=True,height=height,width=20,relief='flat',borderwidth=0,
            padx=12,pady=9,bg=FIELD,fg=INK,insertbackground=BLUE,selectbackground='#DBE4FF',
            selectforeground=INK,font=('맑은 고딕',10),spacing1=2,spacing3=5,inactiveselectbackground='#E4EAF7')
        s=ttk.Scrollbar(f,command=t.yview);t.configure(yscrollcommand=s.set)
        t.pack(side='left',fill='both',expand=True);s.pack(side='right',fill='y')
        t.bind('<FocusIn>',lambda e:f.configure(highlightbackground=BLUE))
        t.bind('<FocusOut>',lambda e:f.configure(highlightbackground=LINE))
        self.edits.append(t);return t

    def toggle_general(self):
        if self.busy:return
        self.general_expanded=not self.general_expanded
        if self.general_expanded:self.input_panel.grid_remove();self.general_panel.grid()
        else:self.general_panel.grid_remove();self.input_panel.grid()
        self.refresh_state()

    def fit_general(self):
        compact=self.left_content.winfo_height()<470
        self.minutes_hint.configure(wraplength=max(180,self.left_content.winfo_width()-28))
        if compact:self.minutes_hint.grid_remove()
        else:self.minutes_hint.grid()
        self.pdf_caption.configure(height=1 if compact else 2)
        self.left_heading.grid_configure(pady=(0,6 if compact else 12))
        self.pdf_surface.grid_configure(pady=(0,6 if compact else 12))
        self.meta_toggle.grid_configure(pady=(8 if compact else 12,0))

    def scroll_general(self,event):
        self.general_canvas.yview_scroll(-int(event.delta/120),'units');return 'break'

    def fit_editor(self,height):
        compact=height<500
        for widget in [self.chat_title,self.chat_note]:
            if compact:widget.grid_remove()
            else:widget.grid()
        for widget in [self.chat_entry,self.chat_button]:widget.grid_configure(pady=(9,9) if compact else (0,7))

    def reveal_general(self,widget):
        y=widget.winfo_y();top=self.general_canvas.canvasy(0);bottom=top+self.general_canvas.winfo_height()
        if y<top or y+widget.winfo_height()>bottom:
            self.general_canvas.yview_moveto(max(0,y-6)/max(1,self.general_body.winfo_height()))

    def refresh_state(self):
        if hasattr(self,'filename_hint'):
            try:self.filename_hint.set('저장 이름: '+filename(self.title.get()))
            except ValueError:self.filename_hint.set('저장 이름 확인 필요 · 제목 또는 금지 문자 확인')
        if self.pdf_path:self.remove_pdf_button.grid()
        else:self.remove_pdf_button.grid_remove()
        self.remove_pdf_button.configure(state='disabled' if self.busy else 'normal')
        count=sum(bool(v.get().strip()) for v in self.general.values())
        self.meta_toggle.configure(text=f'일반현황 · {count}/{len(GENERAL)} 확인됨    '+('자료 입력으로  ←' if self.general_expanded else '확인하기  →'))
        self.connection_badge.configure(text='●  API 연결됨' if self.connected else '●  API 연결 확인 필요',fg='#168575' if self.connected else MUTED)
        if self.busy:text,bg,fg='처리 중','#EDF0FF',BLUE
        elif self.saved_current:text,bg,fg='저장 완료','#E8F6F0','#168575'
        elif self.get(self.findings).strip():text,bg,fg='미저장 초안','#FFF4DF','#956717'
        else:text,bg,fg='작성 전','#EFF2F7',MUTED
        self.state_badge.configure(text=text,bg=bg,fg=fg)
        if hasattr(self,'draft_hint'):
            self.draft_hint.set('직접 편집 중 · 현재 편집 내용이 승인 시 저장됩니다.' if self.editor_open else ('저장 대상: 최신 초안 · '+text if self.get(self.findings).strip() else '초안 작성 후 원하는 수정을 채팅으로 요청하세요.'))
        if not self.busy:self.progress.configure(value=100 if self.saved_current else 0)

    def toggle_editor(self):
        if self.busy:return
        self.editor_open=not self.editor_open
        if self.editor_open:
            self.chat_view.grid_remove();self.editor_view.grid()
            self.editor_button.configure(text='대화로 돌아가기')
        else:
            self.sync_latest_report();self.editor_view.grid_remove();self.chat_view.grid()
            self.editor_button.configure(text='직접 편집');self.render_conversation(follow=True)
        self.refresh_state()

    def send_chat(self):
        if self.busy or not self.chat.get().strip() or not self.ready():return
        self.ai(self.chat.get().strip(),bool(self.get(self.findings).strip()),from_chat=True)

    def sync_latest_report(self):
        current=self.snapshot().as_dict()
        for message in reversed(self.messages):
            if message['kind']=='report':message['report']=current;return
        if current['findings'].strip():
            self.revision+=1
            self.messages.append({'kind':'report','version':self.revision,'report':current,'origin':'manual'})

    def schedule_conversation(self):
        if self._conversation_timer is not None:self.root.after_cancel(self._conversation_timer)
        self._conversation_timer=self.root.after(140,self.render_conversation)

    def render_conversation(self,follow=False):
        if self._conversation_timer is not None:
            self.root.after_cancel(self._conversation_timer);self._conversation_timer=None
        view=self.conversation.yview();at_bottom=not view or view[1]>.97
        self.conversation.configure(state='normal');self.conversation.delete('1.0','end')
        latest=next((m for m in reversed(self.messages) if m['kind']=='report'),None)
        def report_card(report,heading,latest_card):
            self.conversation.insert('end',heading+'\n','report_head' if latest_card else 'old_head')
            if report.get('title'):self.conversation.insert('end',report['title']+'\n','section')
            for key,label in [('findings','현장 점검·확인 사항'),('actions','안내·조치요청'),('checks','확인할 사항')]:
                if report.get(key,'').strip():
                    self.conversation.insert('end',label+'\n','section')
                    self.conversation.insert('end',report[key]+'\n','body')
            self.conversation.insert('end','\n')
        if not self.messages and not self.get(self.findings).strip():
            self.conversation.insert('end','현장점검 결과서를 작성하세요\n','welcome')
            self.conversation.insert('end','왼쪽에 PDF와 회의록을 입력하고 ‘초안 작성’을 눌러주세요.\n\n초안이 표시되면 원하는 수정을 아래 채팅으로 요청할 수 있습니다.\n직접 고치려면 상단의 ‘직접 편집’을 이용하세요.','hint')
        for message in self.messages:
            if message['kind']=='user':
                self.conversation.insert('end','나의 요청\n','user_head')
                self.conversation.insert('end',message['text']+'\n','user')
                if message.get('status')=='pending':
                    self.conversation.mark_set('stream_start','end-1c');self.conversation.mark_gravity('stream_start','left')
                    self.conversation.insert('end',self.stream_header(),'hint')
                    if self.stream_visible:self.conversation.insert('end',self.stream_visible+' ▍\n','body')
                    self.conversation.mark_set('stream_end','end-1c');self.conversation.mark_gravity('stream_end','right')
                elif message.get('status')=='failed':self.conversation.insert('end','요청을 처리하지 못했습니다. 이전 초안과 입력 내용은 유지됩니다.\n','error')
            elif message['kind']=='report':
                current=message is latest
                report=self.snapshot().as_dict() if current else message['report']
                heading=('최신 초안' if current else '이전 초안')+f' · {message["version"]}차'
                if current:heading+=' · 승인 시 저장 대상'
                report_card(report,heading,current)
        if latest is None and self.get(self.findings).strip():
            report_card(self.snapshot().as_dict(),'직접 편집한 최신 초안 · 승인 시 저장 대상',True)
        self.conversation.configure(state='disabled')
        if follow or at_bottom:self.conversation.see('end')
        else:self.conversation.yview_moveto(view[0])

    def stream_header(self):
        elapsed=int(time.monotonic()-self.ai_started) if self.ai_started is not None else 0
        dots='·'*(1+(elapsed%3))
        return f'AI 작성 중 {dots}  {elapsed}초 경과 · 완료 후 검수 가능\n'

    def render_stream(self):
        if 'stream_start' not in self.conversation.mark_names():
            self.render_conversation();return
        view=self.conversation.yview();follow=not view or view[1]>.97
        self.conversation.configure(state='normal')
        self.conversation.delete('stream_start','stream_end')
        self.conversation.insert('stream_end',self.stream_header(),'hint')
        if self.stream_visible:self.conversation.insert('stream_end',self.stream_visible+' ▍\n','body')
        self.conversation.configure(state='disabled')
        if follow:self.conversation.see('end')
        else:self.conversation.yview_moveto(view[0])

    def text_changed(self,t):
        if t.edit_modified():self.changed();t.edit_modified(False)

    def changed(self):
        self.saved_current=False
        if hasattr(self,'open_file') and self.last_saved:
            self.open_file.configure(state='disabled');self.open_folder.configure(state='disabled')
            if not self.busy:self.status.set('편집 내용이 변경됐습니다. 다시 승인·저장해야 변경 내용이 파일에 반영됩니다.')
        self.refresh_state();self.schedule_conversation()

    def get(self,t):return t.get('1.0','end-1c')

    def snapshot(self):
        return Report(self.title.get(),tuple((k,v.get()) for k,v in self.general.items()),
            self.get(self.findings),self.get(self.actions),self.get(self.checks))

    def lock(self,value):
        self.busy=value
        if value:self.progress.configure(mode='indeterminate');self.progress.start(12)
        else:self.progress.stop();self.progress.configure(mode='determinate',value=0)
        for e in self.entries+self.edits+self.buttons:e.configure(state='disabled' if value else 'normal')
        if not value and not self.saved_current:
            self.open_file.configure(state='disabled');self.open_folder.configure(state='disabled')
        self.refresh_state()

    def background(self,fn,done,status):
        if self.busy:return
        self.lock(True);self.status.set(status)
        def execute():
            try:self.mailbox.put((done,True,fn()))
            except Exception as e:self.mailbox.put((done,False,e))
        threading.Thread(target=execute,daemon=False).start()

    def poll(self):
        if self.metadata_started is not None:
            self.status.set(f'PDF 첨부 완료 · 일반현황 AI 인식 중 · {int(time.monotonic()-self.metadata_started)}초 경과')
        if self.ai_started is not None and self.pending_request is not None:
            try:
                while True:self.stream_json+=self.stream_queue.get_nowait()
            except queue.Empty:pass
            target=preview(self.stream_json)
            # Short paced batches follow actual network data; never invent text.
            gap=len(target)-len(self.stream_visible)
            self.stream_visible=target[:len(self.stream_visible)+max(1,min(500,gap//4))]
            elapsed=int(time.monotonic()-self.ai_started)
            self.status.set(f'AI 작성 중 · {elapsed}초 경과 · '+('본문 수신 중' if target else '응답을 기다리는 중'))
            self.render_stream()
        latest=None
        try:
            while True:latest=self.pdf_progress.get_nowait()
        except queue.Empty:pass
        if latest is not None and self.busy:
            self.status.set(f'PDF 읽기 · {latest[0]}/{latest[1]}쪽 분석 중 · 외부 전송 없음')
        try:
            done,ok,result=self.mailbox.get_nowait()
            if ok and self.ai_started is not None and self.stream_visible!=preview(self.stream_json):
                # Keep the approval gate closed while the last received characters
                # drain, avoiding a final jump from a partial to the entire report.
                self.mailbox.put((done,ok,result))
            else:
                self.ai_started=None
                self.lock(False)
                if ok:done(result)
                else:
                    if self.pending_request is not None:
                        self.pending_request['status']='failed';self.pending_request=None;self.render_conversation(follow=True)
                    self.status.set('처리에 실패했습니다. 입력·편집 내용은 유지됩니다.')
                    messagebox.showerror('처리 실패',self.safe_error(result),parent=self.root)
        except queue.Empty:pass
        self.root.after(40 if self.ai_started is not None else 120,self.poll)

    def safe_error(self,e):
        if isinstance(e,(ValueError,RuntimeError,api.ApiFailure,PermissionError)):return str(e)
        return '작업을 완료하지 못했습니다. 파일·네트워크·접근 권한을 확인해 주세요. 입력 내용은 유지됩니다.'

    def choose_folder(self):
        p=filedialog.askdirectory(parent=self.root,title='저장 폴더 선택 · 로컬 또는 NAS')
        if p:self.folder.set(p)

    def attach(self):
        if self.busy:return
        p=filedialog.askopenfilename(parent=self.root,title='사업계획서 PDF',filetypes=[('PDF','*.pdf')])
        if not p:return
        self.load_pdf(p)

    def remove_pdf(self):
        if self.busy:return
        self.clear_plan_general();self.document_revision+=1;self.general_scanned=False
        self.plan='';self.api_plan='';self.pdf_path='';self.pdf_bytes=None
        hint='PDF 첨부 또는 여기로 드래그 · 최대 30MB' if self.root.tk.call('package','provide','tkdnd') else 'PDF 파일을 첨부해 주세요 · 최대 30MB'
        self.pdf_label.set(hint)
        self.pdf_drag_leave()
        self.status.set('PDF 첨부를 해제했습니다. 회의록과 기존 초안은 유지됩니다. 새 PDF를 첨부한 뒤 필요하면 초안을 다시 작성하세요.')
        self.refresh_state()

    def enable_pdf_drop(self):
        # Normal Tk roots used by existing controller tests need no native DnD.
        if not self.root.tk.call('package','provide','tkdnd'):return
        from tkinterdnd2 import DND_FILES
        for widget in [self.pdf_surface,*self.pdf_surface.winfo_children()]:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind('<<DropEnter>>',self.pdf_drag_enter)
            widget.dnd_bind('<<DropLeave>>',self.pdf_drag_leave)
            widget.dnd_bind('<<Drop>>',self.pdf_drop)
        self.pdf_label.set('PDF 첨부 또는 여기로 드래그 · 최대 30MB')

    def pdf_drag_enter(self,event):
        if self.busy:return 'refuse_drop'
        self.pdf_surface.configure(highlightbackground=BLUE,highlightthickness=1)
        return 'copy'

    def pdf_drag_leave(self,event=None):
        self.pdf_surface.configure(highlightbackground=LINE,highlightthickness=1)
        return 'copy'

    def pdf_drop(self,event):
        self.pdf_drag_leave()
        if self.busy:return 'refuse_drop'
        try:paths=self.root.tk.splitlist(event.data)
        except tk.TclError:paths=()
        if len(paths)!=1 or Path(paths[0]).suffix.lower()!='.pdf':
            self.status.set('사업계획서 PDF 파일 1개만 놓아 주세요. 기존 첨부는 유지됩니다.')
            return 'refuse_drop'
        self.load_pdf(paths[0])
        return 'copy'

    def load_pdf(self,p):
        if self.busy:return
        def done(result):
            self.clear_plan_general();self.document_revision+=1;self.general_scanned=False
            self.plan=result.local_text;self.api_plan=result.api_text
            self.pdf_bytes=result.visual_pdf;self.pdf_path=p
            name=Path(p).name
            if len(name)>32:name=Path(p).stem[:27]+'…'+Path(p).suffix
            self.pdf_label.set(f'{name}\n{result.page_count}쪽 · 첨부 완료')
            if self.connected:
                self.status.set('PDF 첨부 완료 · 일반현황 AI 인식을 준비합니다.')
                self.recognize_general()
            else:self.status.set('PDF 첨부 완료 · API 연결 확인 후 일반현황을 자동 인식합니다. 직접 입력도 가능합니다.')
        self.background(lambda:prepare_pdf(p,progress=lambda current,total:self.pdf_progress.put((current,total))),done,'PDF의 모든 쪽과 시각 자료를 읽고 있습니다. 지금은 외부 전송하지 않습니다.')

    def general_edited(self,key):
        if not self._auto_write:self.auto_general.pop(key,None)

    def set_plan_general(self,key,value):
        self._auto_write=True
        try:self.general[key].set(value);self.auto_general[key]=value
        finally:self._auto_write=False

    def clear_plan_general(self):
        self._auto_write=True
        try:
            for key,value in self.auto_general.items():
                if self.general[key].get()==value:self.general[key].set('')
            self.auto_general.clear()
        finally:self._auto_write=False

    def recognize_general(self,force=False):
        if self.busy or not self.pdf_path:return
        if not self.connected:
            self.status.set('API 설정에서 연결 확인 후 일반현황을 자동 인식합니다. 직접 입력도 가능합니다.');return
        if self.general_scanned and not force:return
        fields=tuple(k for k in metadata.PLAN_FIELDS if not self.general[k].get().strip())
        if not fields:
            self.general_scanned=True;self.status.set('PDF 첨부 완료 · 일반현황이 이미 입력되어 추가 AI 인식을 생략했습니다.');return
        revision=self.document_revision;plan=self.plan;api_plan=self.api_plan;pdf=self.pdf_bytes
        self.metadata_started=time.monotonic()
        def task():
            try:
                key=vault.read()
                if not key:raise ValueError('저장된 API 키가 없습니다.')
                return {'data':metadata.extract(key,api_plan,plan,pdf,fields)}
            except Exception as e:return {'error':self.safe_error(e)}
        def done(result):
            self.metadata_started=None
            if revision!=self.document_revision:return
            if 'error' in result:
                self.status.set('PDF 첨부는 완료됐습니다. 일반현황 AI 인식 실패: '+result['error']+' 일반현황에서 다시 읽기 또는 직접 입력해 주세요.');return
            values,usage=result['data'];added=0
            for key,value in values.items():
                if key in fields and not self.general[key].get().strip():self.set_plan_general(key,value);added+=1
            self.general_scanned=True
            cost=usage.get('estimated_usd');price=f' · 약 ${cost:.5f}' if cost is not None else ''
            self.status.set(f'PDF 첨부 완료 · 일반현황 {added}개 자동 입력 · 확인되지 않은 항목은 직접 확인{price}')
        self.background(task,done,'PDF 첨부 완료 · 일반현황을 AI로 인식합니다. PDF 전송과 API 비용이 발생합니다.')

    def ready(self):
        if not self.connected:
            messagebox.showinfo('API 연결 확인','API 설정에서 키를 저장하고 연결 확인을 먼저 해 주세요.',parent=self.root);return False
        if not self.pdf_path or not self.get(self.minutes).strip():
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

    def ai(self,instruction,is_chat,from_chat=False):
        if self.busy:return
        self.sync_latest_report()
        self.ai_started=time.monotonic();self.stream_json="";self.stream_visible=""
        self.stream_queue=queue.SimpleQueue()
        self.pending_request={'kind':'user','text':instruction,'status':'pending'}
        self.messages.append(self.pending_request)
        if self.editor_open:self.toggle_editor()
        self.render_conversation(follow=True)
        current=self.snapshot().as_dict()
        plan=self.plan;api_plan=self.api_plan;minutes=self.get(self.minutes)
        def task():
            key=vault.read()
            if not key:raise ValueError('저장된 API 키가 없습니다.')
            return api.generate(key,api_plan,minutes,current,instruction,pdf_bytes=self.pdf_bytes,revision=is_chat,on_delta=self.stream_queue.put)
        def done(data):
            result,usage=data
            for t,k in [(self.findings,'findings'),(self.actions,'actions'),(self.checks,'checks')]:
                t.delete('1.0','end');t.insert('1.0',result[k]);t.edit_modified(False)
            for k,v in evidenced_general(result['general'],plan,minutes).items():
                if not self.general[k].get().strip():
                    if k in metadata.PLAN_FIELDS and result['general'][k].get('source')=='plan':self.set_plan_general(k,v)
                    else:self.general[k].set(v)
            self.changed()
            inputs=usage.get('input_tokens','-');outputs=usage.get('output_tokens','-')
            cost=usage.get('estimated_usd');price=f' · 약 ${cost:.5f}' if cost is not None else ''
            self.status.set(f'반영 완료 · {api.MODEL} · 입력 {inputs} / 출력 {outputs} 토큰{price} · 미저장')
            if self.pending_request is not None:self.pending_request['status']='completed';self.pending_request=None
            self.revision+=1
            self.messages.append({'kind':'report','version':self.revision,'report':self.snapshot().as_dict(),'origin':'ai'})
            self.render_conversation(follow=True)
            if is_chat or from_chat:self.chat_info.set('수정을 반영했습니다. 최신 초안을 확인해 주세요.');self.chat.set('')
        self.background(task,done,'OpenAI에서 작성 중입니다. 화면 입력은 잠시 잠기며 기존 내용은 유지됩니다.')

    def missing_dialog(self,missing):
        w=tk.Toplevel(self.root);w.title('승인 전 필수값 확인');w.configure(bg=WHITE);w.resizable(False,False);w.transient(self.root);w.grab_set()
        f=ttk.Frame(w,style='Card.TFrame',padding=22);f.pack(fill='both',expand=True)
        ttk.Label(f,style='Card.TLabel',text='자료에서 확인되지 않은 필수값만 입력해 주세요.\n해당하지 않으면 ‘해당 없음’으로 확인하세요.').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,14))
        values={};accepted=[]
        for i,k in enumerate(missing,1):
            ttk.Label(f,text=GENERAL[k],style='Hint.TLabel').grid(row=i,column=0,sticky='w',padx=(0,10),pady=4)
            values[k]=tk.StringVar();ttk.Entry(f,textvariable=values[k],width=36).grid(row=i,column=1,pady=3)
        def accept():
            if any(not v.get().strip() for v in values.values()):
                messagebox.showinfo('입력 확인','빈 값을 모두 확인해 주세요.',parent=w);return
            for k,v in values.items():self.general[k].set(v.get().strip())
            accepted.append(True);w.destroy()
        ttk.Button(f,text='취소',style='Text.TButton',command=w.destroy).grid(row=len(missing)+1,column=0,sticky='w',pady=(16,0))
        ttk.Button(f,text='확인 후 승인·저장',style='Primary.TButton',command=accept).grid(row=len(missing)+1,column=1,sticky='e',pady=(16,0))
        self.place_dialog(w)
        self.root.wait_window(w);return bool(accepted)

    def place_dialog(self,window):
        window.update_idletasks()
        width=window.winfo_reqwidth();height=window.winfo_reqheight()
        x=self.root.winfo_rootx()+(self.root.winfo_width()-width)//2
        y=self.root.winfo_rooty()+(self.root.winfo_height()-height)//2
        x=max(0,min(x,window.winfo_screenwidth()-width))
        y=max(0,min(y,window.winfo_screenheight()-height-50))
        window.geometry(f'+{x}+{y}')

    def approve(self):
        if self.busy:return
        if not self.title.get().strip() or not self.get(self.findings).strip():
            messagebox.showinfo('입력 확인','결과서 제목과 현장 점검 본문을 입력해 주세요.',parent=self.root);return
        try:destination(self.folder.get(),self.name.get())
        except ValueError as e:messagebox.showerror('저장 설정',str(e),parent=self.root);return
        missing=[k for k in GENERAL if not self.general[k].get().strip()]
        if missing and not self.missing_dialog(missing):return
        self.sync_latest_report();self.render_conversation()
        snapshot=self.snapshot();folder=self.folder.get();name=self.name.get()
        def done(result):
            self.last_saved=result['path']
            self.saved_current=True
            self.open_file.configure(state='normal');self.open_folder.configure(state='normal')
            self.status.set(f'저장 완료 · {result["pages"]}쪽 · 한글 재열기 확인을 마쳤습니다.')
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
        w=tk.Toplevel(self.root);w.title('API 설정');w.configure(bg=WHITE);w.resizable(False,False);w.transient(self.root);w.grab_set()
        f=ttk.Frame(w,style='Card.TFrame',padding=24);f.pack()
        state=tk.StringVar(value='키는 현재 Windows 사용자 자격 증명 저장소에 보관합니다.')
        ttk.Label(f,text='OpenAI API 키',style='Card.TLabel',font=('맑은 고딕',13,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,6))
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
                self.recognize_general()
            self.connected=False
            self.background(task,done,'API 모델 연결을 확인하고 있습니다. 소량의 API 비용이 발생합니다.')
        ttk.Button(f,text='키 저장·변경',command=store).grid(row=3,column=0,pady=8)
        ttk.Button(f,text='키 삭제',style='Danger.TButton',command=remove).grid(row=3,column=1,pady=8)
        ttk.Button(f,text='연결 확인',style='Primary.TButton',command=check).grid(row=3,column=2,pady=8)
        ttk.Label(f,textvariable=state,style='Card.TLabel',wraplength=440).grid(row=4,column=0,columnspan=3,sticky='w',pady=(10,6))
        ttk.Label(f,style='Hint.TLabel',text=f'기본 모델: {api.MODEL}\nPDF 첨부 시: 모든 쪽의 텍스트·시각 자료로 일반현황 인식(추가 과금)\n초안 작성 시: PDF·회의록·현재 초안·수정 요청 전송\n사용량별 과금이며 ChatGPT 구독과 별도입니다.\n표시 비용은 공개 단가 기준 USD 추정치입니다.\n연결 확인도 소량 과금됩니다. 키는 소스·로그에 기록하지 않습니다.',wraplength=440).grid(row=5,column=0,columnspan=3,sticky='w',pady=(8,0))
        w.protocol('WM_DELETE_WINDOW',lambda:None if self.busy else w.destroy())
        self.place_dialog(w);e.focus_set();e.selection_range(0,'end')

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
    from tkinterdnd2 import TkinterDnD
    root=TkinterDnD.Tk();App(root);root.mainloop()
