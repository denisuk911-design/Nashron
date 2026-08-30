# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root / "scripts" / "luminifera_web_launcher.py")], pathex=[str(root)], datas=[(str(root / "apps" / "web" / "static"), "apps/web/static"), (str(root / "data"), "data")], hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto"], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Luminifera", debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=True)
