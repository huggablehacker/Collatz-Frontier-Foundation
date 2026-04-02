# uploader.spec
# PyInstaller spec for collatz_upload_frontier.exe

block_cipher = None

a = Analysis(
    ['collatz_upload_frontier.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'urllib.request',
        'urllib.error',
        'base64',
        'json',
        'argparse',
        'pathlib',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'flask', 'requests'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='collatz_upload_frontier',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)
