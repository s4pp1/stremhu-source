# Frissítés v0.17–v0.22 verzióról · Upgrading from v0.17–v0.22

[Magyar](#magyar) · [English](#english) · [Fejlesztőknek / For developers](#fejlesztőknek--for-developers)

---

## Magyar

A v0.23.0 új architektúrát hozott, ezért a régi (v0.22.x vagy korábbi) verziókról
a sima frissítés nem lehetséges. A beépített migrációs eszköz a letöltött
tartalmakon túl ezeket is átviszi:
- a felhasználókat és jelszavakat;
- az API kulcsokat, így a Stremio/Kodi addon URL-ek és a párosított eszközök tovább működnek;
- az indexer (torrent oldal) belépéseket és a preferenciákat;
- a beállításokat és a torrenteket, a letöltött adatokkal együtt.

**Támogatott verziók:** v0.17.0 – v0.22.0. A v0.18.0 óta nem változott a
`manifest.json` elérési útja. Régebbi verzióknál előbb frissíts v0.18-ra.

1. Állítsd le a szervert: `docker compose down`
2. A `docker-compose.yml`-ben cseréld az image-et az új verzióra. Az új verzió
   a régi `HTTP_PORT`/`HTTPS_PORT` helyett a **7070**-es porton figyel, pl.
   `"4080:7070"`. A futtatás végén az eszköz megmondja a `HOST_IP` vagy
   `REVERSE_PROXY_DOMAIN` értékét.
3. Próbafuttatás. Semmi nem változik, csak jelentés készül:
   ```sh
   docker compose run --rm stremhu-source python -m app.legacy_migration --dry-run
   ```
4. Migrálás:
   ```sh
   docker compose run --rm stremhu-source python -m app.legacy_migration
   ```
5. Indítsd el a szervert: `docker compose up -d`

A jelentés az adatmappában van: `data/migration/<időpont>/report.md`.
- **What to do next:** ez a rész a szükséges beállításokat sorolja fel.
- **Lossy:** ez a rész azt, ami nem vihető át, pl. a tiltott torrent oldalakat.
- **A régi fájlok** a `data/migration/<időpont>/old-data/` mappában maradnak.
- **Hiba esetén** az eszköz mindent visszaállít.

Ha a régi adatokkal indítod az új verziót, a szerver nem indul el, hanem
kiírja a fenti parancsokat.

---

## English

v0.23.0 re-architected StremHU Source, so v0.22.x and older can't be upgraded
in place by just changing the image. The built-in migration tool carries over
more than the downloads:
- users and passwords;
- API keys, so Stremio/Kodi addon URLs and paired devices keep working;
- indexer logins and preferences;
- settings, and torrents together with their downloaded data.

**Supported releases:** v0.17.0 – v0.22.0. The `manifest.json` path hasn't
changed since v0.18.0. Upgrade older installs to v0.18 first.

1. Stop the server: `docker compose down`
2. In `docker-compose.yml`, switch the image to the new version. The new
   version listens on port **7070** instead of the old `HTTP_PORT`/`HTTPS_PORT`,
   e.g. `"4080:7070"`. At the end of the run the tool tells you the
   `HOST_IP` or `REVERSE_PROXY_DOMAIN` value.
3. Dry run. Nothing changes, you get a report:
   ```sh
   docker compose run --rm stremhu-source python -m app.legacy_migration --dry-run
   ```
4. Migrate:
   ```sh
   docker compose run --rm stremhu-source python -m app.legacy_migration
   ```
5. Start the server: `docker compose up -d`

The report is in your data folder: `data/migration/<time>/report.md`.
- **What to do next:** this section lists the settings you need.
- **Lossy:** this section lists what couldn't be carried over, e.g. blocked torrent sites.
- **Old files** are kept in `data/migration/<time>/old-data/`.
- **On failure** the tool rolls everything back.

If you start the new version on old data, the server doesn't start: it prints
the commands above instead.

### Without docker compose

```sh
docker run --rm -it -v /path/to/data:/app/data -e TZ=Europe/Budapest \
  <image> python -m app.legacy_migration --dry-run
```

Use the same `TZ` as the server, because timestamps are stored in local time.
`docker compose run` takes it from your compose file automatically.

### Options

| Option | |
|---|---|
| `--dry-run` | Convert into a scratch database and write a report; change nothing |
| `--source PATH` | Migrate from a separate old data folder (mount it) into `/app/data` instead of in place |
| `--downloads move\|copy\|keep` | With `--source`: what to do with the old downloads (default `move`) |
| `--overwrite` | Replace an existing new-version database; it is backed up first |
| `--no-verify-torrents` | Skip checking the torrent data on disk with libtorrent |
| `--config PATH` | Use a modified `versions.toml` |

---

## Fejlesztőknek / For developers

The code is in `server/app/legacy_migration/`. It works like this:
1. It snapshots and dumps the old SQLite database, read-only.
2. It creates the new database with the app's own alembic migrations and
   boot-time seed sync.
3. It converts the rows and inserts them through the app's ORM models in one
   transaction.
4. It verifies the result through the app's repositories and libtorrent.

Everything release-specific is data in `versions.toml`:
- how each old release is detected (its last TypeORM migration);
- its folder layout, whether it kept resume data, and its trackers;
- the preference value maps;
- the settings keys and their defaults.

To support another old release, add a `[[versions]]` entry there. No code
change is needed.

`tests/test_legacy_migration.py` checks the mappings against this app's seeded
attributes and indexers, and migrates a genuine data folder of every supported
era end to end. Those folders are built by `tests/legacy_fixture.py` from the
schema snapshots in `tests/data/legacy/`. So when a later change to the models
or seeds breaks the migration, CI catches it.
