"""Read-only HWP input conversion in an isolated Hancom worker.

The temporary PDF is input preprocessing, never an approved result and never
written to the user's selected output folder. The original HWP is not saved.
"""
from pathlib import Path
import base64,json,subprocess,sys,tempfile

MAX_BYTES=30*1024*1024

def validate_source(path):
    path=Path(path)
    if path.suffix.lower()!='.hwp':raise ValueError('한글 사업계획서는 .hwp 파일로 첨부해 주세요.')
    if not path.is_file():raise ValueError('첨부할 HWP 파일에 접근할 수 없습니다.')
    if path.stat().st_size>MAX_BYTES:raise ValueError('HWP는 30MB 이하로 첨부해 주세요.')
    data=path.read_bytes()
    if len(data)>MAX_BYTES:raise ValueError('HWP는 30MB 이하로 첨부해 주세요.')
    if not data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):raise ValueError('실제 HWP 5 형식 파일이 아닙니다. 한글에서 .hwp로 다시 저장해 주세요.')
    return data

def convert_pdf(path,consume):
    # Validate before launching COM; worker also validates the source snapshot.
    data=validate_source(path)
    command=[sys.executable,'--hwp-input-worker'] if getattr(sys,'frozen',False) else [sys.executable,str(Path(__file__).resolve().parent.parent/'main.py'),'--hwp-input-worker']
    with tempfile.TemporaryDirectory(prefix='ai-inspection-input-') as folder:
        job=Path(folder);request=job/'request.json';response=job/'response.json';pdf=job/'input.pdf'
        request.write_text(json.dumps({'hwp':base64.b64encode(data).decode('ascii')}),encoding='utf-8')
        try:
            subprocess.run(command+[str(request),str(response)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except subprocess.TimeoutExpired:
            raise RuntimeError('HWP 읽기 시간이 초과됐습니다. 한글의 확인 창을 확인하고 다시 첨부해 주세요. 기존 첨부와 편집 내용은 유지됩니다.') from None
        try:result=json.loads(response.read_text(encoding='utf-8'))
        except (OSError,ValueError):raise RuntimeError('한글 변환 작업이 종료됐습니다. 한글 설치·자동화 연결을 확인해 주세요.') from None
        if not result.get('ok'):raise RuntimeError(result.get('error','HWP를 읽지 못했습니다.'))
        if not pdf.is_file() or not pdf.read_bytes().startswith(b'%PDF-'):raise RuntimeError('한글에서 PDF 변환본을 만들지 못했습니다.')
        prepared=consume(pdf)
        if prepared.page_count!=result.get('pages'):raise RuntimeError('HWP와 PDF 변환본의 쪽수가 다릅니다. 원본을 확인하고 PDF 사본으로 첨부해 주세요.')
        return prepared

def worker(request_path,stage=lambda value:None):
    stage('loading_com')
    import pythoncom,win32com.client
    job=Path(request_path).resolve().parent
    payload=json.loads(Path(request_path).read_text(encoding='utf-8'))
    data=base64.b64decode(payload['hwp'],validate=True)
    if len(data)>MAX_BYTES or not data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):raise ValueError('HWP 형식·크기를 확인해 주세요.')
    pythoncom.CoInitialize();hwp=None
    try:
        hwp=win32com.client.DispatchEx('HWPFrame.HwpObject');stage('com_ready')
        # PDF export may show a Hancom access confirmation. Keep this worker's
        # window visible so a legitimate prompt cannot remain hidden indefinitely.
        hwp.XHwpWindows.Item(0).Visible=True;stage('reading_hwp')
        if not hwp.SetTextFile(base64.b64encode(data).decode('ascii'),'HWP','insertfile'):
            raise ValueError('HWP를 읽지 못했습니다. 암호·보호 설정 또는 문서 손상을 확인해 주세요.')
        stage('hwp_loaded');pages=int(hwp.PageCount)
        if not 1<=pages<=250:raise ValueError('사업계획서는 1~250쪽 범위로 첨부해 주세요.')
        # Export the input to a private temporary PDF to preserve tables/images.
        # No registry, security module, original-file Save or result export call.
        stage('exporting_pdf')
        if not hwp.SaveAs(str(job/'input.pdf'),'PDF',''):raise ValueError('HWP의 PDF 변환을 완료하지 못했습니다.')
        stage('pdf_ready')
        return {'ok':True,'pages':pages}
    finally:
        if hwp is not None:
            try:hwp.Clear(1);hwp.Quit()
            except Exception:pass
        pythoncom.CoUninitialize()

def worker_main():
    def stage(value):
        Path(sys.argv[3]).with_name('stage.json').write_text(json.dumps({'stage':value}),encoding='utf-8')
    try:result=worker(sys.argv[2],stage)
    except ValueError as e:result={'ok':False,'error':str(e)}
    except Exception:result={'ok':False,'error':'한글 자동화로 HWP를 읽지 못했습니다. 한글 설치·COM 등록·확인 창을 확인해 주세요.'}
    Path(sys.argv[3]).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
