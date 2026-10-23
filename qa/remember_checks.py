"""Synthetic credentials only; no real vault writes, no network or HWP."""
import sys,time,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
from inspection import api

def instance():
    root=tk.Tk();root.withdraw();app=App(root,restore_preferences=False)
    until=time.monotonic()+5
    while time.monotonic()<until:
        root.update();time.sleep(.01)
        if called[0] and not app.busy:break
    assert called[0] and not app.busy
    return root,app
def dispose(root):
    for timer in root.tk.call('after','info'):root.after_cancel(timer)
    root.destroy()
results=[]
for case,key,error in [('saved','synthetic-not-real',False),('empty','',False),('network_failure','synthetic-not-real',True)]:
    called=[False]
    def read():called[0]=True;return key
    with patch('inspection.ui.vault.read',side_effect=read),patch('inspection.ui.vault.delete') as delete,patch('inspection.ui.api.connection',side_effect=api.ApiFailure('가상 네트워크 오류') if error else None,return_value={'total_tokens':4}) as connection,patch('inspection.ui.metadata.extract') as metadata,patch('inspection.ui.exporter.save') as save,patch('inspection.ui.messagebox.showerror') as popup:
        root,app=instance()
        assert app.connected==(bool(key) and not error)
        assert connection.call_count==int(bool(key))
        assert key not in app.status.get() if key else True
        metadata.assert_not_called();save.assert_not_called();delete.assert_not_called();popup.assert_not_called()
        if error:assert '키는 삭제하지 않았습니다' in app.status.get()
        dispose(root)
        if case=='saved':
            called[0]=False;root,app=instance();assert app.connected and connection.call_count==2;dispose(root)
        results.append(case)
print('REMEMBER_STARTUP_MOCK_CHECKS_OK '+json.dumps(results),flush=True)
