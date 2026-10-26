"""Only explicitly pinned manual fields are remembered on this Windows profile."""
import json
import os
import tempfile
from pathlib import Path

FIELDS = ('inspector_org', 'inspector')

def default_path():
    base = os.environ.get('LOCALAPPDATA')
    if not base:
        raise OSError('Windows 사용자 설정 경로를 찾을 수 없습니다.')
    return Path(base) / 'AIInspectionReport' / 'preferences.json'

def load(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('pinned'), dict):
        raise ValueError('지원하지 않는 사용자 설정 형식입니다.')
    values={k:v for k,v in data['pinned'].items()
            if k in FIELDS and isinstance(v,str) and len(v) <= 2000}
    if 'visit_org' in data['pinned']:
        try:save(path,values)
        except OSError:pass  # Restore the two retained fields even on read-only settings.
    return values

def save(path, values):
    path = Path(path)
    pinned = {k:v for k,v in values.items() if k in FIELDS and isinstance(v,str) and len(v) <= 2000}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.preferences-', suffix='.tmp', delete=False) as f:
            temporary = Path(f.name)
            json.dump({'version':1, 'pinned':pinned}, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
