$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --clean --windowed --onedir --name AIInspectionReport --add-data 'assets;assets' --collect-all tkinterdnd2 --hidden-import win32timezone --exclude-module numpy --exclude-module PIL main.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
