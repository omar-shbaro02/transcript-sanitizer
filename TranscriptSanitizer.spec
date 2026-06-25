# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


block_cipher = None
root = Path(SPECPATH)


datas = [
    (str(root / "config" / "default_config.json"), "config"),
    (str(root / "README.md"), "."),
]

hiddenimports = []

for package_name in (
    "spacy",
    "presidio_analyzer",
    "presidio_anonymizer",
    "en_core_web_lg",
    "en_core_web_sm",
):
    try:
        datas += collect_data_files(package_name)
        hiddenimports += collect_submodules(package_name)
    except Exception:
        pass


a = Analysis(
    ["app.py"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TranscriptSanitizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file="packaging/macos_entitlements.plist",
    icon="packaging/app.ico" if (root / "packaging" / "app.ico").exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TranscriptSanitizer",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="TranscriptSanitizer.app",
        icon="packaging/app.icns" if (root / "packaging" / "app.icns").exists() else None,
        bundle_identifier="com.transcriptsanitizer.app",
        info_plist={
            "CFBundleName": "TranscriptSanitizer",
            "CFBundleDisplayName": "Transcript Sanitizer",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
