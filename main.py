import sys

if __name__=='__main__':
    if '--hwp-worker' in sys.argv:
        from inspection.exporter import worker_main
        worker_main()
    else:
        from inspection.ui import run
        run()
