# -*- mode: python ; coding: utf-8 -*-
import sys

_hidden = []
if sys.platform == "win32":
    _hidden = ["pynput.keyboard._win32", "pynput.mouse._win32"]
elif sys.platform == "darwin":
    _hidden = ["pynput.keyboard._darwin", "pynput.mouse._darwin"]

a = Analysis(
    ["run_gui.py"],
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
    name="kvmshare-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # windowed=True hides the console on Windows/macOS
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="KVMShare GUI.app",
        icon=None,
        bundle_identifier="com.kvmshare.gui",
        info_plist={
            "NSHighResolutionCapable": True,
        },
    )
