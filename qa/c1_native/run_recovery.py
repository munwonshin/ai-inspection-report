"""Real Tk/COM timeout, failure and same-name retry; synthetic isolated paths."""
import argparse,json,os,sys,time,tempfile,subprocess,hashlib,socket
from pathlib import Path
from unittest.mock import patch
repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo))
from qa.c1_baseline.run_baseline import configure_dependencies,ControllerCase,production_manifest
from qa.c1_acceptance.adapter import invoke_review_ui
p=argparse.ArgumentParser();p.add_argument('--deps-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
dll=configure_dependencies(args.deps_dir)
from inspection import exporter,hwp_process
root=args.output.resolve()
if not root.is_relative_to(repo):raise SystemExit('New checkout-local directory required')
if hwp_process.hancom_pids():raise SystemExit('Existing Hancom: trial not started')
root.mkdir(parents=True,exist_ok=False);(root/'outputs').mkdir();(root/'temp').mkdir();(root/'controller').mkdir()
tempfile.tempdir=str(root/'temp');os.environ['TEMP']=os.environ['TMP']=str(root/'temp');os.environ['C1_NATIVE_DEPS']=str(args.deps_dir.resolve())
def deny(*a,**kw):raise RuntimeError('Network disabled')
socket.socket.connect=deny;socket.getaddrinfo=deny
fixture=json.loads((repo/'qa/c1_baseline/fixtures.json').read_text(encoding='utf-8'))
real_save=exporter.save;real_popen=subprocess.Popen
c=ControllerCase(fixture,{},root/'controller','candidate',invoke_review_ui)
c.action({'action':'base','profile':'A'});c.app.folder.set(str(root/'outputs'));c.app.title.set('RECOVERY');invoke_review_ui(c.app);c.root.update()
body=c.app.snapshot();before=production_manifest()
mode='stall';cases=[];worker_ids=[]
def launch(command,**kw):
    assert command[2]=='--hwp-worker'
    process=real_popen([command[0],str(repo/'qa/c1_native/stall_worker.py'),*command[2:]],**kw)
    worker_ids.append(process.pid);return process
def save(*a,**kw):return real_save(*a,**kw,timeout=20 if mode=='stall' else 120)
try:
    with patch('inspection.ui.exporter.save',side_effect=save),patch('inspection.save_job.subprocess.Popen',side_effect=launch):
        for mode,success in [('stall',False),('normal',True),('failure',False),('normal',True)]:
            if mode=='failure':c.app.title.set('RECOVERY_SECOND')
            os.environ['R028_FAULT']=mode
            prior={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in (root/'outputs').iterdir()}
            started=time.monotonic();c.app.approve_button.invoke()
            while c.app.busy:
                c.root.update();time.sleep(.02)
                if time.monotonic()-started>140:raise RuntimeError('External trial watchdog: incomplete; no broad process kill')
            c.root.update();elapsed=time.monotonic()-started
            assert c.app.saved_current is success,(mode,c.dialogs)
            assert c.app.get(c.app.findings)==body.findings
            assert not list((root/'outputs').glob('*.tmp'))
            assert all(hashlib.sha256((root/'outputs'/n).read_bytes()).hexdigest()==h for n,h in prior.items())
            if mode=='stall':
                assert any('제한 시간' in d['message'] for d in c.dialogs)
                assert not hwp_process.hancom_pids(),'Owned Hancom did not terminate'
                assert not (root/'outputs/RECOVERY.hwp').exists()
            # Allow successful Quit to finish asynchronously before another trial.
            deadline=time.monotonic()+10
            while hwp_process.hancom_pids() and time.monotonic()<deadline:time.sleep(.1)
            assert not hwp_process.hancom_pids()
            cases.append({'mode':mode,'expected_success':success,'status':'PASS','seconds':round(elapsed,2)})
    assert before==production_manifest()
    result={'status':'PASS','cases':cases,'source_unchanged':True,'api_calls':0,'scope':'Actual Tk approval, Python worker and Hancom COM. Stall/failure injected at COM HWP reimport; no real deadlock claim. Test dialogs mocked.'}
    (root/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
except BaseException:
    import traceback
    (root/'failure.json').write_text(json.dumps({'status':'FAIL','cases':cases,'dialogs':c.dialogs,'traceback':traceback.format_exc()},ensure_ascii=False,indent=2),encoding='utf-8')
    raise
finally:
    if not c.app.busy:c.close()
