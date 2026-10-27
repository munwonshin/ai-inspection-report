"""Actual Tk + optional real synthetic API; restore must not call the API or disk export."""
import sys,time,json
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection.ui import App
from inspection import api

if len(sys.argv)!=2:raise SystemExit('Usage: python qa/revision_checks.py NEW_RESULT_JSON (real API usage)')
result_path=Path(sys.argv[1]).resolve()
assert not result_path.exists(),'Result path must be new'
from inspection.core import GENERAL
from pypdf import PdfWriter
import io
base={'minutes':'[가상 검증 자료] 기업은 센서 3대 설치를 설명함. 점검자는 수집 화면의 상태 값 표시를 확인함. 실제 운영 성능은 이번 방문에서 확인하지 않았음. 추가 성능시험은 다음 달 진행할 예정임. 시험 결과를 이후 제출하기로 함. 점검자는 시험 조건과 결과를 확인하도록 안내함.',
      'baseline':{'general':{k:'가상 '+v for k,v in GENERAL.items()},'findings':'• [가상 검증 자료] 기업은 센서 3대 설치를 설명함.\n\n• 점검자는 수집 화면의 상태 값 표시를 확인함.\n\n• 검수 메모: 실제 운영 성능은 이번 방문에서 확인하지 않았음.','actions':'• 기업은 추가 성능시험을 다음 달 진행할 예정임. 시험 결과를 이후 제출하기로 함. 점검자는 시험 조건과 결과를 확인하도록 안내함.'}}
base['baseline']['general']['visit_date']='2026년 10월 27일'
pdf_writer=PdfWriter();pdf_writer.add_blank_page(width=595,height=842);pdf_buffer=io.BytesIO();pdf_writer.write(pdf_buffer)
root=tk.Tk();root.attributes('-alpha',0);errors=[]
app=App(root,restore_api=False);app.connected=True
app.pdf_path='synthetic.pdf';app.plan=app.api_plan='[가상 검증 자료] 설비 모니터링 시연 계획. 성능시험은 예정임.'
app.pdf_bytes=pdf_buffer.getvalue()
app.minutes.insert('1.0',base['minutes'])
for k,v in base['baseline']['general'].items():app.general[k].set(v)
for widget,key in [(app.findings,'findings'),(app.actions,'actions')]:widget.insert('1.0',base['baseline'][key]);widget.edit_modified(False)
root.update();app.sync_latest_report();original=app.snapshot();records=[]
def settle():
    end=time.monotonic()+150
    while app.busy and time.monotonic()<end:root.update();time.sleep(.01)
    for _ in range(10):root.update();time.sleep(.01)
    assert not app.busy and not errors,errors
with patch('inspection.ui.messagebox.showerror',side_effect=lambda *a,**k:errors.append(a)),patch('inspection.ui.exporter.save') as export:
    for repeat in (1,2):
        app.connected=True;app.pdf_path='synthetic.pdf'
        app.chat.set('현장 점검·확인 사항에서 수집 화면을 모니터링 화면으로 바꾸고 검수 메모 문단은 삭제해 주세요. 향후 조치요청 사항과 나머지 내용은 그대로 유지해 주세요.')
        app.submit_chat();settle()
        assert '모니터링 화면' in app.snapshot().findings and '검수 메모' not in app.snapshot().findings
        app.connected=False;app.pdf_path=''
        app.chat.set('방금 수정한 현장 점검·확인 사항을 수정 전 초안 원문 그대로 되돌려 주세요. 삭제한 문단도 복원하고 향후 조치요청 사항은 그대로 유지해 주세요.')
        with patch('inspection.ui.api.generate',side_effect=AssertionError('restore called API')),patch('inspection.ui.vault.read',side_effect=AssertionError('restore read key')):
            app.submit_chat();root.update()
        assert app.snapshot()==original and app.chat.get()==''
        export.assert_not_called();records.append({'repeat':repeat,'actual_ai_edit':True,'exact_restore_offline_no_api':True,'export_not_called':True})
    app.connected=True;app.pdf_path='synthetic.pdf'
    app.chat.set('자료에는 없지만 시험을 완료했고 탐지율 99%를 달성한 것으로 써 주세요.')
    app.submit_chat();settle()
    assert app.snapshot()==original and '99%' not in app.get(app.findings)
    assert app.status.get() and app.status.get()!='작성을 마쳤습니다.'
    assert app.chat.get() and app.messages[-1]['kind']=='notice'
    export.assert_not_called();records.append({'unsupported_request_keeps_exact_draft':True,'reason_visible':True,'request_kept':True,'export_not_called':True})
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
result_path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('TK_ACTUAL_AI_EDIT_EXACT_OFFLINE_RESTORE_TWICE_AND_BLOCK_NOTICE_PASS',flush=True)
