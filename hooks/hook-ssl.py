"""Preserve optional security data used by the build interpreter's ssl module.

The Codex-provided Python loads a public rejected-CA policy beside ssl.py.
Copy it unchanged beside the frozen ssl module. Standard Python has no such
file and needs no extra data. Never replace certificate verification or CA stores.
"""
from pathlib import Path
import ssl

policy=Path(ssl.__file__).with_name('codex-rejected-cas.pem')
datas=[(str(policy),'.')] if policy.is_file() else []
