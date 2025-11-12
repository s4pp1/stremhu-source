# Docker Compose beállítási lehetőségek

A StremHU | Source futtatása Docker-el lehetséges. A lefrissebb image a `s4pp1/stremhu-source:latest` néven érhető el a Docker Hub-on.

A futtatása nem igényel konfigurációt, de van rá lehetőség ezeket tételesen tartalmazza a dokumentáció.

Péda `docker-compose.yaml` fájl az indításhoz:

```yaml
services:
  stremhu-source:
    image: s4pp1/stremhu-source:latest
    container_name: stremhu-source
    ports:
      - target: 3000
        published: 3000
      - target: 6881
        published: 6881
    volumes:
      - type: bind
        source: ./data
        target: /app/data
    restart: unless-stopped
    networks: [stremhu-net]

networks:
  stremhu-net:
    driver: bridge
```

## Konfigurálható környezeti változók

| Válozó elnevezése  | Leírása                                                                                                        |       Alap értéke       |
| ------------------ | -------------------------------------------------------------------------------------------------------------- | :---------------------: |
| `HTTP_PORT`        | Ezen a porton fog elindulni a szerver.                                                                         |          3000           |
| `HTTPS_PORT`       | Ezen a porton fut a HTTPS szerver, amennyiben a beállításoknál a `Hozzáférés otthoni hálózaton` van beállítva. |          3443           |
| `SESSION_SECRET`   | Session titkosításának beállítása.                                                                             |     stremhu-source      |
| `WEB_TORRENT_PORT` | Web Torrent ezt a portot használja a seedelésre                                                                |          6881           |
| `NCORE_URL`        | nCore weboldal URL módósítása esetén van lehetőség a módosításra.                                              |    https://ncore.pro    |
| `BITHUMEN_URL`     | BitHUmen weboldal URL módósítása esetén van lehetőség a módosításra.                                           |   https://bithumen.be   |
| `MAJOMPARADE_URL`  | Majomparádé weboldal URL módósítása esetén van lehetőség a módosításra.                                        | https://majomparade.euo |

> [!NOTE]
> Ha a beállításoknál nem a `Hozzáférés otthoni hálózaton` van kiválasztva, akkor a `HTTPS_PORT` nem érhető el. Ha szeretnéd elérhetővé tenni az interneten, akkor használd a `HTTP_PORT`-ot és erre mutasson a `Reverse Proxy` (használd például a [Cloudflare Tunnel](https://www.cloudflare.com/products/tunnel/)-t).
