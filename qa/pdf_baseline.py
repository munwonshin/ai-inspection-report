"""Every page is preserved: ordinary text as text; visual/uncertain pages as PDF."""
from dataclasses import dataclass
from pathlib import Path
import io

@dataclass(frozen=True)
class PreparedDocument:
    local_text: str
    api_text: str
    visual_pdf: bytes | None
    page_count: int
    visual_pages: tuple
    original_bytes: bytes
    @property
    def mode_label(self):
        if not self.visual_pages:return f'텍스트 {self.page_count}쪽'
        if len(self.visual_pages)==self.page_count:return f'PDF 원본 {self.page_count}쪽'
        return f'텍스트 {self.page_count-len(self.visual_pages)}쪽 + 시각 자료 {len(self.visual_pages)}쪽'

DRAWING={b'Do',b'sh',b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*'}

def prepare_pdf(path):
    from pypdf import PdfReader,PdfWriter
    from pypdf.generic import ContentStream
    data=Path(path).read_bytes()
    if len(data)>30*1024*1024:raise ValueError('PDF는 30MB 이하로 첨부해 주세요.')
    if not data.startswith(b'%PDF-'):raise ValueError('실제 PDF 파일이 아닙니다.')
    reader=PdfReader(io.BytesIO(data))
    if reader.is_encrypted:raise ValueError('암호화된 PDF입니다. 암호를 제거한 사본을 첨부해 주세요.')
    count=len(reader.pages)
    if count<1 or count>250:raise ValueError('PDF는 1~250쪽 범위로 첨부해 주세요.')
    local=[];api=[];visual=[]
    for i,page in enumerate(reader.pages,1):
        uncertain=False
        try:text=(page.extract_text(extraction_mode='layout') or '').strip()
        except Exception:text='';uncertain=True
        try:
            stream=page.get_contents()
            ops=ContentStream(stream,reader).operations if stream is not None else []
            uncertain=uncertain or any(op in DRAWING for _,op in ops) or bool(page.get('/Annots')) or bool(page.get('/Rotate',0)%360) or len(text)<30
        except Exception:uncertain=True
        block=f'[원본 PDF {i}쪽]\n{text}';local.append(block)
        if uncertain:visual.append(i)
        else:api.append(block)
    visual_data=None
    if visual:
        if len(visual)==count:visual_data=data
        else:
            w=PdfWriter()
            for i in visual:w.add_page(reader.pages[i-1])
            b=io.BytesIO();w.write(b);visual_data=b.getvalue()
        api.insert(0,'첨부 PDF 쪽→원본 쪽: '+','.join(f'{j}→{i}' for j,i in enumerate(visual,1)))
    api_text='\n\n'.join(api)
    if len(api_text)>450000:raise ValueError('PDF 텍스트가 너무 깁니다. 나눠 첨부해 주세요. 내용을 임의로 잘라 전송하지 않았습니다.')
    return PreparedDocument('\n\n'.join(local),api_text,visual_data,count,tuple(visual),data)
