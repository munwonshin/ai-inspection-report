"""Real Tk startup with actual API transport mapping and synthetic credentials."""
import sys,time,io,json,urllib.error,ssl
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from inspection.ui import App
from inspection import api

completed={'status':'completed','output':[{'content':[{'type':'output_text','text':'OK'}]}],'usage':{'input_tokens':1,'output_tokens':1}}
results=[]
for case,failures in [('temporary_timeout',[TimeoutError('synthetic-private')]),('persistent_timeout',[TimeoutError('synthetic-private'),TimeoutError('synthetic-private')]),('certificate',[urllib.error.URLError(ssl.SSLCertVerificationError(1,'synthetic-private'))])]:
    response=io.BytesIO(json.dumps(completed).encode())
    sequence=failures+[response]
    with patch('inspection.ui.vault.read',return_value='synthetic-key'),patch('inspection.ui.vault.save') as save_key,patch('inspection.ui.vault.delete') as delete_key,patch('urllib.request.urlopen',side_effect=sequence) as transport,patch('inspection.api.time.sleep'),patch('inspection.ui.exporter.save') as export:
        root=tk.Tk();root.withdraw();app=App(root,restore_preferences=False)
        app.minutes.insert('1.0','가상 회의록 유지');app.findings.insert('1.0','가상 직접 편집 유지')
        errors=[];root.report_callback_exception=lambda *args:errors.append(str(args))
        until=time.monotonic()+10
        while time.monotonic()<until:
            root.update();time.sleep(.01)
            if transport.called and not app.busy:break
        assert not app.busy
        assert app.connected==(case=='temporary_timeout')
        assert transport.call_count==(1 if case=='certificate' else 2)
        if case=='persistent_timeout':assert '대기 시간' in app.status.get()
        if case=='certificate':assert '인증서' in app.status.get()
        assert app.get(app.minutes)=='가상 회의록 유지' and app.get(app.findings)=='가상 직접 편집 유지'
        assert 'synthetic-private' not in app.status.get() and 'synthetic-key' not in app.status.get()
        save_key.assert_not_called();delete_key.assert_not_called();export.assert_not_called();assert not errors
        for timer in root.tk.call('after','info'):root.after_cancel(timer)
        root.destroy();results.append(case)
print('API_TRANSPORT_TK_RECOVERY_AND_INPUT_KEY_PRESERVATION_OK '+json.dumps(results),flush=True)
