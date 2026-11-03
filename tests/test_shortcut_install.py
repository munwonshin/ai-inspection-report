"""Exercise the actual installer commands against isolated paths, no EXE execution."""
from pathlib import Path
import os,shutil,subprocess,tempfile,unittest

@unittest.skipUnless(os.name=='nt','Windows PowerShell and WScript.Shell required')
class NativeInstallerTests(unittest.TestCase):
    def run_install(self,source,base,desktop):
        text=(Path(__file__).resolve().parents[1]/'바탕화면 아이콘 만들기.cmd').read_text(encoding='utf-8')
        block=text.split('powershell.exe -NoLogo -NoProfile -Command ^\n',1)[1].split('\nif errorlevel',1)[0]
        lines=[line.strip().removesuffix(' ^').strip() for line in block.strip().splitlines()]
        self.assertTrue(all(x.startswith('"') and x.endswith('"') for x in lines))
        script=' '.join(x[1:-1] for x in lines)
        expression="$base=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Programs\\AIInspectionReport';"
        self.assertEqual(script.count(expression),1)
        script=script.replace(expression,"$base='"+str(base).replace("'","''")+"';")
        expression="$desktop=$shell.SpecialFolders('Desktop');"
        self.assertEqual(script.count(expression),1)
        script=script.replace(expression,"$desktop='"+str(desktop).replace("'","''")+"';")
        env=dict(os.environ,AIR_INSTALL_SOURCE=str(source))
        result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-Command',script],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        return result
    def fixture(self,folder):
        root=Path(folder);source=root/"가상 '배포' & (테스트)";source.mkdir()
        (source/'AIInspectionReport.exe').write_bytes(b'MZ synthetic non-executable fixture')
        (source/'_internal').mkdir();(source/'_internal/runtime.dll').write_bytes(b'synthetic runtime')
        (source/'private.hwp').write_bytes(b'private original')
        shutil.copy2(Path(__file__).resolve().parents[1]/'install-support.cs',source/'install-support.cs')
        desktop=root/'바탕 화면';desktop.mkdir()
        return source,root/'programs',desktop
    def target(self,link):
        import pythoncom
        from win32com.shell import shell
        pythoncom.CoInitialize();shortcut=None;persist=None
        try:
            shortcut=pythoncom.CoCreateInstance(shell.CLSID_ShellLink,None,pythoncom.CLSCTX_INPROC_SERVER,shell.IID_IShellLink)
            persist=shortcut.QueryInterface(pythoncom.IID_IPersistFile);persist.Load(str(link))
            return Path(shortcut.GetPath(4)[0])
        finally:persist=None;shortcut=None;pythoncom.CoUninitialize()
    def test_copies_payload_without_executing_it_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.fixture(folder);r=self.run_install(source,base,desktop)
            self.assertEqual(r.returncode,0,r.stdout)
            link=desktop/'AI 현장점검 결과서.lnk';self.assertTrue(link.is_file())
            target=self.target(link);self.assertEqual(target.read_bytes(),(source/'AIInspectionReport.exe').read_bytes())
            self.assertEqual((target.parent/'_internal/runtime.dll').read_bytes(),b'synthetic runtime')
            self.assertFalse((target.parent/'private.hwp').exists());self.assertTrue((source/'private.hwp').is_file())
            import pythoncom,win32security
            sd=win32security.GetFileSecurity(str(target.parent),win32security.DACL_SECURITY_INFORMATION)
            self.assertFalse(sd.GetSecurityDescriptorControl()[0] & win32security.SE_DACL_PROTECTED)
    def test_rerun_does_not_overwrite_old_install(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.fixture(folder)
            base=base.with_name('programs with spaces');base.mkdir()
            import ctypes
            short=ctypes.create_unicode_buffer(32768)
            if ctypes.windll.kernel32.GetShortPathNameW(str(base),short,len(short)):
                base=Path(short.value)
            self.assertEqual(self.run_install(source,base,desktop).returncode,0)
            first=self.target(desktop/'AI 현장점검 결과서.lnk');(first.parent/'keep.txt').write_text('keep')
            self.assertEqual(self.run_install(source,base,desktop).returncode,0)
            second=self.target(desktop/'AI 현장점검 결과서.lnk')
            self.assertNotEqual(first,second);self.assertEqual((first.parent/'keep.txt').read_text(),'keep')
    def test_failed_copy_cleans_only_new_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.fixture(folder);(source/'AIInspectionReport.exe').unlink()
            base.mkdir();old=base/'old';old.mkdir();(old/'keep.txt').write_text('keep')
            result=self.run_install(source,base,desktop)
            self.assertEqual(result.returncode,1);self.assertEqual(list(desktop.iterdir()),[])
            self.assertEqual(list(base.iterdir()),[old]);self.assertEqual((old/'keep.txt').read_text(),'keep')

    def test_unrelated_shortcut_remains_unchanged(self):
        import pythoncom
        from win32com.shell import shell
        with tempfile.TemporaryDirectory() as folder:
            source,base,desktop=self.fixture(folder);link=desktop/'AI 현장점검 결과서.lnk'
            pythoncom.CoInitialize();shortcut=None;persist=None
            try:
                shortcut=pythoncom.CoCreateInstance(shell.CLSID_ShellLink,None,pythoncom.CLSCTX_INPROC_SERVER,shell.IID_IShellLink)
                shortcut.SetPath(os.environ['COMSPEC']);persist=shortcut.QueryInterface(pythoncom.IID_IPersistFile);persist.Save(str(link),0)
            finally:persist=None;shortcut=None;pythoncom.CoUninitialize()
            before=link.read_bytes();self.assertEqual(self.run_install(source,base,desktop).returncode,0)
            self.assertEqual(link.read_bytes(),before);self.assertEqual(len(list(desktop.glob('*.lnk'))),2)
