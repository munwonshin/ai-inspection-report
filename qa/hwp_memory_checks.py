"""Explicit synthetic real-HWP test. No API, no registry/security changes.
Usage: python qa/hwp_memory_checks.py --approved EXISTING_TEST_FOLDER
"""
import sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection.core import Report,GENERAL
from inspection.exporter import save
if len(sys.argv)!=3 or sys.argv[1]!='--approved':
    raise SystemExit('Explicit approval required: --approved EXISTING_TEST_FOLDER')
folder=Path(sys.argv[2]).resolve()
if not folder.is_dir():raise SystemExit('Use an existing empty test folder')
r=Report('가상 HWP 저장 시험',tuple((k,'가상 값') for k in GENERAL),
    '• 가상 시연 화면을 확인함.\n\n• 가상 시험은 예정임.',
    '• 가상 보관 방법을 안내함.\n\n• 가상 제출일은 미정임.','')
result=save(r,str(folder),'가상_HWP_3pt_'+uuid.uuid4().hex[:8],approved=True)
assert result['reopened'];print('Real synthetic HWP verified:',result['path'])
