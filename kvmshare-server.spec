# -*- mode: python ; coding: utf-8 -*-
import sys

# Platform-specific pynput backends
_hidden = []
if sys.platform == "win32":
    _hidden = ["pynput.keyboard._win32", "pynput.mouse._win32"]
elif sys.platform == "darwin":
    _hidden = ["pynput.keyboard._darwin", "pynput.mouse._darwin"]

a = Analysis(
    ["run_server.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="kvmshare-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
