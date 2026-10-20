"""Developer-only frozen PDF verification; writes metrics, never document text."""
def main():
    import sys,json,time,hashlib
    from pathlib import Path
    from .documents import prepare_pdf
    from .pdf_native import NativeVisualReader
    started=time.perf_counter();doc=prepare_pdf(sys.argv[2]);elapsed=time.perf_counter()-started
    with NativeVisualReader(doc.original_bytes,doc.page_count) as native:
        available=native.document is not None
    result={'seconds':elapsed,'page_count':doc.page_count,'visual_pages':doc.visual_pages,'native_support_loaded':available,
        'api_text_sha256':hashlib.sha256(doc.api_text.encode()).hexdigest(),'visual_pdf_sha256':hashlib.sha256(doc.visual_pdf or b'').hexdigest()}
    with Path(sys.argv[3]).open('x',encoding='utf-8') as f:json.dump(result,f)
