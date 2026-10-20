"""Fast local quote text for visual pages; their original PDF is still sent.

Text-only pages keep the existing layout extraction and API text. Failures use
the pypdf path. PDFium access is serialized as its API is not thread-safe.
"""
import threading
_LOCK=threading.Lock()


class NativeVisualReader:
    def __init__(self,data,page_count):
        self.data=data;self.page_count=page_count;self.document=None

    def __enter__(self):
        _LOCK.acquire()
        try:
            import pypdfium2
            self.document=pypdfium2.PdfDocument(self.data)
            if len(self.document)!=self.page_count:
                self.document.close();self.document=None
        except Exception:self.document=None
        return self

    def visual_text(self,index,source_page):
        if self.document is None:return None
        page=None;textpage=None
        try:
            page=self.document[index]
            # Type 1 is text. Paths/images/shadings/forms and unknown objects
            # conservatively retain the original page as PDF evidence.
            visual=bool(source_page.get('/Annots')) or bool(source_page.get('/Rotate',0)%360)
            if not visual:visual=any(obj.type!=1 for obj in page.get_objects(max_depth=1))
            if not visual:return None
            textpage=page.get_textpage()
            return textpage.get_text_range(errors='strict').replace('\r\n','\n').strip()
        except Exception:return None
        finally:
            if textpage is not None:textpage.close()
            if page is not None:page.close()

    def __exit__(self,*args):
        try:
            if self.document is not None:self.document.close()
        finally:_LOCK.release()
