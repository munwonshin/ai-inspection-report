"""Run all tests; retry only transient Windows locks when cleaning test temp dirs."""
from pathlib import Path
import sys,tempfile,time,unittest
base=Path(__file__).resolve().parents[1];sys.path.insert(0,str(base))
OriginalTemporaryDirectory=tempfile.TemporaryDirectory
class TestTemporaryDirectory(OriginalTemporaryDirectory):
    retries=0
    def cleanup(self):
        delays=(.05,.1,.2,.4,.8,1.)
        for attempt in range(len(delays)+1):
            try:return super().cleanup()
            except OSError as e:
                if getattr(e,'winerror',None) not in (32,33) or attempt==len(delays):raise
                type(self).retries+=1;time.sleep(delays[attempt])
tempfile.TemporaryDirectory=TestTemporaryDirectory
try:
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover(str(base/'tests')))
finally:tempfile.TemporaryDirectory=OriginalTemporaryDirectory
print('TEST_TEMP_CLEANUP_RETRIES',TestTemporaryDirectory.retries,flush=True)
if not result.wasSuccessful():raise SystemExit(1)
