import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyInstaller.building.api import COLLECT, EXE, PYZ
    from PyInstaller.building.build_main import Analysis
    from PyInstaller.building.osx import BUNDLE

    SPECPATH: str = ""

from PyInstaller.utils.hooks import collect_submodules

# 1. Platform-felismerés (macOS, Windows, Linux)
is_darwin: bool = sys.platform == "darwin"
is_windows: bool = sys.platform == "win32"
is_linux: bool = sys.platform.startswith("linux")

# 2. Projekt gyökérkönyvtár meghatározása
spec_dir: Path = Path(SPECPATH).resolve()
if (spec_dir / "pyproject.toml").exists():
    root_dir: Path = spec_dir
elif (spec_dir.parent / "pyproject.toml").exists():
    root_dir: Path = spec_dir.parent
elif (spec_dir.parent.parent / "pyproject.toml").exists():
    root_dir: Path = spec_dir.parent.parent
else:
    root_dir: Path = spec_dir.parent.parent

sys.path.insert(0, str(root_dir / "server"))
sys.path.insert(0, str(root_dir))

# 3. Adatfájlok és binárisok (Platform-független és platform-specifikus)
datas: list[tuple[str, str]] = [
    (str(root_dir / "server" / "alembic.ini"), "."),
    (str(root_dir / "server" / "alembic"), "alembic"),
]

binaries: list[tuple[str, str]] = []

# macOS-specifikus libtorrent dylib függőségek
if is_darwin:
    libtorrent_spec = importlib.util.find_spec("libtorrent")
    if libtorrent_spec and libtorrent_spec.origin:
        libtorrent_dir = Path(libtorrent_spec.origin).parent
        dylibs_dir = libtorrent_dir.parent / "libtorrent.dylibs"
        if dylibs_dir.exists():
            datas.append((str(dylibs_dir), "libtorrent.dylibs"))
            for dylib in dylibs_dir.glob("*.dylib"):
                binaries.append((str(dylib), "libtorrent.dylibs"))

# Kliens webes assetek (React / Vite frontend)
client_candidates: list[Path] = [
    root_dir / "server" / "client",
    root_dir / "client" / "dist",
]
for candidate in client_candidates:
    if candidate.exists() and any(candidate.iterdir()):
        datas.append((str(candidate), "client"))
        break

# Asztali ikonok és grafikai assetek
assets_dir: Path = root_dir / "desktop" / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "desktop/assets"))
    datas.append((str(assets_dir), "assets"))

# 4. Dinamikusan betöltött modulok (Pluginok és adatbázis dialektusok)
dynamic_submodules: list[str] = [
    *collect_submodules("alembic"),
    *collect_submodules("sqlalchemy.dialects.sqlite"),
    *collect_submodules("server.modules.indexer_definitions.integrations"),
    *collect_submodules("server.modules.network.ddns.providers"),
]

# Explicit stringként hivatkozott modulok (pl. Hypercorn 'server.app:app')
explicit_hidden_imports: list[str] = [
    "server.app",
    "alembic.ddl.sqlite",
    "python-multipart",
]

hidden_imports: list[str] = sorted(set(dynamic_submodules + explicit_hidden_imports))

# 5. Ikon kiválasztása platform szerint
icon_path: str | None = None
if is_darwin:
    icon_candidate = assets_dir / "icon.icns"
    if icon_candidate.exists():
        icon_path = str(icon_candidate)
elif is_windows:
    icon_candidate = assets_dir / "icon.ico"
    if icon_candidate.exists():
        icon_path = str(icon_candidate)
elif is_linux:
    icon_candidate = assets_dir / "icon.png"
    if icon_candidate.exists():
        icon_path = str(icon_candidate)

# 6. PyInstaller Analízis
a: Analysis = Analysis(
    scripts=[
        str(root_dir / "desktop" / "__main__.py"),
        str(root_dir / "server" / "__main__.py"),
    ],
    pathex=[str(root_dir), str(root_dir / "server")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "pytest",
        "unittest",
    ],
    noarchive=False,
    optimize=0,
)

pyz: PYZ = PYZ(a.pure)

# 7. Futtatható fájl (EXE) generálás
exe: EXE = EXE(
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
    icon=icon_path,
)

# 8. Mappastruktúra összeállítása (COLLECT)
coll: COLLECT = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StremHU",
)

# 9. macOS Alkalmazáscsomag (.app BUNDLE)
if is_darwin:
    app: BUNDLE = BUNDLE(
        coll,
        name="StremHU.app",
        icon=icon_path,
        bundle_identifier="hu.stremhu.desktop",
        info_plist={
            "CFBundleName": "StremHU",
            "CFBundleDisplayName": "StremHU Desktop",
            "CFBundleIdentifier": "hu.stremhu.desktop",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": "True",
            "LSUIElement": "0",
            "NSHumanReadableCopyright": "Copyright © 2026 StremHU",
        },
    )
