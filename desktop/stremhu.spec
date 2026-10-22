from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyInstaller.building.api import COLLECT, EXE, PYZ
    from PyInstaller.building.build_main import Analysis
    from PyInstaller.building.osx import BUNDLE

from PyInstaller.utils.hooks import collect_submodules

# Határozzuk meg a projekt gyökérkönyvtárát a spec fájlhoz képest
spec_dir = Path(SPECPATH).resolve()
root_dir = spec_dir.parent if spec_dir.name == "desktop" else spec_dir

sys.path.insert(0, str(root_dir / "server"))
sys.path.insert(0, str(root_dir))

server_modules = collect_submodules("server")
desktop_modules = collect_submodules("desktop")

datas = [
    (str(root_dir / "server" / "alembic.ini"), "."),
    (str(root_dir / "server" / "alembic"), "alembic"),
]

client_candidates = [
    root_dir / "server" / "client",
    root_dir / "client" / "dist",
]
for candidate in client_candidates:
    if candidate.exists() and any(candidate.iterdir()):
        datas.append((str(candidate), "client"))
        break

assets_dir = root_dir / "desktop" / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "desktop/assets"))

hiddenimports = (
    [
        "alembic",
        "sqlalchemy",
        "pydantic",
        "pydantic_settings",
        "fastapi",
        "uvicorn",
        "hypercorn",
        "sqlite3",
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "platformdirs",
        "psutil",
        "libtorrent",
        "setproctitle",
        "aiolimiter",
        "argon2",
        "pyotp",
        "apscheduler",
        "acme",
        "cryptography",
        "josepy",
        "humanize",
        "tzlocal",
        "torf",
        "selectolax",
        "dns",
        "email_validator",
    ]
    + server_modules
    + desktop_modules
)

a = Analysis(
    [str(root_dir / "desktop" / "__main__.py")],
    pathex=[str(root_dir / "server"), str(root_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

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

icon_file = root_dir / "desktop" / "assets" / "icon.icns"
icon_path = str(icon_file) if icon_file.exists() else None

app = BUNDLE(
    coll,
    name="StremHU.app",
    icon=icon_path,
    bundle_identifier="com.stremhu.desktop",
    info_plist={
        "CFBundleName": "StremHU",
        "CFBundleDisplayName": "StremHU",
        "CFBundleIdentifier": "com.stremhu.desktop",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
)

