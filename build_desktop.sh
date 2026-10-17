#!/bin/bash
set -e

# Projekt gyökérkönyvtár meghatározása
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Megfelelő Python parancs kiválasztása
if [ -f "$SCRIPT_DIR/.conda/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.conda/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "Hiba: Nem található Python értelmező!"
    exit 1
fi

echo "Használt Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

echo "=== React Kliens Építése ==="
cd client
npm install
npm run build
cd "$SCRIPT_DIR"

echo "=== Alkalmazás Ikon Generálása (macOS) ==="
if [ "$(uname)" = "Darwin" ]; then
    mkdir -p desktop/assets
    if [ ! -f "desktop/assets/icon.icns" ] && [ -f "client/public/logo.png" ]; then
        echo "macOS icon.icns generálása a logo.png-ből..."
        ICONSET_DIR="/tmp/stremhu_icon_$$.iconset"
        mkdir -p "$ICONSET_DIR"
        sips -z 16 16     client/public/logo.png --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
        sips -z 32 32     client/public/logo.png --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
        sips -z 32 32     client/public/logo.png --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
        sips -z 64 64     client/public/logo.png --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
        sips -z 128 128   client/public/logo.png --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
        sips -z 256 256   client/public/logo.png --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
        sips -z 256 256   client/public/logo.png --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
        sips -z 512 512   client/public/logo.png --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
        sips -z 512 512   client/public/logo.png --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
        iconutil -c icns "$ICONSET_DIR" -o desktop/assets/icon.icns
        rm -rf "$ICONSET_DIR"
    fi
fi

echo "=== Statikus Fájlok Másolása ==="
rm -rf core/client server/client
cp -r client/dist core/client

echo "=== Python Csomagok Telepítése / Ellenőrzése ==="
"$PYTHON_BIN" -m pip install -r requirements.txt
"$PYTHON_BIN" -m pip install -r desktop/requirements.txt

echo "=== Python Futtatható Fájl Építése (PyInstaller) ==="
"$PYTHON_BIN" -m PyInstaller --clean -y desktop/stremhu.spec

if [ "$(uname)" = "Darwin" ]; then
    echo "=== macOS Csomag Aláírása (Ad-hoc codesign) ==="
    codesign --force --deep --sign - "dist/StremHU.app"

    echo "=== macOS DMG Telepítőcsomag Készítése ==="
    DMG_NAME="StremHU.dmg"
    DMG_PATH="dist/$DMG_NAME"
    TMP_DMG_STAGING="dist/dmg_staging"

    rm -f "$DMG_PATH"
    rm -rf "$TMP_DMG_STAGING"
    mkdir -p "$TMP_DMG_STAGING"

    cp -R "dist/StremHU.app" "$TMP_DMG_STAGING/"
    ln -s /Applications "$TMP_DMG_STAGING/Applications"

    hdiutil create -volname "StremHU" -srcfolder "$TMP_DMG_STAGING" -ov -format UDZO "$DMG_PATH"
    rm -rf "$TMP_DMG_STAGING"

    echo "=== Kész! ==="
    echo "1. Alkalmazás bundle: dist/StremHU.app"
    echo "2. Telepítő lemezkép (DMG): dist/StremHU.dmg"
else
    echo "=== Kész! ==="
    echo "A kész asztali alkalmazás a dist/StremHU mappában található."
fi
