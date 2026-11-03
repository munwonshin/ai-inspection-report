"""Package only the clean build payload; never include user credentials or inputs."""
from pathlib import Path
import hashlib,json,re,sys,zipfile

root=Path(__file__).resolve().parents[1]
if len(sys.argv)!=3:raise SystemExit('Usage: package_release.py BUILD_FOLDER VERSION')
build=Path(sys.argv[1]).resolve();version=sys.argv[2]
if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise SystemExit('Invalid release version')
for name in ('AIInspectionReport.exe','_internal','바탕화면 아이콘 만들기.cmd','install-support.cs','THIRD_PARTY_NOTICES.md','licenses'):
    if not (build/name).exists():raise SystemExit('Missing distribution component: '+name)
if (build/'AIInspectionReport.exe').read_bytes()[:2]!=b'MZ':raise SystemExit('Not a Windows executable')
output=root/'release';output.mkdir(exist_ok=True)
archive=output/f'AIInspectionReport-{version}-windows-x64.zip'
guide="""AI 현장점검 결과서 — Windows 실행용

1. ZIP 전체를 풀어 주세요. EXE만 따로 옮기지 마세요.
2. AIInspectionReport 폴더의 '바탕화면 아이콘 만들기.cmd'를 실행하세요.
3. 바탕화면의 'AI 현장점검 결과서'로 실행하세요.
4. 프로그램의 API 설정에서 본인의 OpenAI API 키를 저장하고 연결을 확인하세요.

Windows 64비트와 한글 COM 자동화를 지원하는 한컴오피스가 필요합니다.
Python을 별도로 설치할 필요는 없습니다. 한컴오피스는 포함하지 않습니다.
새 Windows 사용자에게 API 키가 제공되지 않습니다. 기존 사용자의 키는 유지됩니다.
API 비용은 별도이며 입력 문서·회의록·초안이 AI 분석을 위해 전송됩니다.
사용자가 검토·승인한 뒤에만 결과 HWP를 저장합니다.
"""
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(build.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(build)
        if p.is_symlink() or p.suffix.lower() in ('.hwp','.hwpx','.pdf','.docx','.pptx','.xlsx','.log','.key'):
            raise SystemExit('Unexpected distribution file: '+str(rel))
        if p.name.lower() in ('preferences.json','job.json','response.json','auth.json','.env'):
            raise SystemExit('Private configuration must not be packaged')
        data=p.read_bytes()
        if re.search(rb'(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{30,}',data):raise SystemExit('Potential key in payload')
        z.writestr('AIInspectionReport/'+rel.as_posix(),data)
    z.writestr('AIInspectionReport/처음_사용하기.txt',guide.encode('utf-8-sig'))
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:raise SystemExit('Invalid ZIP CRC')
    if z.read('AIInspectionReport/AIInspectionReport.exe')!=(build/'AIInspectionReport.exe').read_bytes():raise SystemExit('EXE mismatch')
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(output/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
(output/'RELEASE_NOTES.md').write_text("""Windows 실행용 ZIP입니다. 아래 Assets에서 `AIInspectionReport-VERSION-windows-x64.zip`을 받아 전체 압축을 푼 뒤, 폴더 안의 **바탕화면 아이콘 만들기.cmd**를 실행하세요.

`Source code (zip)`과 저장소의 `Code → Download ZIP`은 소스용입니다. 설치용 ZIP을 선택하세요.

- Windows 64비트와 한글 COM 자동화를 지원하는 한컴오피스 필요
- Python 별도 설치 불필요. API 키 미포함, 각 사용자가 API 설정에서 입력
- 자동 검사는 단위 검사·빌드/소스 일치·패키지 구성 검사이며 실제 한글·NAS 동작은 PC별 확인 필요
""".replace('VERSION',version),encoding='utf-8')
print(json.dumps({'archive':archive.name,'bytes':archive.stat().st_size,'sha256':digest}),flush=True)
