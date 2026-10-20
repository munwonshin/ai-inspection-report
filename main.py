import sys

if __name__=='__main__':
    if '--hwp-worker' in sys.argv:
        from inspection.exporter import worker_main
        worker_main()
    elif len(sys.argv)==4 and sys.argv[1]=='--pdf-check':
        from inspection.pdf_probe import main
        main()
    else:
        from inspection.ui import run
        run()
