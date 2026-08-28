# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


root = Path(SPECPATH)
codex_binary = root / "vendor" / "codex" / "win-x64" / "codex.exe"
binaries = []
if codex_binary.exists():
    binaries.append((str(codex_binary), "vendor/codex/win-x64"))
local_runtime = root / "vendor" / "local_supervisor" / "llama.cpp"
if local_runtime.exists():
    binaries.append((str(local_runtime), "vendor/local_supervisor/llama.cpp"))

datas = [
    ("prompts/roman_system.md", "prompts"),
    ("data/roman_identity.json", "data"),
    ("data/roman_timeline.json", "data"),
    ("data/agent_skills.json", "data"),
    ("data/app_settings.json", "data"),
    ("data/avatars", "data/avatars"),
    ("data/branding", "data/branding"),
    ("data/theme_backgrounds", "data/theme_backgrounds"),
    ("build/build_info.json", "data"),
    ("vendor/local_supervisor/models/qwen2.5-0.5b-instruct-q4_k_m.gguf", "vendor/local_supervisor/models"),
    ("vendor/local_supervisor/models/LICENSE-Qwen2.5", "vendor/local_supervisor/models"),
    ("vendor/local_supervisor/MODEL_MANIFEST.json", "vendor/local_supervisor"),
    ("vendor/local_supervisor/llama.cpp/LICENSE-llama.cpp", "vendor/local_supervisor/llama.cpp"),
]

a = Analysis(
    ["app.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

worker_analysis = Analysis(
    ["runtime_v3/local_supervisor_worker.py"],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
worker_pyz = PYZ(worker_analysis.pure)
worker_exe = EXE(
    worker_pyz,
    worker_analysis.scripts,
    [],
    name="Team2050LocalWorker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Team2050",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    worker_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Team2050",
)
