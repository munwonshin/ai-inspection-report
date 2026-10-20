"""Verify a prepared visual subset against original pages, entirely in memory."""
import hashlib
import pypdfium2

def signature(page):
    size=page.get_size();textpage=page.get_textpage()
    try:text=textpage.get_text_range(errors='strict')
    finally:textpage.close()
    bitmap=page.render(scale=900/max(size))
    try:pixels=(bitmap.width,bitmap.height,hashlib.sha256(bytes(bitmap.buffer)).hexdigest())
    finally:bitmap.close()
    return size,text,pixels

def verify_visual_pages(doc):
    if not doc.visual_pages:return {'pages_checked':0,'all_text_and_renderings_match_original':True}
    original=pypdfium2.PdfDocument(doc.original_bytes);subset=pypdfium2.PdfDocument(doc.visual_pdf)
    try:
        assert len(subset)==len(doc.visual_pages)
        for index,page_number in enumerate(doc.visual_pages):
            a=original[page_number-1];b=subset[index]
            try:assert signature(a)==signature(b),'Visual source page differs: '+str(page_number)
            finally:a.close();b.close()
    finally:subset.close();original.close()
    return {'pages_checked':len(doc.visual_pages),'all_text_and_renderings_match_original':True}
