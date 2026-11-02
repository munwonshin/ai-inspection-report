"""Synthetic four-division saves using the same isolated worker as the app."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection import exporter
from inspection.core import Report,GENERAL
from inspection.report_format import DIVISIONS,report_title
R=Path(__file__).resolve().parents[1];out=R/'qa/header_roundtrip';out.mkdir(exist_ok=True)
g={k:'가상 '+v for k,v in GENERAL.items()};g['visit_date']='2026-11-02'
before=hashlib.sha256((R/'assets/template.hml').read_bytes()).hexdigest();records=[]
for i,division in enumerate(DIVISIONS,1):
 report=Report(f'가상_저장파일명_{i}',tuple(g.items()),'• 가상 센서 현황을 설명함. 실제 성능은 미확정임.','• 가상 시험 결과를 추후 확인할 예정임.','',report_title('2026',division))
 saved=exporter.save(report,str(out),report.title,approved=True)
 assert saved['ok'] and saved['reopened']
 assert Path(saved['path']).read_bytes().startswith(bytes.fromhex('D0CF11E0A1B11AE1'))
 records.append({'division':division,'document_title':report.document_title,'filename':Path(saved['path']).name,'native_hwp_saved_and_reimported':True,'pages':saved['pages']})
 print(json.dumps(records[-1],ensure_ascii=False),flush=True)
assert before==hashlib.sha256((R/'assets/template.hml').read_bytes()).hexdigest()
(R/'qa/report_header_roundtrip.json').write_text(json.dumps({'records':records,'original_template_unchanged':True,'api_called':False},ensure_ascii=False,indent=2),encoding='utf-8')
