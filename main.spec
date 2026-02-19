# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# 获取 Python 环境路径
python_path = sys.prefix

a = Analysis(
    ['ui.py'],
    pathex=[],
    binaries=[
        (os.path.join(python_path, 'Library', 'bin', 'tcl86t.dll'), '.'),
        (os.path.join(python_path, 'Library', 'bin', 'tk86t.dll'), '.'),
        (os.path.join(python_path, 'Library', 'bin', 'libexpat.dll'), '.'),
        (os.path.join(python_path, 'Library', 'bin', 'libmpdec-4.dll'), '.'),
        (os.path.join(python_path, 'Library', 'bin', 'liblzma.dll'), '.'),
        (os.path.join(python_path, 'Library', 'bin', 'LIBBZ2.dll'), '.'),
        (os.path.join(python_path, 'Library', 'bin', 'ffi.dll'), '.'),
    ],
    datas=[
        ('config.json', '.'),
        ('config_loader.py', '.'),
        ('main.py', '.'),
        ('images/*.png', 'images'),
        ('Tesseract-OCR', 'Tesseract-OCR'),
        (os.path.join(python_path, 'Library', 'lib', 'tcl8.6'), 'tcl8.6'),
        (os.path.join(python_path, 'Library', 'lib', 'tk8.6'), 'tk8.6'),
    ],
    hiddenimports=['openpyxl', 'cv2', 'numpy', 'pytesseract', 'psutil', 'pyautogui', 'PIL'],
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
    a.binaries,
    a.datas,
    [],
    name='DeltaSteamVerifier',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
