## StremHU | Source elérése az internetről

Ebben a fejezetben azt mutatjuk meg, hogyan tudod a StremHU | Source-ot úgy beállítani, hogy **az otthoni hálózatodon kívülről is elérd** (pl. mobilnetről, munkahelyről).

### Mit fogunk csinálni?

Ahhoz, hogy kívülről is elérd a StremHU | Source-ot, három dolog kell:

1. **Egy név (domain / hostnév)**  
   – pl. `stremhu.valami.hu` vagy `stremhu.duckdns.org`.

2. **Egy reverse proxy**, ami a kintről érkező kéréseket továbbítja a StremHU | Source felé  
   – pl. Synology Reverse Proxy, Caddy, Traefik stb.

3. **Egy megoldás a változó IP cím követésére (DDNS – Dynamic DNS)**  
   – pl. DuckDNS, No-IP, Synology DDNS.

> Ez egy haladó rész. Itt már routert, domainnevet és tanúsítványokat (HTTPS) is érintünk. Ha bizonytalan vagy, érdemes lépésről lépésre haladni, és először csak a helyi hálózatos beállítást beüzemelni.

---

### 1. Domain vagy hostnév beszerzése

Internet felől általában **nem IP címmel**, hanem **névvel** érjük el a szolgáltatásokat (pl. `valami.hu`). Neked is kell egy ilyen név.

Három tipikus lehetőség:

#### 1.1. Synology DDNS (ha Synology NAS-od van)

Synology tud adni neked egy ilyen címet, pl.:

- `barmi.synology.me`

Ezt a DSM felületén tudod beállítani a **DDNS** résznél; ilyenkor a NAS automatikusan frissíti a címet, ha változik az otthoni IP-d.

**Előny:**

- semmit nem kell külön regisztrálni, minden a NAS-on történik.

**Hátrány:**

- csak akkor opció, ha tényleg van Synology NAS-od.

#### 1.2. Ingyenes DDNS szolgáltatás (DuckDNS, No-IP, stb.)

Ha nincs Synology NAS, használhatsz ingyenes DDNS-t, pl.:

- DuckDNS
- No-IP

A folyamat általában:

1. Regisztrálsz a szolgáltatónál.
2. Létrehozol egy hostnevet (pl. `stremhu.duckdns.org`).
3. Kapni fogsz egy tokent / jelszót, amit az IP-frissítéshez használsz.

#### 1.3. Saját domain regisztrálása (pl. valami.hu)

Ha „saját” domainnevet szeretnél (pl. `stremhu.valami.hu`), akkor:

1. Regisztrálsz egy domain-regisztrátornál (pl. Cloudflare, Namecheap, stb.).
2. Megveszed a domaint (éves díj).
3. A DNS rekordokat te kezeled (A rekord, CNAME, stb.).
4. A dinamikus IP követésére használhatsz:
   - a regisztrátor saját DDNS/API funkcióját, vagy
   - egy külső DDNS-klienst, ami a DNS rekordot frissíti.

---

### 2. Változó IP cím kezelése (DDNS)

A legtöbb otthoni internet-előfizetés **dinamikus IP címet** ad – időnként megváltozhat. Ha csak simán A rekordot állítasz a domainen, az **el fog romlani**, amikor az IP-d változik.

Itt jön be a DDNS (Dynamic DNS):

- A DDNS szolgáltató (Synology DDNS, DuckDNS, No-IP stb.) ad neked egy hostnevet.
- A NAS-od / géped / routered időnként „szól” a szolgáltatónak:
  - „Helló, most ez az IP címem.”
- A DDNS pedig frissíti a rekordot, hogy a hostnév **mindig** a jelenlegi IP-re mutasson.

**Gyakorlati lépések:**

1. Válassz DDNS szolgáltatót (Synology DDNS, DuckDNS, No-IP).
2. Hozz létre egy hostnevet (pl. `stremhu.duckdns.org`).
3. Állítsd be a DDNS klienst:
   - Synology-n: DSM felületen, **DDNS** résznél.
   - Sok routerben is van „Dynamic DNS” menüpont.
   - Vagy futtatsz egy kis scriptet / Docker konténert, ami frissíti az IP-t.

