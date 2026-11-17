import json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from inspection import save_job,hwp_process


class SaveSupervisionTests(unittest.TestCase):
    def test_invalid_completion_never_publishes_and_cleans_owned_stage(self):
        from inspection import exporter
        from inspection.core import Report,GENERAL
        report=Report('합성 검사',tuple((k,'합성 값') for k in GENERAL),'합성 본문','합성 후속','')
        with tempfile.TemporaryDirectory() as folder,patch('inspection.save_job.run',return_value={'ok':True,'sha256':'unused'}),patch('inspection.exporter.publish_no_replace') as publish:
            with self.assertRaisesRegex(RuntimeError,'완료 응답'):exporter.save(report,folder,'synthetic',approved=True)
            self.assertEqual(list(Path(folder).iterdir()),[])
        publish.assert_not_called()

    def test_duplicate_stops_before_stage_or_worker(self):
        from inspection import exporter
        from inspection.core import Report,GENERAL
        report=Report('합성 검사',tuple((k,'합성 값') for k in GENERAL),'합성 본문','합성 후속','')
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'synthetic.hwp';dest.write_bytes(b'original')
            with patch('inspection.exporter.stage_bytes') as stage,patch('inspection.save_job.run') as run:
                with self.assertRaises(FileExistsError):exporter.save(report,folder,'synthetic',approved=True)
            stage.assert_not_called();run.assert_not_called();self.assertEqual(dest.read_bytes(),b'original')

    def test_timeout_kills_only_worker_and_proven_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            job=Path(folder)/'job.json';response=Path(folder)/'response.json'
            info={'pid':123,'created':4.0,'image':'hwp.exe'}
            (Path(folder)/'owner.json').write_text(json.dumps(info))
            process=Mock();process.wait.side_effect=[subprocess.TimeoutExpired('worker',.01),0];process.poll.return_value=None
            with patch('inspection.save_job.subprocess.Popen',return_value=process),patch('inspection.save_job.hwp_process.terminate_owned',return_value=True) as cleanup:
                with self.assertRaisesRegex(RuntimeError,'제한 시간'):save_job.run(['worker'],job,response,timeout=.01)
            cleanup.assert_called_once_with(info);process.kill.assert_called_once()

    def test_unknown_owner_never_terminates_hancom(self):
        with tempfile.TemporaryDirectory() as folder:
            process=Mock();process.wait.side_effect=[subprocess.TimeoutExpired('worker',.01),0];process.poll.return_value=None
            with patch('inspection.save_job.subprocess.Popen',return_value=process),patch('inspection.save_job.hwp_process.terminate_owned') as cleanup:
                with self.assertRaises(RuntimeError):save_job.run(['worker'],Path(folder)/'job',Path(folder)/'response',timeout=.01)
            cleanup.assert_not_called()

    def test_successful_retry_after_timeout(self):
        with tempfile.TemporaryDirectory() as folder:
            job=Path(folder)/'job';response=Path(folder)/'response'
            failed=Mock();failed.wait.side_effect=[subprocess.TimeoutExpired('worker',.01),0];failed.poll.return_value=None
            succeeded=Mock();succeeded.returncode=0
            with patch('inspection.save_job.subprocess.Popen',side_effect=[failed,succeeded]):
                with self.assertRaises(RuntimeError):save_job.run(['worker'],job,response,timeout=.01)
                response.write_text(json.dumps({'ok':True,'pages':1}))
                self.assertEqual(save_job.run(['worker'],job,response,timeout=1)['pages'],1)

    def test_pid_reuse_or_different_image_is_not_killed(self):
        old={'pid':123,'created':4.,'image':'hwp.exe'};handle=Mock()
        with patch('inspection.hwp_process.process_info',return_value=(handle,{**old,'created':5.})),patch('win32api.TerminateProcess') as kill:
            self.assertFalse(hwp_process.terminate_owned(old))
        kill.assert_not_called();handle.Close.assert_called_once()

    def test_replaced_stage_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'stage';path.write_bytes(b'keep')
            save_job.cleanup_stage(path,[-1,-1]);self.assertEqual(path.read_bytes(),b'keep')

    def test_actual_python_worker_timeout_does_not_publish(self):
        import sys
        with tempfile.TemporaryDirectory() as folder:
            # A real child process sleeps; no Hancom or network is used.
            with self.assertRaises(RuntimeError):
                save_job.run([sys.executable,'-c','import time;time.sleep(10)'],Path(folder)/'job',Path(folder)/'response',timeout=.1)
            self.assertEqual(list(Path(folder).iterdir()),[])
