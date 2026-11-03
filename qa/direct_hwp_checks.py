"""Read-only benchmark for a caller-supplied synthetic HWP; no API or output HWP."""
from pathlib import Path
import sys,time,json,hashlib
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from inspection.documents import prepare_hwp
from inspection.hwp_direct import MARKER
source=Path(sys.argv[1]);before=hashlib.sha256(source.read_bytes()).hexdigest();samples=[]
with patch('inspection.hwp_input.convert_pdf',side_effect=AssertionError('Unexpected conversion')),patch('win32com.client.DispatchEx',side_effect=AssertionError('Unexpected Hancom launch')):
    for _ in range(3):
        start=time.perf_counter();result=prepare_hwp(source);samples.append(round(time.perf_counter()-start,4))
        assert result.original_bytes.startswith(MARKER) and result.visual_pdf is None
        assert '[HWP 구역 1]' in result.api_text and '[표 ' in result.api_text
        assert result.api_text==result.local_text
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
proof={'seconds':samples,'sections':result.page_count,'characters':len(result.local_text),'table_markers':result.local_text.count(': '),
    'hancom_application_not_launched':True,'pdf_conversion_not_called':True,'source_unchanged':True,
    'scope':'One caller-supplied synthetic HWP; excludes API and process startup.'}
(R/'qa/direct_hwp_checks.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps(proof),flush=True)
