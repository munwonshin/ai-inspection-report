$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
python -c "import sys,struct,platform; assert sys.platform=='win32' and struct.calcsize('P')==8 and platform.machine().lower() in ('amd64','x86_64'), 'Windows x64 Python required'"
if ($LASTEXITCODE -ne 0) { throw 'Windows x64 Python required for the bundled TkDND runtime' }
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' qa/run_unit_checks.py
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --windowed --onedir --name AIInspectionReport --icon assets/app.ico --add-data 'assets;assets' --additional-hooks-dir hooks --collect-all pypdfium2 --collect-all pypdfium2_raw --collect-all resvg_py --hidden-import win32timezone --exclude-module numpy --exclude-module cryptography --exclude-module Crypto main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }

& '.\.venv\Scripts\python.exe' qa/verify_frozen.py '.\dist\AIInspectionReport\AIInspectionReport.exe'
if ($LASTEXITCODE -ne 0) { throw 'Frozen code differs from source. Rebuild without editing source during compilation.' }

Copy-Item -LiteralPath '바탕화면 아이콘 만들기.cmd' -Destination '.\dist\AIInspectionReport\'
Copy-Item -LiteralPath 'THIRD_PARTY_NOTICES.md' -Destination '.\dist\AIInspectionReport\'
Copy-Item -LiteralPath 'licenses' -Destination '.\dist\AIInspectionReport\' -Recurse -Force

Copy-Item -LiteralPath 'install-support.cs' -Destination '.\dist\AIInspectionReport\'
