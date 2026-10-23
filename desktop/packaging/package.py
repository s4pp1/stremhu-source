#!/usr/bin/env python3
"""StremHU Desktop - Multi-platform packaging script.

Támogatott platformok: macOS (.dmg), Windows (.zip, Inno Setup .exe), Linux (.tar.gz)
Használható helyi fejlesztésnél és GitHub Actions CI/CD munkafolyamatokban is.
"""

from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_root_dir() -> Path:
    """Megkeresi a projekt gyökérkönyvtárát."""
    return Path(__file__).resolve().parent.parent.parent


def get_packaging_dir() -> Path:
    """Visszaadja a packaging segédkönyvtárat."""
    return Path(__file__).resolve().parent


def compute_sha256(file_path: Path) -> str:
    """Kiszámítja egy fájl SHA256 ellenőrzőösszegét."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_frontend(root_dir: Path) -> None:
    """Lefordítja a kliens webes felületét (React / Vite)."""
    client_dir = root_dir / "client"
    print("\n📦 [1/4] Frontend fordítása (client)...")

    node_modules = client_dir / "node_modules"
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    if not node_modules.exists():
        print("   -> node_modules hiányzik, npm ci futtatása...")
        subprocess.run([npm_cmd, "ci"], cwd=str(client_dir), check=True)

    print("   -> npm run build futtatása...")
    subprocess.run([npm_cmd, "run", "build"], cwd=str(client_dir), check=True)

    # Szinkronizálás a server/client mappával
    dist_dir = client_dir / "dist"
    server_client_dir = root_dir / "server" / "client"
    if dist_dir.exists():
        print(f"   -> Frontend másolása {server_client_dir} mappába...")
        if server_client_dir.exists():
            shutil.rmtree(server_client_dir)
        shutil.copytree(dist_dir, server_client_dir)
    print("   ✅ Frontend sikeresen lefordítva.")


def run_pyinstaller(root_dir: Path, clean: bool = False) -> None:
    """Lefuttatja a PyInstaller fordítást a desktop/packaging/stremhu.spec fájllal."""
    print("\n🔨 [2/4] PyInstaller bináris fordítása...")
    spec_file = get_packaging_dir() / "stremhu.spec"

    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    if clean:
        cmd.append("--clean")

    subprocess.run(cmd, cwd=str(root_dir), check=True)
    print("   ✅ PyInstaller fordítás sikeresen befejeződött.")


def package_macos(root_dir: Path) -> list[Path]:
    """Csomagolja a macOS alkalmazást (.dmg fájlba)."""
    print("\n🍏 [3/4] macOS csomagolás (.dmg)...")
    dist_dir = root_dir / "dist"
    app_bundle = dist_dir / "StremHU.app"
    if not app_bundle.exists():
        raise FileNotFoundError(f"Nem található az alkalmazáscsomag: {app_bundle}")

    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    dmg_name = f"StremHU-macOS-{arch}.dmg"
    dmg_path = dist_dir / dmg_name
    universal_dmg = dist_dir / "StremHU.dmg"

    # Ad-hoc kódaláírás fejlesztési és teszt célra
    print("   -> Ad-hoc kódaláírás ellenőrzése...")
    subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(app_bundle)],
        check=True,
    )

    staging_dir = dist_dir / "dmg_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    try:
        print("   -> Alkalmazás másolása a DMG előkészítőbe...")
        shutil.copytree(app_bundle, staging_dir / "StremHU.app", symlinks=True)

        print("   -> /Applications szimbolikus link létrehozása...")
        (staging_dir / "Applications").symlink_to("/Applications")

        if dmg_path.exists():
            dmg_path.unlink()

        print(f"   -> DMG lemezkép létrehozása: {dmg_name}...")
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                "StremHU",
                "-srcfolder",
                str(staging_dir),
                "-ov",
                "-format",
                "UDZO",
                str(dmg_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        shutil.copyfile(dmg_path, universal_dmg)
        print(f"   ✅ macOS DMG elkészült: {dmg_path.name}")
        return [dmg_path, universal_dmg]
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


def package_windows(root_dir: Path) -> list[Path]:
    """Csomagolja a Windows alkalmazást (ZIP és opcionálisan Inno Setup EXE)."""
    print("\n🪟 [3/4] Windows csomagolás...")
    dist_dir = root_dir / "dist"
    stremhu_dir = dist_dir / "StremHU"
    if not stremhu_dir.exists():
        raise FileNotFoundError(f"Nem található a lefordított mappa: {stremhu_dir}")

    artifacts: list[Path] = []
    zip_name = "StremHU-Windows-x64.zip"
    zip_path = dist_dir / zip_name

    print(f"   -> Hordozható ZIP archívum készítése: {zip_name}...")
    shutil.make_archive(
        str(dist_dir / "StremHU-Windows-x64"),
        "zip",
        root_dir=dist_dir,
        base_dir="StremHU",
    )
    artifacts.append(zip_path)

    # Inno Setup keresése a telepítőhöz
    iscc = shutil.which("iscc") or shutil.which("ISCC.exe")
    if not iscc:
        candidates = [
            Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
            Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        ]
        for cand in candidates:
            if cand.exists():
                iscc = str(cand)
                break

    packaging_dir = get_packaging_dir()
    iss_file = packaging_dir / "installer.iss"
    if iscc and iss_file.exists():
        print("   -> Inno Setup telepítő készítése (ISCC)...")
        subprocess.run([iscc, str(iss_file)], cwd=str(packaging_dir), check=True)
        setup_exe = dist_dir / "StremHU-Windows-x64-Setup.exe"
        if setup_exe.exists():
            artifacts.append(setup_exe)
            print(f"   ✅ Windows telepítő elkészült: {setup_exe.name}")
    else:
        print(
            "   ℹ️  Inno Setup nincs telepítve, az önálló telepítő kihagyva (ZIP elérhető)."
        )

    print(f"   ✅ Windows csomagolás kész: {zip_name}")
    return artifacts


def package_linux(root_dir: Path) -> list[Path]:
    """Csomagolja a Linux alkalmazást (.tar.gz archívumba)."""
    print("\n🐧 [3/4] Linux csomagolás...")
    dist_dir = root_dir / "dist"
    stremhu_dir = dist_dir / "StremHU"
    if not stremhu_dir.exists():
        raise FileNotFoundError(f"Nem található a lefordított mappa: {stremhu_dir}")

    machine = platform.machine().lower()
    arch = "x86_64" if machine in ("x86_64", "amd64") else machine
    tar_name = f"StremHU-Linux-{arch}.tar.gz"
    tar_path = dist_dir / tar_name

    # .desktop launcher fájl készítése
    desktop_file = stremhu_dir / "stremhu.desktop"
    desktop_file.write_text(
        "[Desktop Entry]\n"
        "Name=StremHU\n"
        "Comment=StremHU Desktop and Torrent Relay Engine\n"
        "Exec=./StremHU\n"
        "Icon=assets/icon.png\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=AudioVideo;Video;Network;\n",
        encoding="utf-8",
    )

    print(f"   -> Tömörített archívum készítése: {tar_name}...")
    shutil.make_archive(
        str(dist_dir / f"StremHU-Linux-{arch}"),
        "gztar",
        root_dir=dist_dir,
        base_dir="StremHU",
    )
    print(f"   ✅ Linux archívum elkészült: {tar_name}")
    return [tar_path]


def generate_checksums(artifacts: list[Path], dist_dir: Path) -> Path:
    """Létrehoz egy SHA256SUMS.txt fájlt az összes generált telepítőhöz."""
    print("\n🔒 [4/4] SHA-256 ellenőrzőösszegek számítása...")
    sums_file = dist_dir / "SHA256SUMS.txt"
    lines = []

    unique_artifacts = sorted(set(artifacts), key=lambda p: p.name)
    for art in unique_artifacts:
        if art.is_file() and art.name != "SHA256SUMS.txt":
            sha = compute_sha256(art)
            lines.append(f"{sha}  {art.name}\n")
            size_mb = art.stat().st_size / (1024 * 1024)
            print(f"   - {art.name:<32} ({size_mb:6.1f} MB) SHA256: {sha[:16]}...")

    sums_file.write_text("".join(lines), encoding="utf-8")
    print(f"   ✅ Checksum fájl elkészült: {sums_file.name}")
    return sums_file


def main() -> None:
    parser = argparse.ArgumentParser(description="StremHU Desktop csomagoló script")
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Frontend újraépítésének kihagyása",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Előző buildek kitakarítása fordítás előtt",
    )
    args = parser.parse_args()

    root_dir = get_root_dir()
    dist_dir = root_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"🚀 StremHU Desktop Packaging ({sys.platform} - {platform.machine()})")
    print("=" * 60)

    # 1. Frontend build
    if not args.skip_frontend:
        build_frontend(root_dir)
    else:
        print("\n⏩ [1/4] Frontend fordítás kihagyva (--skip-frontend)")

    # 2. PyInstaller build
    run_pyinstaller(root_dir, clean=args.clean)

    # 3. Platform-specifikus csomagolás
    artifacts: list[Path] = []
    if sys.platform == "darwin":
        artifacts.extend(package_macos(root_dir))
    elif sys.platform == "win32":
        artifacts.extend(package_windows(root_dir))
    elif sys.platform.startswith("linux"):
        artifacts.extend(package_linux(root_dir))
    else:
        print(f"⚠️ Ismeretlen platform: {sys.platform}")

    # 4. SHA-256 ellenőrzőösszegek
    if artifacts:
        generate_checksums(artifacts, dist_dir)

    print("\n" + "=" * 60)
    print("🎉 A csomagolás sikeresen befejeződött!")
    print(f"📁 Kimeneti könyvtár: {dist_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
