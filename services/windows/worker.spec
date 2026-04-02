# worker.spec
# PyInstaller spec for collatz_worker.exe
# Run: pyinstaller worker.spec

block_cipher = None

a = Analysis(
    ['collatz_worker.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.models',
        'requests.sessions',
        'urllib3',
        'urllib3.util',
        'urllib3.util.retry',
        'multiprocessing',
        'multiprocessing.pool',
        'multiprocessing.process',
        'argparse',
        'socket',
        'json',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # gmpy2 is optional — if not present it falls back to Python ints
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
    name='collatz_worker',
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
    icon=None,
    version=None,
)
