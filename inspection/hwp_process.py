"""Identify a new automation-owned Hancom process; never kill by image name."""
from pathlib import Path
import ctypes
from ctypes import wintypes


def process_info(pid, *, terminate=False):
    import win32api, win32process
    handle=win32api.OpenProcess(0x1000|0x100000|(1 if terminate else 0),False,pid)
    try:
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.QueryFullProcessImageNameW.argtypes=(wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD))
        name=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(name))
        if not kernel.QueryFullProcessImageNameW(int(handle),0,name,ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return handle,{'pid':int(pid),'image':Path(name.value).name.lower(),
            'created':win32process.GetProcessTimes(handle)['CreationTime'].timestamp()}
    except BaseException:
        handle.Close();raise


def hancom_pids():
    import win32process
    found=set()
    for pid in win32process.EnumProcesses():
        try:handle,info=process_info(pid)
        except Exception:continue
        try:
            if info['image']=='hwp.exe':found.add(pid)
        finally:handle.Close()
    return found


def identify(obj,before,started):
    import win32gui,win32process
    hwnd=int(obj.XHwpWindows.Item(0).WindowHandle)
    if not win32gui.IsWindow(hwnd):raise RuntimeError('한글 작업 창의 소유권을 확인할 수 없습니다.')
    _,pid=win32process.GetWindowThreadProcessId(hwnd)
    handle,info=process_info(pid)
    try:
        if pid in before or info['image']!='hwp.exe' or info['created']<started:
            raise RuntimeError('독립된 한글 저장 세션을 확인하지 못했습니다. 기존 한글 창은 변경하지 않았습니다.')
        return info
    finally:handle.Close()


def terminate_owned(info):
    """Keep the validated handle open through termination (PID reuse safe)."""
    import win32api,win32event
    try:handle,current=process_info(info['pid'],terminate=True)
    except Exception:
        return info['pid'] not in hancom_pids()
    try:
        if current!=info or current['image']!='hwp.exe':return False
        if win32event.WaitForSingleObject(handle,0)==0:return True
        win32api.TerminateProcess(handle,1)
        return win32event.WaitForSingleObject(handle,5000)==0
    finally:handle.Close()
