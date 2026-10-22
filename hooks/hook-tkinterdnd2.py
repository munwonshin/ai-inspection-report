"""Ship only the Windows x64 TkDND runtime targeted by this release."""
from pathlib import Path
from PyInstaller.utils.hooks import get_package_paths
_,package=get_package_paths('tkinterdnd2')
datas=[(str(Path(package)/'tkdnd'/'win-x64'),'tkinterdnd2/tkdnd/win-x64')]
