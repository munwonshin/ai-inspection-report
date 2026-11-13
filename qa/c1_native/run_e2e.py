"""Real Tk approval -> real exporter subprocess/COM. Synthetic inputs only."""
import sys,os,pathlib,json,time,hashlib,socket,traceback,subprocess,argparse
from unittest.mock import patch
repo=pathlib.Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--deps-dir',type=pathlib.Path,required=True)
parser.add_argument('--output',type=pathlib.Path,required=True)
args=parser.parse_args();deps=args.deps_dir.resolve();root=args.output.resolve()
if not root.is_relative_to(repo):raise SystemExit('Use a new output directory in this checkout')
sys.path.insert(0,str(repo))
from qa.c1_baseline.run_baseline import configure_dependencies,ControllerCase,production_manifest,create_pdf
dll=configure_dependencies(deps)
from inspection import exporter
from qa.c1_acceptance.adapter import invoke_review_ui
root.mkdir(parents=True,exist_ok=False)
for folder in ('inputs','outputs','evidence','runtime-temp'):(root/folder).mkdir()
fixture=json.loads((repo/'qa/c1_baseline/fixtures.json').read_text(encoding='utf-8'))
for profile in ('A','B'):
    (root/'inputs'/('plan_'+profile+'.pdf')).write_bytes(create_pdf(fixture['profiles'][profile]))
    (root/'inputs'/('minutes_'+profile+'.txt')).write_text(fixture['profiles'][profile]['minutes'],encoding='utf-8')
(root/'inputs/long_60_paragraphs.txt').write_text('\n'.join('C1-LONG-%02d 합성 검수 문단 %02d: 장치 7대 관련 가상 내용입니다. 본문과 서식, 문단 순서가 모두 보존되어야 합니다.'%(i,i) for i in range(1,61)),encoding='utf-8')
os.environ['C1_NATIVE_DEPS']=str(deps)
os.environ['C1_NATIVE_EVIDENCE']=str(root/'evidence')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
scratch=root/'controller';scratch.mkdir()
os.environ['TEMP']=os.environ['TMP']=str(root/'runtime-temp')
import tempfile
tempfile.tempdir=str(root/'runtime-temp')
def deny(*a,**kw):raise RuntimeError('Network disabled in synthetic native trial')
socket.socket.connect=deny;socket.getaddrinfo=deny
real_save=exporter.save;real_run=subprocess.run
events=[];before=production_manifest()
def event(kind,**values):
    row={'event':kind,'time':time.time(),**values};events.append(row)
    with (root/'evidence/events.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(json.dumps(row,ensure_ascii=True),flush=True)
def instrument(command,**kw):
    assert command[1]==str(repo/'main.py') and command[2]=='--hwp-worker'
    return real_run([command[0],str(repo/'qa/c1_native/worker.py'),*command[2:]],**kw)
fixture=json.loads((repo/'qa/c1_baseline/fixtures.json').read_text(encoding='utf-8'))
c=ControllerCase(fixture,{},scratch,'candidate',invoke_review_ui)
c.app.folder.set(str(root/'outputs'))
def settle():
    start=time.monotonic();warned=False
    while c.app.busy:
        c.root.update();time.sleep(.02)
        if time.monotonic()-start>60 and not warned:
            event('WATCHDOG_WARNING',message='60 seconds; no kill/retry');warned=True
        if time.monotonic()-start>120:raise TimeoutError('Worker still running: do not retry or kill Hancom')
    c.root.update()
def hashes():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'outputs').iterdir() if p.is_file()}
def approve(name,expected=True):
    c.app.title.set(name);c.root.update();snapshot=c.app.snapshot()
    prior=hashes();event('approval_start',name=name)
    c.app.approve_button.invoke();settle()
    path=root/'outputs'/(name+'.hwp')
    assert path.exists()==expected,(name,c.dialogs)
    if expected:
        assert c.app.saved_current,(name,c.dialogs)
        (root/'evidence'/(name+'-expected.json')).write_text(json.dumps(snapshot.as_dict(),ensure_ascii=False,indent=2),encoding='utf-8')
    assert all(hashes().get(n)==v for n,v in prior.items())
    event('approval_result',name=name,expected_file=expected,hashes=hashes(),dialogs=c.dialogs)
try:
    with patch('inspection.ui.exporter.save',side_effect=real_save),patch('inspection.exporter.subprocess.run',side_effect=instrument):
        # Use kit PDFs/minutes with real attachment processing and manual report text.
        c.app.load_pdf(str(root/'inputs/plan_A.pdf'));c.settle();c.general('A')
        c.set_text(c.app.minutes,(root/'inputs/minutes_A.txt').read_text(encoding='utf-8'))
        c.action({'action':'manual_draft','profile':'A'});invoke_review_ui(c.app)
        approve('C1_A');a=hashes();body=c.app.get(c.app.findings)
        c.app.load_pdf(str(root/'inputs/plan_B.pdf'));c.settle();c.general('B')
        c.set_text(c.app.minutes,(root/'inputs/minutes_B.txt').read_text(encoding='utf-8'))
        assert c.app.get(c.app.findings)==body
        approve('C1_BLOCKED',False);assert hashes()==a
        event('b_blocked',status='PASS',body_preserved=True)
        c.action({'action':'manual_draft','profile':'B'});invoke_review_ui(c.app)
        approve('C1_B');approve('C1_RENAMED')
        old=hashes();c.app.title.set('C1_B');c.app.approve_button.invoke();settle();assert hashes()==old
        assert any('같은 이름' in d['message'] for d in c.dialogs)
        event('collision_blocked',status='PASS',hashes=old)
        c.set_text(c.app.findings,(root/'inputs/long_60_paragraphs.txt').read_text(encoding='utf-8'))
        invoke_review_ui(c.app);approve('C1_LONG')
    assert before==production_manifest(), 'Source changed during native test'
    assert set(hashes())=={'C1_A.hwp','C1_B.hwp','C1_RENAMED.hwp','C1_LONG.hwp'}
    record={'result':'PASS','cases':{'A_save':'PASS','B_unreviewed_block':'PASS','B_review_save':'PASS','rename':'PASS','collision':'PASS','long_60':'PASS'},'source_manifest':before,'source_unchanged':True,'outputs_sha256':hashes(),'callback_errors':c.callback_errors,'external_AI_calls':0,'scope':'Actual Tk review/approval buttons and original exporter save/worker/COM. API/vault/dialog replies mocked; companion measure_open checks final file Open separately.'}
    with (root/'evidence/results.json').open('x',encoding='utf-8') as out:json.dump(record,out,ensure_ascii=False,indent=2)
    event('controller_complete',status='PASS',callback_errors=c.callback_errors)
except Exception:
    event('FAIL',traceback=traceback.format_exc())
    raise
finally:
    event('source_integrity',unchanged=before==production_manifest())
    if not c.app.busy:c.close()
