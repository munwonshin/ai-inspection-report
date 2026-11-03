import sys

if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='--desktop-shortcut':
        from inspection.desktop_shortcut import main
        main()
    elif len(sys.argv)==4 and sys.argv[1]=='--local-input-check':
        from inspection.input_probe import main
        main()
    elif len(sys.argv)==4 and sys.argv[1]=='--hwp-read-check':
        from inspection.hwp_direct import check_main
        check_main()
    elif '--hwp-worker' in sys.argv:
        from inspection.exporter import worker_main
        worker_main()
    elif len(sys.argv)==3 and sys.argv[1]=='--api-check':
        from inspection.api_probe import main
        main()
    elif len(sys.argv) in (3,4) and sys.argv[1]=='--runtime-check':
        from inspection.runtime_probe import main
        main()
    elif len(sys.argv)==4 and sys.argv[1]=='--pdf-check':
        from inspection.pdf_probe import main
        main()
    else:
        from inspection.ui import run
        run()
