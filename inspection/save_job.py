"""Bounded worker lifetime and parent-only publication of verified HWP bytes."""
import json,subprocess
from pathlib import Path
from . import hwp_process

SAVE_TIMEOUT_SECONDS=120


def identity(path):
    stat=Path(path).stat()
    return [stat.st_dev,stat.st_ino]


def cleanup_stage(path,expected):
    try:
        if identity(path)==expected:Path(path).unlink()
    except FileNotFoundError:pass


def run(command,job,response,*,timeout=SAVE_TIMEOUT_SECONDS):
    if timeout<=0:raise ValueError('저장 제한 시간은 양수여야 합니다.')
    owner=Path(job).parent/'owner.json'
    process=subprocess.Popen(command+[str(job),str(response)],stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Stop the Python worker first: it can never publish a late result.
        if process.poll() is None:process.kill()
        process.wait(timeout=5)
        cleaned=True
        try:
            info=json.loads(owner.read_text(encoding='utf-8'))
            cleaned=hwp_process.terminate_owned(info)
        except FileNotFoundError:cleaned=False  # Dispatch did not prove ownership: do not guess.
        except Exception:cleaned=False
        detail='' if cleaned else ' 작업 한글 창의 자동 정리가 확인되지 않았습니다. 해당 창을 확인한 후 재시도해 주세요.'
        raise RuntimeError('한글 저장 제한 시간을 초과했습니다. 파일 접근 확인 창도 확인해 주세요. 편집 내용과 기존 파일은 유지됩니다.'+detail) from None
    try:result=json.loads(Path(response).read_text(encoding='utf-8'))
    except (ValueError,OSError):
        cleanup_owner(owner)
        raise RuntimeError('한글 저장 작업이 비정상 종료됐습니다. 편집 내용은 유지됩니다. 다시 저장할 수 있습니다.') from None
    if process.returncode or not isinstance(result,dict) or not result.get('ok'):
        cleanup_owner(owner)
        raise RuntimeError(result.get('error','한글 저장에 실패했습니다.') if isinstance(result,dict) else '한글 저장 응답이 올바르지 않습니다.')
    return result


def cleanup_owner(owner):
    try:return hwp_process.terminate_owned(json.loads(Path(owner).read_text(encoding='utf-8')))
    except (OSError,ValueError,KeyError):return False
