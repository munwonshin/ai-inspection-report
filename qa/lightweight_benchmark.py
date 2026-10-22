import sys,time,json,hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
import tkinter as tk
from inspection.ui import App
from inspection import ui
root=tk.Tk();root.withdraw();app=App(root,restore_api=False)
body={'findings':'가상 현장 확인 사항임.\n'*1000,'actions':'가상 안내함.','checks':'가상 확인 필요.'}
encoded=json.dumps(body,ensure_ascii=False)
app.ai_started=time.monotonic();app.pending_request={'kind':'user','text':'가상 시험','status':'pending'};app.messages.append(app.pending_request)
app.render_conversation();app.busy=True
count={'preview':0,'status_writes':0,'text_deletes':0}
real=ui.preview
def counted(s):count['preview']+=1;return real(s)
app.status.trace_add('write',lambda *args:count.__setitem__('status_writes',count['status_writes']+1))
real_delete=app.conversation.delete
def delete(*a):count['text_deletes']+=1;return real_delete(*a)
app.conversation.delete=delete
started=time.perf_counter()
with patch.object(ui,'preview',counted),patch.object(ui.time,'monotonic',return_value=100.0):
    app.ai_started=100.0
    # Same network pattern: bursts, followed by waiting ticks and paced drain.
    for tick in range(600):
        if tick<100:
            app.stream_queue.put(encoded[len(encoded)*tick//100:len(encoded)*(tick+1)//100])
        app.poll()
elapsed=time.perf_counter()-started
assert app.stream_visible==real(encoded)
assert app.snapshot().findings==''
for timer in root.tk.call('after','info'):root.after_cancel(timer)
root.destroy()
result={'seconds':elapsed,**count,'ticks':600,'preview_sha256':hashlib.sha256(app.stream_visible.encode()).hexdigest()}
Path(sys.argv[2]).write_text(json.dumps(result),encoding='utf-8');print(json.dumps(result))
