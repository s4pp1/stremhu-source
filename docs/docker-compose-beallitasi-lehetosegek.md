# Docker Compose beállítási lehetőségek

A StremHU Source futtatása Docker-el lehetséges. A lefrissebb image a `s4pp1/stremhu-source:latest` néven érhető el a Docker Hub-on.

A futtatása nem igényel konfigurációt, de van rá lehetőség ezeket tételesen tartalmazza a dokumentáció.

Péda `docker-compose.yaml` fájl az indításhoz:

```yaml
services:
  stremhu-source:
    image: s4pp1/stremhu-source:latest
    container_name: stremhu-source
    ports:
      - 3000:3000
      - 6881:6881
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    networks:
      - stremhu

networks:
  stremhu:
    driver: bridge
```

Ha szeretnéd, hogy a tényleges adat másik HDD-n legyen tárolva, akkor így tudod konfigurálni.

```yaml
services:
  stremhu-source:
    volumes:
      - ./data/database:/app/data/database
      - ./data/torrents:/app/data/torrents

      # A ":" elötti részbe add meg a teljes elérési útját a mappának, ahol tárolni szeretnéd az adatot.
      - /kulso/hdd/mappa:/app/data/downloads
```

## Konfigurálható környezeti változók

| Válozó elnevezése               | Leírása                                                                                                                                            |       Alap értéke       |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------: |
| `HTTP_PORT`                     | Ezen a porton fog elindulni a szerver.                                                                                                             |          3000           |
| `HTTPS_PORT`                    | Ezen a porton fut a HTTPS szerver, amennyiben a beállításoknál a `Hozzáférés otthoni hálózaton` van beállítva.                                     |          3443           |
| `SESSION_SECRET`                | Session titkosításának beállítása.                                                                                                                 |     stremhu-source      |
| `TORRENT_CLIENT`                | Beállítja, hogy a libtorrent vagy a WebTorrent legyen használva                                                                                    |       web-torrent       |
| `TORRENT_PORT`                  | Torrent kliens ezt a portot használja a seedelésre                                                                                                 |          6881           |
| `TORRENT_PEER_LIMIT`            | Torrent kliens peer limit beállítása, torrentenként értendő. Minnél több peer-re csatlakozik annál magasabb a RAM és CPU terhelés.                 |           20            |
| `WEB_TORRENT_STORE_CACHE_SLOTS` | Web Torrent hány darab chunk-ot tart memóriában, minnél magasabb annál kevesebb lemez-I/O, gyorsabb hozzáférés, de több RAM-ot használ a rendszer. |           10            |
| `NCORE_URL`                     | nCore weboldal URL módósítása esetén van lehetőség a módosításra.                                                                                  |    https://ncore.pro    |
| `NCORE_MAX_CONCURRENT`          | Meghatározza, hogy egyidejűleg hány kérés indulhat az nCore irányába, ha túl magas a szám a tracker megtagadja a kérést.                           |            5            |
| `BITHUMEN_URL`                  | BitHUmen weboldal URL módósítása esetén van lehetőség a módosításra.                                                                               |   https://bithumen.be   |
| `BITHUMEN_MAX_CONCURRENT`       | Meghatározza, hogy egyidejűleg hány kérés indulhat a BitHUmen irányába, ha túl magas a szám a tracker megtagadja a kérést.                         |            5            |
| `MAJOMPARADE_URL`               | Majomparádé weboldal URL módósítása esetén van lehetőség a módosításra.                                                                            | https://majomparade.euo |
| `MAJOMPARADE_MAX_CONCURRENT`    | Meghatározza, hogy egyidejűleg hány kérés indulhat a Majomparádé irányába, ha túl magas a szám a tracker megtagadja a kérést.                      |            5            |

> [!WARNING]
> Ha a beállításoknál a `Hozzáférés otthoni hálózaton` van kiválasztva, akkor a `HTTPS_PORT`-on beállított érték legyen a `target` a `docker-compose.yaml`-ben. `target` és a `published` port pedig azonos legyen a működés érdekében!

> [!NOTE]
> Ha a beállításoknál nem a `Hozzáférés otthoni hálózaton` van kiválasztva, akkor a `HTTPS_PORT` nem érhető el. Ha szeretnéd elérhetővé tenni az interneten, akkor nézd meg a következő útmutatót: ["StremHU Source elérése az internetről"](./stremhu-source-elerese-az-internetrol.md)
