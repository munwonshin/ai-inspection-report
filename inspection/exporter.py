"""No result or staging file is created before explicit approval."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from .core import Report, destination, compose, verify_xml

def resource_dir():
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))/'assets'

def template_text():
    p=resource_dir()/'template.hml'
    b=p.read_bytes()
    expected=(resource_dir()/'template.sha256').read_text().strip()
    if hashlib.sha256(b).hexdigest()!=expected:
        raise ValueError('양식 무결성 검사에 실패했습니다. 배포 파일을 다시 준비해 주세요.')
    return b.decode('utf-8-sig')

def save(report, folder, name, *, approved=False):
    # Must precede ALL file access, including directory creation.
    if approved is not True:
        raise PermissionError('사용자 승인 전에는 저장할 수 없습니다.')
    if report.missing() or not report.title.strip() or not report.findings.strip():
        raise ValueError('제목·본문과 필수 일반현황을 확인해 주세요.')
    dest=destination(folder,name)
    payload={'approved':True,'report':report.as_dict(),'destination':str(dest)}
    command=[sys.executable,'--hwp-worker'] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve().parent.parent/'main.py'),'--hwp-worker']
    with tempfile.TemporaryDirectory(prefix='ai-inspection-approved-job-') as jobdir:
        job=Path(jobdir)/'job.json'
        response=Path(jobdir)/'response.json'
        job.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        p=subprocess.run(command+[str(job),str(response)],stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            result=json.loads(response.read_text(encoding='utf-8'))
        except (ValueError,OSError):
            raise RuntimeError('한글 저장 작업이 비정상 종료됐습니다. 한글 창의 오류를 확인해 주세요. 편집 내용은 유지됩니다.') from None
    if not result.get('ok'):
        raise RuntimeError(result.get('error','한글 저장에 실패했습니다.'))
    return result

def worker(payload):
    if payload.get('approved') is not True:
        raise PermissionError('사용자 승인 전에는 저장할 수 없습니다.')
    d=payload['report']
    report=Report(d['title'],tuple(d['general'].items()),d['findings'],d['actions'],d['checks'])
    if report.missing() or not report.title.strip() or not report.findings.strip():
        raise ValueError('필수 입력이 없습니다.')
    raw=Path(payload['destination'])
    dest=destination(str(raw.parent),raw.name)
    if not dest.parent.is_dir():
        raise OSError('저장 폴더에 접근할 수 없습니다. 로컬·NAS 연결과 쓰기 권한을 확인해 주세요.')
    if dest.exists():
        raise FileExistsError('같은 이름의 파일이 있습니다. 파일명을 바꿔 주세요. 덮어쓰지 않았습니다.')
    xml=compose(template_text(),report)
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    hwp=None
    stage=None
    try:
        # Same-volume staging supports UNC paths and atomic no-replace publication.
        stage=Path(tempfile.mkdtemp(prefix='.ai-inspection-',dir=str(dest.parent)))
        staged=stage/'approved.hwp'
        with tempfile.TemporaryDirectory(prefix='ai-inspection-approved-') as local:
            hml=Path(local)/'approved.hml'
            hml.write_text(xml,encoding='utf-8-sig')
            hwp=win32com.client.DispatchEx('HWPFrame.HwpObject')
            hwp.XHwpWindows.Item(0).Visible=True
            if not hwp.Open(str(hml),'HWPML2X',''):
                raise RuntimeError('한글에서 승인 문서를 열지 못했습니다. 파일 접근 확인 창을 확인해 주세요.')
            if not hwp.SaveAs(str(staged),'HWP',''):
                raise RuntimeError('한글 HWP 저장이 취소되거나 실패했습니다. 편집 내용은 유지됩니다.')
            hwp.Clear(1)
            if not hwp.Open(str(staged),'HWP',''):
                raise RuntimeError('저장한 HWP를 한글에서 다시 열지 못했습니다. 최종 파일로 확정하지 않았습니다.')
            verify_xml(hwp.GetTextFile('HWPML2X',''),report)
            pages=int(hwp.PageCount)
            hwp.Clear(1)
            hwp.Quit()
            hwp=None
            with staged.open('rb') as f:
                if f.read(8)!=bytes.fromhex('D0CF11E0A1B11AE1'):
                    raise RuntimeError('실제 HWP 파일 형식 검증에 실패했습니다.')
            # Windows rename fails if the target appeared during COM processing.
            # Do not use replace(), which would overwrite that target.
            os.rename(str(staged),str(dest))
            return {'ok':True,'path':str(dest),'pages':pages,'reopened':True}
    finally:
        if hwp is not None:
            try:hwp.Clear(1); hwp.Quit()
            except Exception:pass
        if stage is not None:
            shutil.rmtree(stage,ignore_errors=True)
        pythoncom.CoUninitialize()

def worker_main():
    try:
        result=worker(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
    except FileExistsError:
        result={'ok':False,'error':'같은 이름의 파일이 있습니다. 파일명을 바꿔 주세요. 덮어쓰지 않았습니다.'}
    except (ValueError,PermissionError,RuntimeError) as e:
        result={'ok':False,'error':str(e)}
    except OSError as e:
        result={'ok':False,'error':f'파일 저장 실패(Windows 오류 {getattr(e,"winerror",None) or e.errno}). 경로·NAS 연결·쓰기 권한을 확인하고 다른 경로로 재시도해 주세요.'}
    except Exception:
        result={'ok':False,'error':'한글 자동화 오류입니다. 한글 설치·COM 등록·파일 접근 확인 창을 확인해 주세요. 편집 내용은 유지됩니다.'}
    Path(sys.argv[3]).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
