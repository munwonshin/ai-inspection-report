from pathlib import Path
from unittest.mock import patch
import tempfile,unittest,json
from inspection.desktop_shortcut import install,NAME,VERSION

class FakeLink:
    def __init__(self,path):
        self.path=Path(path);self.TargetPath='';self.Arguments='';self.WorkingDirectory='';self.IconLocation=''
        if self.path.exists():self.__dict__.update(json.loads(self.path.read_text()))
    def Save(self):
        self.path.write_text(json.dumps({k:v for k,v in vars(self).items() if k!='path'}))
class FakeShell:
    def CreateShortcut(self,path):return FakeLink(path)

class ShortcutTests(unittest.TestCase):
    def setup_files(self,folder):
        base=Path(folder);source=base/'한글 경로 배포';source.mkdir();(source/'AIInspectionReport.exe').write_bytes(b'verified-exe')
        (source/'_internal').mkdir();(source/'_internal/runtime.dll').write_bytes(b'runtime')
        (source/'private.hwp').write_bytes(b'private original')
        desktop=base/'redirected desktop';desktop.mkdir()
        return source,base/'LocalAppData/Programs/AIInspectionReport',desktop
    def test_copy_shortcut_and_preserve_business_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.setup_files(folder);r=install(source,base,desktop,FakeShell())
            target=Path(r['target']);self.assertEqual(target.read_bytes(),b'verified-exe')
            self.assertTrue((target.parent/'_internal/runtime.dll').is_file());self.assertFalse((target.parent/'private.hwp').exists())
            self.assertEqual((source/'private.hwp').read_bytes(),b'private original')
            link=FakeLink(r['shortcut']);self.assertEqual(link.WorkingDirectory,str(target.parent));self.assertEqual(link.Arguments,'')
    def test_does_not_overwrite_install_or_unrelated_shortcut(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.setup_files(folder);old=base/VERSION;old.mkdir(parents=True);(old/'keep.txt').write_text('keep')
            unrelated=desktop/(NAME+'.lnk');unrelated.write_text(json.dumps({'TargetPath':str(Path(folder)/'other.exe')}))
            before=unrelated.read_bytes();r=install(source,base,desktop,FakeShell())
            self.assertNotEqual(Path(r['target']).parent,old);self.assertNotEqual(Path(r['shortcut']),unrelated)
            self.assertEqual(unrelated.read_bytes(),before);self.assertEqual((old/'keep.txt').read_text(),'keep')
    def test_rerun_inside_installed_folder_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.setup_files(folder);first=install(source,base,desktop,FakeShell())
            second=install(Path(first['target']).parent,base,desktop,FakeShell())
            self.assertFalse(second['copied']);self.assertEqual(first['target'],second['target'])
            self.assertEqual(len(list(base.iterdir())),1)
    def test_failed_copy_no_shortcut_or_partial_install(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.setup_files(folder)
            with patch('inspection.desktop_shortcut.shutil.copytree',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):install(source,base,desktop,FakeShell())
            self.assertEqual(list(base.iterdir()),[]);self.assertEqual(list(desktop.iterdir()),[])
    def test_requires_unpacked_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.setup_files(folder);(source/'_internal').rename(source/'missing-runtime')
            with self.assertRaises(ValueError):install(source,base,desktop,FakeShell())
            self.assertFalse(base.exists());self.assertEqual(list(desktop.iterdir()),[])

    @unittest.skipUnless(__import__('sys').platform=='win32','Windows ACL regression')
    def test_installed_folder_inherits_parent_acl(self):
        import pythoncom,win32security
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.setup_files(folder)
            result=install(source,base,desktop,FakeShell())
            sd=win32security.GetFileSecurity(str(Path(result['target']).parent),win32security.DACL_SECURITY_INFORMATION)
            control,_=sd.GetSecurityDescriptorControl()
            self.assertFalse(control & win32security.SE_DACL_PROTECTED)
