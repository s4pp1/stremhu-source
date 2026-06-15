### Node.js (fnm)

Node.js verzió kezeléshez a `fnm` használata javasolt. https://github.com/Schniz/fnm

- `fnm install` – Telepíti a `.node-version` fájlban megadott verziót.
- `fnm use` – Aktiválja a projekt által használt verziót.
- `fnm current` – Megmutatja az aktuálisan aktív verziót.

### Conda

A Python környezet kezeléséhez:

- `conda env create -p ./.conda -f environment.yaml` – Létrehozza a környezetet a helyi `.conda` mappába.
- `conda env update -p ./.conda -f environment.yaml --prune` – Frissíti a környezetet és törli a feleslegessé vált csomagokat.

### Kódminőség és típusellenőrzés (Linting & Typing)

- `basedpyright .` – Típusellenőrzés futtatása.
- `ruff check .` – Statikus kódellenőrzés (linter).
- `ruff check . --fix` – Kódhibák automatikus javítása.
- `ruff format .` – Kód formázása.
