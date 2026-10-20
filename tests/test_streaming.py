import io,json,unittest
from unittest.mock import patch
from inspection import api
from inspection.core import filename
from inspection.streaming import events,preview

def wire(items):
    return io.BytesIO(b''.join(('data: '+json.dumps(x,ensure_ascii=False)+'\n\n').encode() for x in items))

class StreamingTests(unittest.TestCase):
    def test_windows_names(self):
        for name in ['현장점검_결과서','가상_2026-10-20 (검수)','x1_f0']:
            self.assertEqual(filename(name),name+'.hwp')
        for char in '<>:"/\\|?*\x00\x1f':
            with self.assertRaises(ValueError):filename('가상'+char+'결과')

    def test_every_json_character_boundary(self):
        body={'findings':'가상 설명 "인용"\n진행 중 😀','actions':'안내 없음','checks':'확인 필요'}
        for ascii_mode in [False,True]:
            text=json.dumps(body,ensure_ascii=ascii_mode)
            last=''
            for i in range(len(text)+1):
                current=preview(text[:i]);self.assertTrue(current.startswith(last));last=current
            self.assertIn(body['findings'],last)
            self.assertNotIn('"findings"',last)

    def test_nested_evidence_not_displayed(self):
        self.assertEqual(preview('{"general":{"findings":"숨김"},"findings":"가상'), '현장 점검·확인 사항\n가상')

    def test_stream_completed_and_usage(self):
        text=json.dumps({'findings':'가상','actions':'없음','checks':''},ensure_ascii=False)
        result={'status':'completed','output':[{'content':[{'type':'output_text','text':text}]}],'usage':{'input_tokens':2,'output_tokens':3}}
        stream=wire([{'type':'response.output_text.delta','delta':text[:10]},{'type':'response.output_text.delta','delta':text[10:]},{'type':'response.completed','response':result}])
        chunks=[]
        with patch('urllib.request.urlopen',return_value=stream) as call:
            received,usage=api.request('fake-secret',{'model':api.MODEL},chunks.append)
        self.assertEqual(received,text);self.assertEqual(''.join(chunks),text)
        self.assertEqual(usage['output_tokens'],3)
        self.assertTrue(json.loads(call.call_args.args[0].data)['stream'])

    def test_interrupted_and_failed_never_complete(self):
        for end in [[],[{'type':'response.failed'}],[{'type':'response.incomplete'}]]:
            with patch('urllib.request.urlopen',return_value=wire([{'type':'response.output_text.delta','delta':'partial'}]+end)):
                with self.assertRaises(api.ApiFailure):api.request('fake',{'model':api.MODEL},lambda d:None)

    def test_sse_comments_and_multiline(self):
        self.assertEqual(list(events(io.BytesIO(b': heartbeat\n\ndata: {"type":\ndata: "test"}\n\n'))),[{'type':'test'}])
