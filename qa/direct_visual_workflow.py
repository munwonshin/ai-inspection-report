"""Real API/Tk workflow with only self-generated synthetic HWP and image."""
from pathlib import Path
import sys,tempfile,io,time,json,hashlib
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'tests')]
from PIL import Image,ImageDraw,ImageFont
from test_hwp_direct import compound,text
from test_hwp_images import descriptor,picture
from inspection.ui import App
from inspection import vault,api
import tkinter as tk
target=R/'qa/visual_ai_outputs';target.mkdir(exist_ok=True)
assert not list(target.glob('*.hwp')),'Use a fresh output folder'
with tempfile.TemporaryDirectory(prefix='synthetic-visual-input-') as folder:
    base=Path(folder);img=Image.new('RGB',(1300,240),'white')
    ImageDraw.Draw(img).text((32,64),'참여 책임자: 가상 한빛',font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',54),fill='black')
    image=io.BytesIO();img.save(image,format='PNG')
    plan='가상 검증 자료. 2026년 AI바우처 지원사업 일반분과. 과제명: 가상 펌프 이상진단. 주관기관: 가상새봄제조. 참여기관: 가상파동AI. 주관 책임자: 가상 김하늘. 참여 책임자는 첨부 그림에 기재함. 배경: 설비 데이터 활용 필요. 계획 목표: 데이터 10만 건 확보, 탐지율 90% 검증 예정. 계획 목표는 달성 실적이 아님.'
    source=base/'가상_그림포함_사업계획서.hwp'
    source.write_bytes(compound([text(plan)+picture()],1,descriptors=[descriptor()],assets={'BIN0001.png':image.getvalue()}))
    before=hashlib.sha256(source.read_bytes()).digest()
    root=tk.Tk();root.attributes('-alpha',0);app=App(root,restore_api=False,preferences_path=base/'preferences.json');app.connected=True;errors=[]
    def settle():
        end=time.monotonic()+180
        while (app.busy or not app.mailbox.empty()) and time.monotonic()<end:root.update();time.sleep(.02)
        for _ in range(5):root.update();time.sleep(.02)
        assert not app.busy and not errors,errors
    try:
        with patch('inspection.ui.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('inspection.ui.messagebox.showinfo'),patch('inspection.ui.messagebox.askyesno',return_value=True),patch('inspection.hwp_input.convert_pdf',side_effect=AssertionError('Forbidden PDF conversion')):
            app.load_pdf(str(source));settle();print('ATTACHED_AND_RECOGNIZED',flush=True)
            assert isinstance(app.pdf_bytes,tuple) and app.general_scanned,(type(app.pdf_bytes).__name__,app.general_scanned,app.status.get(),app.general_issues)
            assert app.general['partner_person'].get().replace(' ','')=='가상한빛',app.general_issues
            app.minutes.insert('1.0','가상 회의록. 기업은 센서 2대 설치 완료 및 6만 건 수집을 설명함. 현장에서 집계 화면을 확인함. 성능 시험은 아직 실시하지 않았음. 다음 방문 전 수집 누락 구간을 점검하고 점검 기록을 공유하도록 요청함. 시험 결과 전 탐지율 달성으로 기재하지 않도록 안내함.')
            for k,v in {'visit_date':'2026-11-02','visit_org':'가상 실증현장','inspector_org':'가상 점검기관','inspector':'가상 점검자'}.items():app.general[k].set(v)
            for k,var in app.general.items():
                if not var.get():var.set('가상 검증 수동값')
            app.folder.set(str(target));app.title.set('가상_그림직접읽기_검증')
            app.draft();settle();assert app.snapshot().findings;print('ACTUAL_DRAFT',flush=True)
            marker='검수 메모: 성능 시험 전이며 목표 달성은 미확정임.'
            app.findings.insert('end','\n\n'+marker);app.sync_latest_report()
            app.chat.set('현장점검 확인사항과 검수 메모는 그대로 유지하고, 향후 조치요청 사항만 관련 내용끼리 묶어 2문단으로 정리해 주세요. 새로운 사실이나 조치요청을 추가하지 마세요.')
            app.submit_chat();settle();assert marker in app.snapshot().findings;print('ACTUAL_REVISION',flush=True)
            assert not list(target.iterdir()),'Output created before approval'
            app.approve();settle();assert app.last_saved and Path(app.last_saved).is_file()
            assert hashlib.sha256(source.read_bytes()).digest()==before
            proof={'synthetic_only':True,'picture_only_general_field_recognized':True,'whole_text_and_image_sent':True,
                'actual_draft_and_chat':True,'manual_edit_preserved':True,'no_output_before_approval':True,'native_hwp_saved_and_reimported':True,
                'source_unchanged':True,'input_pdf_conversion_calls':0,'result_bytes':Path(app.last_saved).stat().st_size}
            (R/'qa/direct_visual_workflow.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps(proof),flush=True)
    finally:root.destroy()
