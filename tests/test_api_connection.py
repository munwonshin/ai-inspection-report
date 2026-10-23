import io,json,ssl,socket,http.client,urllib.error,unittest
from unittest.mock import patch
from inspection import api

class ApiConnectionChecks(unittest.TestCase):
    def test_transport_errors_are_distinct_and_do_not_expose_raw_messages(self):
        cases=[(FileNotFoundError('fake-secret'),'tls_files',False),(TimeoutError('fake-secret'), 'timeout',True),(urllib.error.URLError(TimeoutError('fake-secret')),'timeout',True),
               (socket.gaierror(11001,'fake-secret'),'dns',True),(ConnectionResetError(10054,'fake-secret'),'connection_reset',True),
               (http.client.IncompleteRead(b'fake-secret'),'connection_reset',True),
               (ssl.SSLCertVerificationError(1,'fake-secret'),'certificate',False),(ssl.SSLError(1,'fake-secret'),'tls',False),
               (urllib.error.URLError(OSError('fake-secret')),'network',True)]
        for error,kind,retryable in cases:
            with self.subTest(kind=kind),patch('urllib.request.urlopen',side_effect=error) as call:
                with self.assertRaises(api.ApiFailure) as caught:api.request('synthetic-key',{'model':api.MODEL})
                self.assertEqual(caught.exception.kind,kind);self.assertEqual(caught.exception.retryable,retryable)
                self.assertNotIn('fake-secret',str(caught.exception));self.assertNotIn('synthetic-key',str(caught.exception))
                self.assertEqual(call.call_count,1)

    def test_connection_retries_once_then_succeeds_with_30_second_limit(self):
        transient=api.ApiFailure('synthetic',kind='timeout',retryable=True)
        with patch('inspection.api.request',side_effect=[transient,('OK',{'total_tokens':16})]) as request,patch('inspection.api.time.sleep') as sleep:
            self.assertEqual(api.connection('synthetic-key'),{'total_tokens':16})
            self.assertEqual(request.call_count,2)
            self.assertTrue(all(c.kwargs['timeout']==30 for c in request.call_args_list));sleep.assert_called_once_with(1)

    def test_connection_retry_is_bounded_and_auth_certificate_not_retried(self):
        for retryable,kind in [(True,'connection_reset'),(False,'certificate'),(False,'http_401'),(False,'http_429')]:
            failure=api.ApiFailure('synthetic',kind=kind,retryable=retryable)
            with self.subTest(kind=kind),patch('inspection.api.request',side_effect=failure) as request,patch('inspection.api.time.sleep'):
                with self.assertRaises(api.ApiFailure):api.connection('synthetic-key')
                self.assertEqual(request.call_count,2 if retryable else 1)

    def test_http_error_retry_eligibility_does_not_expose_response_body(self):
        for code in (400,401,403,404,408,429,500,502,503,504):
            error=urllib.error.HTTPError('https://api.openai.com/v1/responses',code,'fake-secret',{},io.BytesIO(b'fake-secret'))
            with self.subTest(code=code),patch('urllib.request.urlopen',side_effect=error):
                with self.assertRaises(api.ApiFailure) as caught:api.request('synthetic-key',{'model':api.MODEL})
                self.assertEqual(caught.exception.retryable,code in (408,500,502,503,504))
                self.assertNotIn('fake-secret',str(caught.exception))

    def test_partial_stream_failure_never_retries_report_request(self):
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def __iter__(self):
                yield b'data: {"type":"response.output_text.delta","delta":"partial"}\n'
                yield b'\n'
                raise ConnectionResetError(10054,'fake-secret')
        chunks=[]
        with patch('urllib.request.urlopen',return_value=Stream()) as request:
            with self.assertRaises(api.ApiFailure) as caught:api.request('synthetic-key',{'model':api.MODEL},chunks.append)
            self.assertEqual(request.call_count,1);self.assertEqual(chunks,['partial'])
            self.assertEqual(caught.exception.kind,'connection_reset')
