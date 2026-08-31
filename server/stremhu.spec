from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyInstaller.building.api import COLLECT, EXE, PYZ
    from PyInstaller.building.build_main import Analysis
    from PyInstaller.building.osx import BUNDLE

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules

app_modules = collect_submodules("app")

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("client", "client"),
        ("alembic.ini", "."),
        ("alembic", "alembic"),
    ],
    hiddenimports=[
        "alembic",
        "sqlalchemy",
        "pydantic",
        "fastapi",
        "uvicorn",
        "hypercorn",
        "sqlite3",
        "pystray",
        "PIL",
    ]
    + app_modules,
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
    name="StremHU",
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StremHU",
)

app = BUNDLE(
    coll,
    name="StremHU.app",
    icon=None,
    bundle_identifier="com.stremhu.desktop",
    info_plist={"LSUIElement": True},
)
