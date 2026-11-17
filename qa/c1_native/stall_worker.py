"""Synthetic fault at real COM reimport, after ownership proof and stage write."""
import os,runpy,sys,time
from pathlib import Path
repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo))
from qa.c1_baseline.run_baseline import configure_dependencies
dll=configure_dependencies(Path(os.environ['C1_NATIVE_DEPS']))
from inspection import hwp_process
import win32com.client
real=win32com.client.DispatchEx
class Fault:
    def __init__(self,obj):self.obj=obj
    def __getattr__(self,name):return getattr(self.obj,name)
    def SetTextFile(self,text,fmt,opt):
        if fmt=='HWP':
            if os.environ['R028_FAULT']=='stall':time.sleep(90)
            if os.environ['R028_FAULT']=='failure':return False
        return self.obj.SetTextFile(text,fmt,opt)
def dispatch(*args,**kw):
    if hwp_process.hancom_pids():raise RuntimeError('Synthetic trial refuses any existing Hancom session')
    return Fault(real(*args,**kw))
win32com.client.DispatchEx=dispatch
import socket
def deny(*args,**kw):raise RuntimeError('Network forbidden in synthetic trial')
socket.socket.connect=deny;socket.getaddrinfo=deny
sys.argv=[str(repo/'main.py'),*sys.argv[1:]]
runpy.run_path(str(repo/'main.py'),run_name='__main__')
