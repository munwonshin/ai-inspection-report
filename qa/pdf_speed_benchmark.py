"""Local PDF preparation benchmark. No network/API calls or document output."""
from pathlib import Path
import sys,tempfile,time,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pdf_baseline
from inspection.documents import prepare_pdf
from pdf_visual_verify import verify_visual_pages
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject,NameObject,DictionaryObject

def synthetic(path):
    writer=PdfWriter()
    font=writer._add_object(DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')}))
    for n in range(20):
        page=writer.add_blank_page(595,842)
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        stream=DecodedStreamObject();ops=[f'BT /F1 12 Tf 30 780 Td (Synthetic page {n+1:02d}, planned evidence is not actual performance.) Tj ET']
        ops.extend(f'{x%500} {100+x%600} 10 10 re S' for x in range(800))
        stream.set_data('\n'.join(ops).encode());page[NameObject('/Contents')]=writer._add_object(stream)
    writer.write(path)

def compare(path):
    start=time.perf_counter();old=pdf_baseline.prepare_pdf(path);before=time.perf_counter()-start
    start=time.perf_counter();new=prepare_pdf(path);after=time.perf_counter()-start
    fields=['api_text','page_count','visual_pages','original_bytes']
    assert all(getattr(old,f)==getattr(new,f) for f in fields),'AI source payload changed'
    verification=verify_visual_pages(new)
    return {'pages':new.page_count,'bytes':len(new.original_bytes),'baseline_seconds':before,'optimized_seconds':after,'api_text_and_mapping_equal':True,'visual_pdf_bytes_equal':old.visual_pdf==new.visual_pdf,'visual_verification':verification,'local_quote_layout_equal':old.local_text==new.local_text}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pdf',type=Path);args=parser.parse_args()
    if args.pdf:result=compare(args.pdf)
    else:
        with tempfile.TemporaryDirectory(prefix='inspection-synthetic-speed-') as tmp:
            path=Path(tmp)/'synthetic.pdf';synthetic(path);result=compare(path)
    print(json.dumps(result,ensure_ascii=False,indent=2))
