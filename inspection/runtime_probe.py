"""Explicit developer diagnostics, no API transmission or report export."""
def main():
    import sys,json,ssl
    from pathlib import Path
    from tkinterdnd2 import TkinterDnD
    from .documents import prepare_pdf
    root=TkinterDnD.Tk();root.withdraw()
    version=str(root.tk.call('package','provide','tkdnd'))
    root.drop_target_register('DND_Files');root.destroy()
    result={'tkdnd':version,'tls':ssl.OPENSSL_VERSION}
    # Only explicitly supplied synthetic developer fixtures are read.
    if len(sys.argv)==4:
        try:prepare_pdf(sys.argv[3])
        except ValueError as e:result['pdf_error']=str(e)
        else:result['pdf_error']=None
    with Path(sys.argv[2]).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False)
