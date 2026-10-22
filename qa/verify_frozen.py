"""Read-only build check: frozen application code must match saved source."""
import sys
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
if len(sys.argv)!=2:raise SystemExit('Usage: python qa/verify_frozen.py PATH_TO_EXE')
root=Path(__file__).resolve().parents[1]
archive=CArchiveReader(str(Path(sys.argv[1]).resolve())).open_embedded_archive('PYZ.pyz')
names=['ui','api','style','metadata','core','streaming','exporter','vault','documents','runtime_probe']
for name in names:
    actual=archive.extract('inspection.'+name)
    expected=compile((root/'inspection'/f'{name}.py').read_bytes(),actual.co_filename,'exec')
    if actual!=expected:raise SystemExit('Build/source mismatch: '+name+'. Rebuild without modifying source during the build.')
print('FROZEN_MODULES_MATCH_SOURCE',len(names),flush=True)
