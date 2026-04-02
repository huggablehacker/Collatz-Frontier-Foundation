# coordinator.spec
# PyInstaller spec for collatz_coordinator.exe
# Run: pyinstaller coordinator.spec

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all Flask/Werkzeug data (templates, static, etc.)
flask_datas    = collect_data_files('flask')
werkzeug_datas = collect_data_files('werkzeug')

a = Analysis(
    ['collatz_coordinator.py'],
    pathex=['.'],
    binaries=[],
    datas=flask_datas + werkzeug_datas,
    hiddenimports=[
        'flask',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.routing',
        'werkzeug.exceptions',
        'waitress',
        'waitress.server',
        'waitress.task',
        'waitress.channel',
        'waitress.runner',
        'json',
        'threading',
        'pathlib',
        'logging',
        'argparse',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['gmpy2', 'tkinter', 'matplotlib', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='collatz_coordinator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # keep console window so logs are visible
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version=None,
)
