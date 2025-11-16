## StremHU | Source beüzemelése otthon

Lépésről lépésre útmutató, hogy otthon, a helyi hálózatodon tudd használni a StremHU | Source-ot.

### Mit érünk el a végére?

- A StremHU | Source egy Docker konténerként fog futni a gépen/NAS-on.
- Csak az otthoni hálózatodon lesz elérhető.
- A Stremio-ban hozzá tudod adni, mint kiegészítőt.

> [!NOTE]
> Ha azt szeretnéd, hogy az internetről is elérhető legyen (pl. mobilnetről), arról egy külön útmutató szól: ["StremHU | Source elérése az internetről"](./stremhu-source-elerese-az-internetrol.md)

---

### 1. Amire szükséged lesz (előfeltételek)

- Egy számítógép vagy NAS, amin fut a Docker.
  (pl. Docker Desktop Windows/Mac-en, vagy Container Manager Synology-n).
- Egy Stremio fiók és a Stremio alkalmazás - [https://www.stremio.com](https://www.stremio.com).
- StremHU | Source által támogatott tracker hozzáférés.

---

### 2. Külön mappa létrehozása a StremHU | Source számára

Először hozz létre egy mappát, ahova a StremHU | Source „csomagja” kerül.

- Windows-on például:
  `C:\stremhu-source`

- Mac / Linux alatt például:
  `~/stremhu-source`

A további lépésekben feltételezzük, hogy ebbe a mappába dolgozol.

---

### 3. A docker-compose.yaml fájl elhelyezése

Az előző lépésben létrehozott mappában hozz létre egy új fájlt `docker-compose.yaml` néven, és másold bele az alábbi tartalmat:

```yaml
services:
  stremhu-source:
    image: s4pp1/stremhu-source:latest
    container_name: stremhu-source
    ports:
      - target: 3000
        published: 3000
      - target: 3443
        published: 3443
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

> [!NOTE]
> Ez egy alap példa. Ha szeretnél rajta változtatni (image név, portok, ENV változók), nézd meg a részletes útmutatót: ["Docker Compose beállítási lehetőségek"](./docker-compose-beallitasi-lehetosegek.md)

---

### 4. A StremHU | Source elindítása Docker Compose-szal

- Windows: Start menü → „PowerShell” vagy „Parancssor”
- Mac: „Terminal” alkalmazás
- Linux: bármelyik terminál

1. Lépj be abba a mappába, ahova a `docker-compose.yaml` fájlt mentetted.

   - Windows például:

   ```powershell
   cd C:\stremhu-source
   ```

   - Mac / Linux például:

   ```bash
   cd ~/stremhu-source
   ```

2. Indítsd el a StremHU | Source-ot a következő paranccsal:

```bash
   docker compose up -d
```

- `up` = indítás
- `-d` = „detached” mód, azaz a háttérben fog futni

Ha minden rendben ment, a Docker létrehoz egy `stremhu-source` nevű konténert, ami ezentúl automatikusan fut (és ha leáll a gép, indításkor újra elindítható).

---

### 5. Ellenőrizd, hogy fut-e

Nyisd meg a böngészőt (Chrome, Edge, stb.), és írd be a címsorba:

```text
http://GEP_IP_CIME:3000
```

Példák:

- Ha saját gépeden fut a Docker, sokszor működik:
  - `http://localhost:3000`
- Ha NAS-on vagy másik gépen fut, akkor annak az IP címét használd, például:
  - `http://192.168.1.100:3000`

Mit kell látnod?

- A StremHU | Source felületét.
- Első indításkor admin fiókot kell létrehozni.

---

### 6. Tracker és URL beállítása

- A fiók létrehozása után hozzá kell adni a tracker-t, amit használni szeretnél a `Beállítások - Trackerek` résznél.

- A Stremio használatához be kell állítani az `Addon URL`-t a `Beállítások - Hozzáférés` résznél.
  - A `Hozzáférés otthoni hálózaton` legyen kiválaszva.
  - Ha az IP címed a `192.168.1.100` akkor következőképpen töltsd ki az `Addon URL`-t: `https://192-168-1-100.local-ip.medicmobile.org:3443` - Ezen az URL-en az addon felülete is elérhető.

Ezzel azt érted el, hogy a StremHU | Source ezzel az URL-el rendelkező információkat küld majd a Stremio-nak, amit el is fog fogadni.

---

### 7. StremHU | Source hozzáadása a Stremio-hoz

Nincs más dolgod, mint a `Fiókom` menüpontban a Stremio integráció a `Stremio integráció` résznél választani egy lehetőséget.

Ha mindent jól csináltál a Stremio elfogadta az URL-t és tudtad telepíteni az addont!

Nincs más dolgod mint élvezni a korlátlan streming élményt!
