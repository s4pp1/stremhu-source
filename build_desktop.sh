#!/bin/bash
set -e

echo "=== React Kliens Építése ==="
cd client
npm install
npm run build
cd ..

echo "=== Statikus Fájlok Másolása ==="
rm -rf server/client
cp -r client/dist server/client

echo "=== Python Futtatható Fájl Építése (PyInstaller) ==="
cd server
python -m pip install pyinstaller pystray pillow
python -m PyInstaller --clean -y stremhu.spec

echo "=== Kész! ==="
echo "A kész asztali alkalmazás a server/dist/StremHU mappában található."
