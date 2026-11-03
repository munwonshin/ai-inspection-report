"""Per-user installation and desktop shortcut; no admin, API or report writes."""
from pathlib import Path
import hashlib,shutil,sys,uuid

VERSION='0.4.25'
NAME='AI 현장점검 결과서'

def inside(path,parent):
    return Path(path).resolve().is_relative_to(Path(parent).resolve())

def unique_path(folder,name,suffix=''):
    candidate=folder/(name+suffix);number=2
    while candidate.exists():
        candidate=folder/(name+' ('+str(number)+')'+suffix);number+=1
    return candidate

def install(source,base,desktop,shell):
    source=Path(source).resolve();base=Path(base).resolve();desktop=Path(desktop).resolve()
    exe=source/'AIInspectionReport.exe'
    if not exe.is_file() or not (source/'_internal').is_dir():
        raise ValueError('ZIP 전체를 먼저 풀어 주세요. EXE와 _internal 폴더가 함께 있어야 합니다.')
    if not desktop.is_dir():raise OSError('바탕화면 폴더에 접근할 수 없습니다.')
    stage=None;installed=source
    try:
        if not inside(source,base):
            base.mkdir(parents=True,exist_ok=True)
            # Executable payload must inherit the normal per-user install ACL.
            # mkdtemp's protected Windows mode 0700 can deny Explorer execution.
            stage=base/('.install-'+uuid.uuid4().hex)
            stage.mkdir(mode=0o777)
            # Copy only application payload, never work documents beside the EXE.
            shutil.copy2(exe,stage/exe.name)
            shutil.copytree(source/'_internal',stage/'_internal')
            for name in ('바탕화면 아이콘 만들기.cmd','install-support.cs','THIRD_PARTY_NOTICES.md','사용안내_0.4.25.md'):
                if (source/name).is_file():shutil.copy2(source/name,stage/name)
            if (source/'licenses').is_dir():shutil.copytree(source/'licenses',stage/'licenses')
            if hashlib.sha256(exe.read_bytes()).digest()!=hashlib.sha256((stage/exe.name).read_bytes()).digest():
                raise OSError('설치 파일의 복사 검증에 실패했습니다.')
            installed=unique_path(base,VERSION)
            # Never replace an existing install, including another user's files.
            stage.rename(installed);stage=None
        target=installed/exe.name
        link=desktop/(NAME+'.lnk')
        if link.exists():
            try:owned=inside(shell.CreateShortcut(str(link)).TargetPath,base)
            except Exception:owned=False
            if not owned:link=unique_path(desktop,NAME+' '+VERSION,'.lnk')
        shortcut=shell.CreateShortcut(str(link))
        shortcut.TargetPath=str(target);shortcut.Arguments='';shortcut.WorkingDirectory=str(installed)
        shortcut.IconLocation=str(target)+',0';shortcut.Description='AI 현장점검 결과서 작성 프로그램'
        shortcut.WindowStyle=1;shortcut.Save()
        check=shell.CreateShortcut(str(link))
        if Path(check.TargetPath).resolve()!=target.resolve() or check.Arguments:
            raise OSError('바로가기 대상 검증에 실패했습니다.')
        return {'shortcut':str(link),'target':str(target),'version':VERSION,'copied':installed!=source}
    finally:
        if stage is not None:
            # Only a newly created staging folder inside this app's install root.
            if inside(stage,base) and stage.name.startswith('.install-'):
                shutil.rmtree(stage,ignore_errors=True)

def create():
    import pythoncom,win32com.client
    if not getattr(sys,'frozen',False):raise ValueError('빌드된 프로그램에서 실행해 주세요.')
    pythoncom.CoInitialize();shell=None
    try:
        shell=win32com.client.Dispatch('WScript.Shell')
        desktop=shell.SpecialFolders('Desktop')
        local=shell.ExpandEnvironmentStrings('%LOCALAPPDATA%')
        if not local or '%' in local:raise OSError('사용자 설치 경로를 확인할 수 없습니다.')
        return install(Path(sys.executable).parent,Path(local)/'Programs'/'AIInspectionReport',desktop,shell)
    finally:
        shell=None
        pythoncom.CoUninitialize()

def main():
    import ctypes
    try:
        result=create()
        ctypes.windll.user32.MessageBoxW(None,'바탕화면에 “'+NAME+'” 아이콘을 만들었습니다.\n\n다음부터 이 아이콘을 두 번 클릭해 실행하세요.\nAPI 설정과 기존 자료는 유지됩니다.',NAME,0x40)
    except Exception:
        ctypes.windll.user32.MessageBoxW(None,'바로가기를 만들지 못했습니다.\nZIP 전체를 푼 상태인지, 저장 공간과 사용자 설치 폴더·바탕화면 쓰기 권한을 확인해 주세요.\n기존 프로그램과 업무 자료는 삭제하지 않았습니다.',NAME,0x10)
