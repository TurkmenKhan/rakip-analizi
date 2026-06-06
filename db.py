import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rakip_analizi.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_tables():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS isps (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            url             TEXT    NOT NULL,
            kategori        TEXT    DEFAULT 'belirsiz',
            aktif           INTEGER DEFAULT 1,
            eklenme_tarihi  TEXT    DEFAULT (datetime('now','localtime')),
            last_parsed_ts  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            isp_id          INTEGER NOT NULL REFERENCES isps(id),
            kontrol_zamani  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            parse_json      TEXT,
            llm_cagrildi    INTEGER DEFAULT 0,
            hata            TEXT
        );

        CREATE TABLE IF NOT EXISTS packages (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            isp_id                INTEGER NOT NULL REFERENCES isps(id),
            paket_key             TEXT    NOT NULL UNIQUE,
            paket_adi             TEXT,
            hiz_mbps              INTEGER,
            hiz_yukleme_mbps      INTEGER,
            teknoloji             TEXT,
            fiyat_ilk_donem       REAL,
            fiyat_ortalama        REAL,
            fiyat_sonraki_donem   REAL,
            ilk_donem_ay          INTEGER,
            fiyat_sabit_mi        INTEGER DEFAULT 0,
            sozlesme_suresi_ay    INTEGER DEFAULT 0,
            taahhut_var           INTEGER DEFAULT 0,
            modem                 TEXT,
            modem_ucreti_aylik    REAL    DEFAULT 0,
            sadece_yeni_musteri   INTEGER DEFAULT 0,
            kurulum_ucreti        REAL    DEFAULT 0,
            one_cikan_ifadeler    TEXT    DEFAULT '[]',
            ek_paketler           TEXT    DEFAULT '[]',
            bolge_kisiti          TEXT,
            kampanya_bitis        TEXT,
            ham_metin             TEXT,
            kaynak_url            TEXT,
            son_guncelleme        TEXT    DEFAULT (datetime('now','localtime')),
            aktif                 INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS package_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            paket_key       TEXT    NOT NULL,
            isp_id          INTEGER NOT NULL REFERENCES isps(id),
            degisim_zamani  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            alan            TEXT    NOT NULL,
            eski_deger      TEXT,
            yeni_deger      TEXT,
            aciklama        TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            isp_id          INTEGER NOT NULL REFERENCES isps(id),
            paket_key       TEXT,
            olusma_zamani   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            tur             TEXT    NOT NULL,
            mesaj           TEXT    NOT NULL,
            goruldu         INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS isp_urls (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            isp_id         INTEGER NOT NULL REFERENCES isps(id),
            url            TEXT    NOT NULL,
            etiket         TEXT,
            aktif          INTEGER DEFAULT 1,
            cd_uuid        TEXT,
            parse_pkg      INTEGER DEFAULT 1,
            last_parsed_ts INTEGER DEFAULT 0,
            UNIQUE(isp_id, url)
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_isp    ON snapshots(isp_id, kontrol_zamani DESC);
        CREATE INDEX IF NOT EXISTS idx_packages_isp     ON packages(isp_id);
        CREATE INDEX IF NOT EXISTS idx_pkg_history_key  ON package_history(paket_key, degisim_zamani DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_goruldu   ON alerts(goruldu, olusma_zamani DESC);
        CREATE INDEX IF NOT EXISTS idx_isp_urls         ON isp_urls(isp_id);
    """)
    conn.commit()
    conn.close()
    print(f"Tablolar hazır: {DB_PATH}")


def save_snapshot(isp_id: int, parse_json: str | None = None,
                  llm_cagrildi: int = 0, hata: str | None = None) -> int:
    """Sadece parse sonucunu kaydeder — sayfa metni saklanmaz."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO snapshots (isp_id, parse_json, llm_cagrildi, hata) VALUES (?,?,?,?)",
        (isp_id, parse_json, llm_cagrildi, hata)
    )
    conn.commit()
    snapshot_id = cur.lastrowid
    conn.close()
    return snapshot_id


def get_active_isps() -> list[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM isps WHERE aktif=1
        ORDER BY CASE WHEN kategori='rakip' THEN 0 ELSE 1 END, name
    """).fetchall()
    conn.close()
    return rows


def get_isp_url_selectors_with_cd(isp_id: int) -> list[dict]:
    """
    ISS için {id, url, selector, cd_uuid, parse_pkg, last_parsed_ts} dict listesini döndürür.
    parse_pkg=0 → değişim tespiti için izle ama package parse'a katma.
    isp_urls tablosu boşsa isps.url'den döner.
    """
    conn = get_conn()
    extra = conn.execute(
        """SELECT id, url, selector, cd_uuid,
                  COALESCE(parse_pkg,1) as parse_pkg,
                  COALESCE(last_parsed_ts,0) as last_parsed_ts
           FROM isp_urls WHERE isp_id=? AND aktif=1""",
        (isp_id,)
    ).fetchall()
    if extra:
        result = [{"id": r["id"], "url": r["url"], "selector": r["selector"] or None,
                   "cd_uuid": r["cd_uuid"], "parse_pkg": r["parse_pkg"],
                   "last_parsed_ts": r["last_parsed_ts"]} for r in extra]
    else:
        row = conn.execute("SELECT url FROM isps WHERE id=?", (isp_id,)).fetchone()
        result = [{"id": None, "url": row["url"], "selector": None,
                   "cd_uuid": None, "parse_pkg": 1, "last_parsed_ts": 0}] if row else []
    conn.close()
    return result


def get_last_parsed_ts(isp_id: int) -> int:
    """ISS'in CD last_changed bazlı son parse timestamp'ini döndürür."""
    conn = get_conn()
    row = conn.execute("SELECT last_parsed_ts FROM isps WHERE id=?", (isp_id,)).fetchone()
    conn.close()
    return int(row["last_parsed_ts"] or 0) if row else 0


def update_last_parsed_ts(isp_id: int, ts: int):
    """ISS'in son parse timestamp'ini günceller (geriye dönük uyumluluk)."""
    conn = get_conn()
    conn.execute("UPDATE isps SET last_parsed_ts=? WHERE id=?", (ts, isp_id))
    conn.commit()
    conn.close()


def update_url_last_parsed_ts(url_id: int, ts: int):
    """Tek bir isp_urls satırının last_parsed_ts'ini günceller."""
    if url_id is None:
        return
    conn = get_conn()
    conn.execute("UPDATE isp_urls SET last_parsed_ts=? WHERE id=?", (ts, url_id))
    conn.commit()
    conn.close()


def add_isp_url(isp_name: str, url: str, etiket: str = None):
    conn = get_conn()
    isp = conn.execute("SELECT id FROM isps WHERE name=?", (isp_name,)).fetchone()
    if not isp:
        conn.close()
        raise ValueError(f"ISS bulunamadı: {isp_name}")
    conn.execute(
        "INSERT OR IGNORE INTO isp_urls (isp_id, url, etiket) VALUES (?,?,?)",
        (isp["id"], url, etiket)
    )
    conn.commit()
    conn.close()


def _paket_slug(pkg: dict) -> str:
    import re
    name = (pkg.get("paket_adi") or "").strip()
    if name:
        slug = re.sub(r"[^a-z0-9]", "_", name.lower())
        slug = re.sub(r"_+", "_", slug).strip("_")
        return slug[:60]
    # paket_adi yoksa modem + fiyat ile ayırt et
    modem  = (pkg.get("modem") or "x")
    fiyat  = str(pkg.get("fiyat_ilk_donem") or "0").replace(".", "_")
    return f"{modem}_{fiyat}"


def upsert_package(isp_id: int, pkg: dict):
    slug  = _paket_slug(pkg)
    fiyat = int(pkg.get("fiyat_ilk_donem") or 0)
    key   = f"{isp_id}|{pkg.get('hiz_mbps')}|{pkg.get('teknoloji')}|{pkg.get('sozlesme_suresi_ay', 0)}|{fiyat}|{slug}"
    import json
    conn = get_conn()
    existing = conn.execute("SELECT * FROM packages WHERE paket_key=?", (key,)).fetchone()

    fields = {
        "isp_id":               isp_id,
        "paket_key":            key,
        "paket_adi":            pkg.get("paket_adi"),
        "hiz_mbps":             pkg.get("hiz_mbps"),
        "hiz_yukleme_mbps":     pkg.get("hiz_yukleme_mbps"),
        "teknoloji":            pkg.get("teknoloji"),
        "fiyat_ilk_donem":      pkg.get("fiyat_ilk_donem"),
        "fiyat_ortalama":       pkg.get("fiyat_ortalama"),
        "fiyat_sonraki_donem":  pkg.get("fiyat_sonraki_donem"),
        "ilk_donem_ay":         pkg.get("ilk_donem_ay"),
        "fiyat_sabit_mi":       int(bool(pkg.get("fiyat_sabit_mi"))),
        "sozlesme_suresi_ay":   pkg.get("sozlesme_suresi_ay", 0),
        "taahhut_var":          int(bool(pkg.get("taahhut_var"))),
        "modem":                pkg.get("modem"),
        "modem_ucreti_aylik":   pkg.get("modem_ucreti_aylik", 0),
        "sadece_yeni_musteri":  int(bool(pkg.get("sadece_yeni_musteri"))),
        "kurulum_ucreti":       pkg.get("kurulum_ucreti", 0),
        "one_cikan_ifadeler":   json.dumps(pkg.get("one_cikan_ifadeler", []), ensure_ascii=False),
        "ek_paketler":          json.dumps(pkg.get("ek_paketler", []), ensure_ascii=False),
        "bolge_kisiti":         pkg.get("bolge_kisiti"),
        "kampanya_bitis":       pkg.get("kampanya_bitis"),
        "ham_metin":            pkg.get("ham_metin"),
        "kaynak_url":           pkg.get("kaynak_url"),
        "aktif":                1,
    }

    if existing:
        placeholders = ", ".join(f"{k}=?" for k in fields if k not in ("isp_id", "paket_key"))
        values = [v for k, v in fields.items() if k not in ("isp_id", "paket_key")]
        values.append(key)
        conn.execute(
            f"UPDATE packages SET {placeholders}, son_guncelleme=datetime('now','localtime') WHERE paket_key=?",
            values
        )
    else:
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        conn.execute(f"INSERT INTO packages ({cols}) VALUES ({placeholders})", list(fields.values()))

    conn.commit()
    conn.close()
    return key, dict(existing) if existing else None


def mark_packages_inactive(isp_id: int, active_keys: list[str]):
    conn = get_conn()
    if active_keys:
        placeholders = ",".join("?" for _ in active_keys)
        conn.execute(
            f"UPDATE packages SET aktif=0, son_guncelleme=datetime('now','localtime') "
            f"WHERE isp_id=? AND paket_key NOT IN ({placeholders}) AND aktif=1",
            [isp_id] + active_keys
        )
    else:
        conn.execute(
            "UPDATE packages SET aktif=0 WHERE isp_id=? AND aktif=1", (isp_id,)
        )
    conn.commit()
    conn.close()


def add_alert(isp_id: int, tur: str, mesaj: str, paket_key: str | None = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO alerts (isp_id, paket_key, tur, mesaj) VALUES (?, ?, ?, ?)",
        (isp_id, paket_key, tur, mesaj)
    )
    conn.commit()
    conn.close()


def add_package_history(isp_id: int, paket_key: str, alan: str,
                        eski: str, yeni: str, aciklama: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO package_history (paket_key, isp_id, alan, eski_deger, yeni_deger, aciklama) VALUES (?,?,?,?,?,?)",
        (paket_key, isp_id, alan, eski, yeni, aciklama)
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
