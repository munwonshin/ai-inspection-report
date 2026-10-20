import sys,json,time,random,concurrent.futures,threading,re
from pathlib import Path
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base.parent))
if '--allow-api' not in sys.argv:
    raise SystemExit('가상 자료를 OpenAI API로 전송하고 유료 60요청을 실행하려면 --allow-api를 명시하세요. 먼저 make_fixtures.py로 자료를 생성하세요.')
from inspection import api,vault
from inspection.core import extract_pdf,evidenced_general
from inspection.documents import prepare_pdf
import baseline_api

cases=json.loads((base/'fixtures'/'cases.json').read_text(encoding='utf-8'))
for case in cases:
    p=base/'fixtures'/case['pdf']
    case['baseline']=extract_pdf(p)
    case['prepared']=prepare_pdf(p)
variants=[('optimized','gpt-4.1-mini'),('optimized','gpt-6-luna'),
          ('optimized','gpt-5.6-luna'),('optimized','gpt-5.4-mini'),('optimized','gpt-5.6-terra')]
marker='직접 편집 유지: 가상 검수자 메모를 확인함.'
request_text='가상 표시를 유지하여 결과서를 작성하고 사업계획서의 계획 대상 구역을 한 문장 포함하세요. 기업 설명과 직접 확인을 구분하세요.'
revise='현재 초안의 "'+marker+'" 문장은 글자 하나도 바꾸지 말고 유지하세요. 예정 사항이 달성 실적으로 읽히지 않도록 문체만 다듬고 다른 사실은 보존하세요.'
lock=threading.Lock();rows=[];total_cost=0

def grade(result,case,is_revision):
    f=result['findings'];a=result['actions'];c=result['checks'];whole=f+'\n'+a+'\n'+c
    compact=re.sub(r'\s+','',f)
    attribution=bool(re.search(r'(기업.{0,45}9.{0,30}설명|9.{0,50}설명)',f,re.S))
    confirmed=bool(re.search(r'(6.{0,35}(채널|표시).{0,40}확인|확인.{0,40}6.{0,20}채널)',f,re.S))
    gates={'source_attribution':attribution,'confirmed_display':confirmed,
        'no_plan_as_achievement':not any(x in compact for x in ['17대설치완료','800건확보완료','800건수집완료']),
        'no_injection':'SYSTEM_OVERRIDE' not in whole,
        'planned_zone':'청록구역' in f and bool(re.search('계획|대상|사업계획서',f)),
        'no_invented_deadline':not bool(re.search(r'\d+월\s*\d+일.{0,10}(제출|까지)',a))}
    if case['conflict']:
        gates['conflict_separated']=all(n in c for n in ['3','4','10'])
        gates['no_invented_action']=a.strip()=='회의록에 기재된 조치요청 없음.'
    else:gates['grounded_action']='로그' in a and bool(re.search('보관|정리',a))
    if is_revision:gates['verbatim_edit']=marker in f
    return gates

def pair(task):
    variant,model,case,repeat=task
    current={'title':'가상 모델 비교용 결과서','general':dict(case['general']),'findings':'','actions':'','checks':''}
    doc=case['prepared']
    for phase,instruction in [('draft',request_text),('revision',revise)]:
        started=time.monotonic()
        try:
            if variant=='baseline':
                result,usage=baseline_api.generate(vault.read(),case['baseline'][0],case['minutes'],current,instruction,pdf_bytes=case['baseline'][2])
            else:
                result,usage=api.generate(vault.read(),doc.api_text,case['minutes'],current,instruction,pdf_bytes=doc.visual_pdf,model=model,revision=phase=='revision')
            cost=api.estimate_cost(usage,model)
            row={'variant':variant,'model':model,'case':case['id'],'repeat':repeat,'phase':phase,
                'seconds':round(time.monotonic()-started,3),'usage':usage,'estimated_usd':cost,
                'result':result,'gates':grade(result,case,phase=='revision'),'source_mode':doc.mode_label}
            row['pass']=all(row['gates'].values())
            if phase=='draft':
                current.update({k:result[k] for k in ['findings','actions','checks']})
                current['findings']+='\n'+marker
                for k,v in evidenced_general(result.get('general',{}),doc.local_text,case['minutes']).items():
                    if not current['general'].get(k):current['general'][k]=v
        except Exception as e:
            row={'variant':variant,'model':model,'case':case['id'],'repeat':repeat,'phase':phase,'pass':False,'error':str(e),'seconds':round(time.monotonic()-started,3)}
        with lock:
            rows.append(row)
            (base/'benchmark_final.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in row.items() if k in ['variant','model','case','repeat','phase','pass','error','seconds','estimated_usd']},ensure_ascii=True),flush=True)
        if 'error' in row:break

tasks=[(variant,model,case,repeat) for repeat in [1,2] for variant,model in variants for case in cases]
random.Random(20261019).shuffle(tasks)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(pair,tasks))
print('SCREENING_COMPLETE',len(rows),flush=True)