---

### 3. Reverse proxy beállítása

A reverse proxy az a „kapuőr”, ami az internet felől érkező kérést fogadja, és továbbítja a belső szolgáltatás felé (StremHU | Source).

Általános séma:

```text
Internet → [Reverse proxy + HTTPS] → StremHU | Source (pl. 192.168.1.100:3000)
```

#### 3.1. Synology Reverse Proxy (ha DSM-et használsz)

Synology DSM 7-ben van beépített reverse proxy, amit a vezérlőpulton keresztül tudsz beállítani.

Lépések nagy vonalakban:

1. Lépj be a DSM felületre.
2. Nyisd meg a **Vezérlőpult** (Control Panel) menüpontot.
3. Keresd meg az **Bejelentkezési portál** / **Speciális** részt.
4. Ott válaszd a **Fordított Proxy** lehetőséget.
5. Hozz létre egy új szabályt:

   **Forrás (Source):**

   - Protokoll: `HTTPS`
   - Állomásnév: pl. `stremhu.valami.hu`
   - Port: `443`

   **Cél (Destination):**

   - Protokoll: `HTTP`
   - Állomásnév: pl. `192.168.1.100` (ahol a StremHU konténer fut)
   - Port: `3000` (ahogy lokálban beállítottad)

Ezzel elérted, hogy amikor kintről valaki a `https://stremhu.valami.hu` címet nyitja meg, a reverse proxy továbbdobja a kérést a helyi StremHU | Source-ra.

#### 3.2. Caddy mint reverse proxy (NAS-tól független megoldás)

Ha nem Synology-t használsz (vagy saját megoldást szeretnél), nagyon kényelmes reverse proxy a **Caddy**:

- automatikus HTTPS (Let’s Encrypt / ZeroSSL),
- egyszerű konfiguráció: akár 3–4 soros Caddyfile is elég.

Egyszerű példa Caddyfile-ra:

```caddy
stremhu.valami.hu {
    reverse_proxy 192.168.1.100:3000
}
```

Ha ezt lefuttatod, a Caddy:

- megszerzi és automatikusan megújítja a tanúsítványt a `stremhu.valami.hu` névre,
- továbbítja a kéréseket a StremHU | Source felé a helyi hálózaton.

Caddyt futtathatsz Dockerben is, akár ugyanazon a gépen vagy NAS-on, ahol a StremHU konténer fut.

---

### 4. Porttovábbítás (router)

Hiába van domain és reverse proxy, ha az otthoni routered nem engedi be kintről a forgalmat.

A routered admin felületén be kell állítanod, hogy:

- a 443-as (HTTPS) port kívülről menjen a NAS/gép 443-as portjára (ahol a reverse proxy figyel).

Így néz ki az útvonal:

```text
Internet (443) → Router → NAS/gép (443) → Reverse proxy → StremHU | Source
```

---

### 5. Összefoglaló ajánlott útvonal

Egy tipikus, jól működő recept:

1. DDNS beállítása
   - Synology DDNS vagy DuckDNS / No-IP hostnév.
2. Reverse proxy beállítása
   - Synology Reverse Proxy vagy Caddy (Dockerben).
3. Router porttovábbítás
   - kívül 443 → belül 443 (reverse proxy).
4. StremHU | Source URL beállítása
   - a StremHU | Source „Addon URL”-jéhez már a publikus domaint írod (pl. `https://stremhu.valami.hu`).
5. Addon beállítása Stremióban
   - a Stremio felé is ezt az URL-t adod meg.

Ha ez megvan, ugyanazzal az URL-lel eléred a StremHU | Source-ot otthonról és az internetről is.

---

### 6. Biztonsági megjegyzések

- Használj HTTPS-t ez a Stremio működéséhez is szükséges (Let’s Encrypt, Caddy automatikus tanúsítványa, Cloudflare, stb.).
- A tracker belépési adataidat mindig óvd, és csak a StremHU | Source felületén add meg őket.
