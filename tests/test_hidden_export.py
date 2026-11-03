from pathlib import Path
from unittest.mock import Mock,patch
import base64,os,tempfile,unittest
from inspection import exporter
from inspection.core import Report,GENERAL,compose

@unittest.skipUnless(os.name=='nt','Windows file attributes required')
class HiddenExportTests(unittest.TestCase):
    def report(self):
        return Report('가상 저장 검증',tuple((k,'가상 값') for k in GENERAL),'• 가상 진행상황을 설명함.','• 가상 후속 일정을 안내함.','')
    def fake_hwp(self):
        report=self.report();xml=compose(exporter.template_text(),report);data=bytes.fromhex('D0CF11E0A1B11AE1')+b'synthetic transport only'
        hwp=Mock();hwp.PageCount=1;hwp.SetTextFile.return_value=True
        hwp.GetTextFile.side_effect=lambda fmt,opt:xml if fmt=='HWPML2X' else base64.b64encode(data).decode()
        return hwp,data
    def payload(self,folder):
        return {'approved':True,'report':self.report().as_dict(),'destination':str(Path(folder)/'가상_검증.hwp')}
    def test_no_staging_before_approval(self):
        with patch('inspection.exporter.stage_bytes') as stage,patch('inspection.exporter.destination') as dest:
            with self.assertRaises(PermissionError):exporter.worker({'approved':False})
        stage.assert_not_called();dest.assert_not_called()
    def test_hidden_file_created_without_any_directory(self):
        import pythoncom,win32file,win32con
        with tempfile.TemporaryDirectory() as folder:
            staged=exporter.stage_bytes(folder,b'verified bytes')
            self.assertEqual(list(Path(folder).iterdir()),[staged]);self.assertTrue(staged.is_file())
            self.assertTrue(win32file.GetFileAttributes(str(staged)) & win32con.FILE_ATTRIBUTE_HIDDEN)
            self.assertEqual(staged.read_bytes(),b'verified bytes')
    def test_success_has_hidden_stage_during_reimport_and_visible_final(self):
        import pythoncom,win32file,win32con
        hwp,data=self.fake_hwp();observations=[]
        with tempfile.TemporaryDirectory() as folder:
            def load(content,fmt,opt):
                entries=list(Path(folder).iterdir());self.assertFalse(any(p.is_dir() for p in entries))
                if fmt=='HWP':
                    self.assertEqual(len(entries),1);self.assertEqual(entries[0].suffix,'.tmp')
                    self.assertTrue(win32file.GetFileAttributes(str(entries[0])) & win32con.FILE_ATTRIBUTE_HIDDEN)
                    observations.append(True)
                return True
            hwp.SetTextFile.side_effect=load
            with patch('win32com.client.DispatchEx',return_value=hwp):result=exporter.worker(self.payload(folder))
            dest=Path(result['path']);self.assertEqual(list(Path(folder).iterdir()),[dest]);self.assertEqual(dest.read_bytes(),data)
            self.assertFalse(win32file.GetFileAttributes(str(dest)) & (win32con.FILE_ATTRIBUTE_HIDDEN|win32con.FILE_ATTRIBUTE_TEMPORARY))
            self.assertTrue(observations);self.assertTrue(result['reopened'])
    def test_failed_hancom_reimport_cleans_stage_and_keeps_original(self):
        import pythoncom,win32com.client
        hwp,_=self.fake_hwp();hwp.SetTextFile.side_effect=[True,False]
        with tempfile.TemporaryDirectory() as folder:
            original=Path(folder)/'original.txt';original.write_bytes(b'keep')
            with patch('win32com.client.DispatchEx',return_value=hwp):
                with self.assertRaises(RuntimeError):exporter.worker(self.payload(folder))
            self.assertEqual(list(Path(folder).iterdir()),[original]);self.assertEqual(original.read_bytes(),b'keep')
    def test_collision_after_verification_preserves_other_file(self):
        import pythoncom,win32com.client
        hwp,_=self.fake_hwp();real=exporter.publish_no_replace
        def collide(stage,dest):
            dest.write_bytes(b'existing user file');real(stage,dest)
        with tempfile.TemporaryDirectory() as folder,patch('win32com.client.DispatchEx',return_value=hwp),patch('inspection.exporter.publish_no_replace',side_effect=collide):
            with self.assertRaises(FileExistsError):exporter.worker(self.payload(folder))
            entries=list(Path(folder).iterdir());self.assertEqual(len(entries),1);self.assertEqual(entries[0].read_bytes(),b'existing user file')
    def test_failed_flush_cleans_created_file(self):
        import pythoncom,win32file
        with tempfile.TemporaryDirectory() as folder,patch('win32file.FlushFileBuffers',side_effect=PermissionError('synthetic storage failure')):
            with self.assertRaises(PermissionError):exporter.stage_bytes(folder,b'approved bytes')
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_native_write_denial_reports_windows_error_and_creates_nothing(self):
        import pythoncom,pywintypes,win32file
        with tempfile.TemporaryDirectory() as folder,patch('win32file.CreateFile',side_effect=pywintypes.error(5,'CreateFile','denied')):
            with self.assertRaises(PermissionError) as caught:exporter.stage_bytes(folder,b'approved')
            self.assertEqual(caught.exception.winerror,5);self.assertEqual(list(Path(folder).iterdir()),[])
