# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[('vendor\\codex\\win-x64\\codex.exe', 'vendor\\codex\\win-x64')],
    datas=[('prompts\\roman_system.md', 'prompts'), ('data\\roman_identity.json', 'data'), ('data\\roman_timeline.json', 'data'), ('data\\agent_skills.json', 'data'), ('data\\app_settings.json', 'data'), ('data\\avatars', 'data\\avatars'), ('build\\build_info.json', 'data')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Roman 2050',
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
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Roman 2050',
)
