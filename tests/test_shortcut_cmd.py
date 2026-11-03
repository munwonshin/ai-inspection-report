"""Run the actual CMD guards without installing software or opening a GUI."""
from pathlib import Path
import os,shutil,subprocess,tempfile,unittest

@unittest.skipUnless(os.name=='nt','Windows CMD required')
class ShortcutCmdTests(unittest.TestCase):
    def run_guard(self,files):
        script=Path(__file__).resolve().parents[1]/'바탕화면 아이콘 만들기.cmd'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'가상 배포 (시험) & 공백';root.mkdir()
            target=root/script.name;shutil.copy2(script,target)
            for name in files:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'not an executable')
            result=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c','call',str(target)],input=b'\r\n',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
            self.assertNotIn(b'LAUNCH_FAILED',result.stdout)
            return result
    def test_source_zip_gets_explanation_without_starting_missing_exe(self):
        result=self.run_guard([])
        self.assertEqual(result.returncode,2,result.stdout.decode('utf-8',errors='replace'));self.assertIn(b'SOURCE_ZIP',result.stdout)
    def test_exe_alone_rejected_before_launch(self):
        result=self.run_guard(['AIInspectionReport.exe'])
        self.assertEqual(result.returncode,3,result.stdout.decode('utf-8',errors='replace'));self.assertIn(b'MISSING_RUNTIME',result.stdout)
    def test_built_distribution_checks_its_runtime(self):
        result=self.run_guard(['dist/AIInspectionReport/AIInspectionReport.exe'])
        self.assertEqual(result.returncode,3,result.stdout.decode('utf-8',errors='replace'));self.assertIn(b'MISSING_RUNTIME',result.stdout)
