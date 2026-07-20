"""
changedetection.io API köprüsü.


Büyük/rakip ISS'ler için Layer 1 (değişim tespiti) changedetection.io'ya devredilir.
Bu modül CD API'sini sarar; main.py scraping yerine buradan snapshot alır.

Kullanım:
    bridge = ChangedetectionBridge()
    watches = bridge.get_all_watches()
    url_map = bridge.build_url_to_uuid_map(watches)
    snapshot = bridge.get_latest_snapshot(uuid)
"""
import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

CD_BASE_URL = os.environ.get("CD_BASE_URL", "http://localhost:5000")
CD_API_KEY  = os.environ.get("CD_API_KEY",  "9f27a45aed03c826410dc5be255db03b")

_TIMEOUT     = 20   # saniye
_POOL_SIZE   = 20   # max paralel bağlantı
_MAX_WORKERS = 15   # paralel thread sayısı


class ChangedetectionBridge:
    def __init__(self, base_url: str = CD_BASE_URL, api_key: str = CD_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
        # Connection pool büyüt (paralel fetch için)
        adapter = HTTPAdapter(pool_connections=_POOL_SIZE, pool_maxsize=_POOL_SIZE)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ── Watches ────────────────────────────────────────────────────────────────

    def get_all_watches(self) -> dict:
        """
        Tüm izlenen URL'leri döndürür.
        Dönüş: {uuid: {"url": ..., "last_changed": int_ts, "last_error": ...}}
        """
        try:
            r = self.session.get(f"{self.base_url}/api/v1/watch", timeout=_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logging.warning(f"[CD] get_all_watches hata: {e}")
            return {}

    def get_changed_watches(self, since_ts: int) -> dict:
        """
        since_ts'den (unix timestamp) sonra değişen watch'ları döndürür.
        Dönüş: {uuid: watch_info}
        """
        watches = self.get_all_watches()
        return {
            uuid: w for uuid, w in watches.items()
            if (w.get("last_changed") or 0) > since_ts
               and not w.get("last_error")
        }

    def build_url_to_uuid_map(self, watches: dict | None = None) -> dict:
        """
        URL → UUID eşleme tablosu. Normalize edilmiş URL'lerle karşılaştırır.
        Dönüş: {normalized_url: uuid}
        """
        if watches is None:
            watches = self.get_all_watches()
        return {_norm_url(w.get("url", "")): uuid for uuid, w in watches.items()}

    # ── Snapshot ───────────────────────────────────────────────────────────────

    def get_latest_snapshot(self, uuid: str) -> str | None:
        """
        uuid'nin en son snapshot metnini döndürür (changedetection'ın çektiği metin).
        Dönüş: str veya None (hata/boş)
        """
        try:
            r = self.session.get(
                f"{self.base_url}/api/v1/watch/{uuid}/history/latest",
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                text = r.text.strip()
                return text if text else None
            logging.warning(f"[CD] snapshot {uuid}: HTTP {r.status_code}")
            return None
        except Exception as e:
            logging.warning(f"[CD] get_latest_snapshot {uuid}: {e}")
            return None

    def get_snapshot_hash(self, uuid: str) -> str | None:
        """Snapshot metninin MD5'ini döndürür (değişim tespiti için)."""
        text = self.get_latest_snapshot(uuid)
        if text is None:
            return None
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get_multi_snapshot(self, uuids: list[str]) -> tuple[str, str]:
        """
        Birden fazla UUID için snapshot'ları birleştirir.
        Dönüş: (birlesik_metin, md5_hash)
        Metin, fetch_selector_multi'ye uyumlu === URL === bölümler içerir.
        """
        parts = []
        for uuid in uuids:
            # URL'yi watch bilgisinden al (veya doğrudan)
            text = self.get_latest_snapshot(uuid)
            if text:
                parts.append(text)

        combined = "\n---\n".join(parts)
        combined_hash = hashlib.md5(combined.encode("utf-8")).hexdigest()
        return combined, combined_hash

    def get_multi_snapshot_with_urls(self, uuid_url_pairs: list[tuple[str, str]],
                                     max_workers: int = _MAX_WORKERS) -> tuple[str, str]:
        """
        [(uuid, url), ...] listesi için snapshot'ları paralel olarak çeker ve
        URL section header'larıyla birleştirir.
        Dönüş: (birlesik_metin, md5_hash) — mevcut selector_metin formatıyla uyumlu.
        """
        if not uuid_url_pairs:
            return "", hashlib.md5(b"").hexdigest()

        # Paralel fetch
        results: dict[str, tuple[str, str]] = {}  # uuid -> (url, text)

        def _fetch_one(pair):
            uuid, url = pair
            text = self.get_latest_snapshot(uuid)
            return uuid, url, text

        with ThreadPoolExecutor(max_workers=min(max_workers, len(uuid_url_pairs))) as ex:
            futures = {ex.submit(_fetch_one, pair): pair for pair in uuid_url_pairs}
            for fut in as_completed(futures):
                try:
                    uuid, url, text = fut.result()
                    if text:
                        results[uuid] = (url, text)
                except Exception as e:
                    logging.warning(f"[CD] parallel fetch hata: {e}")

        # Orijinal sırayı koru (URL section'ları deterministic olsun)
        parts = []
        for uuid, url in uuid_url_pairs:
            if uuid in results:
                _, text = results[uuid]
                parts.append(f"=== {url} ===\n{text}")

        combined = "\n\n".join(parts)
        combined_hash = hashlib.md5(combined.encode("utf-8")).hexdigest()
        return combined, combined_hash

    # ── Recheck ────────────────────────────────────────────────────────────────

    def trigger_recheck(self, uuid: str) -> bool:
        """Belirtilen watch için anlık yeniden çekme tetikler."""
        try:
            r = self.session.get(
                f"{self.base_url}/api/v1/watch/{uuid}",
                params={"recheck": "1"},
                timeout=_TIMEOUT,
            )
            return r.status_code == 200
        except Exception as e:
            logging.warning(f"[CD] recheck {uuid}: {e}")
            return False

    def recheck_unfetched(self) -> int:
        """
        last_changed=0 olan (hiç çekilmemiş) watch'ları hemen recheck ettirir.
        Döndürür: tetiklenen watch sayısı.
        """
        watches = self.get_all_watches()
        unfetched = [
            uuid for uuid, w in watches.items()
            if isinstance(w, dict) and (w.get("last_changed") or 0) == 0
        ]
        if not unfetched:
            return 0
        count = 0
        for uuid in unfetched:
            if self.trigger_recheck(uuid):
                count += 1
        if count:
            logging.info(f"[CD] {count} hiç çekilmemiş watch recheck tetiklendi")
        return count

    # ── DB Sync ────────────────────────────────────────────────────────────────

    def sync_uuids_to_db(self, dry_run: bool = False) -> dict:
        """
        1. isps tablosundaki URL'leri isp_urls'e migrate eder (kayıt yoksa).
        2. changedetection'daki URL'lerle isp_urls'i eşleştirir ve cd_uuid'leri günceller.

        Dönüş: {"updated": [...], "not_found": [...], "migrated": int}
        """
        from db import get_conn

        # Önce migrate — isp_urls kaydı olmayan ISS'lerin URL'lerini ekle
        migrated = 0 if dry_run else _migrate_isps_to_isp_urls()
        if migrated:
            logging.info(f"[CD sync] {migrated} ISS isp_urls'e taşındı")

        watches = self.get_all_watches()

        # GÜVENLİK: CD bağlantı hatası verirse get_all_watches boş {} döner.
        # Bunu "CD'de watch yok" sanıp DB'yi mahvetmemek için erken çık.
        # (Gerçekten watch silinmişse manuel müdahale gerek — sync bunu yapmasın.)
        if not watches:
            logging.error(
                "[CD sync] CD'den 0 watch geldi — muhtemelen bağlantı sorunu. "
                "DB'ye dokunulmadı. CD'yi kontrol edin ve tekrar deneyin."
            )
            return {"updated": [], "not_found": [], "migrated": migrated, "aborted": True}

        url_uuid_map = self.build_url_to_uuid_map(watches)

        conn = get_conn()
        rows = conn.execute("SELECT id, url FROM isp_urls WHERE aktif=1").fetchall()

        updated = []
        not_found = []

        for row in rows:
            norm = _norm_url(row["url"])
            uuid = url_uuid_map.get(norm)
            if uuid:
                if not dry_run:
                    conn.execute(
                        "UPDATE isp_urls SET cd_uuid=? WHERE id=?",
                        (uuid, row["id"])
                    )
                updated.append({"id": row["id"], "url": row["url"], "uuid": uuid})
            else:
                # CD'de yok → URL'yi pasif et
                if not dry_run:
                    conn.execute(
                        "UPDATE isp_urls SET aktif=0, cd_uuid=NULL WHERE id=?",
                        (row["id"],)
                    )
                not_found.append(row["url"])
                logging.warning(f"[CD sync] CD'de yok, pasif edildi: {row['url']}")

        if not dry_run:
            # CD'de hiç aktif URL'si kalmayan ISS'leri pasif et
            deactivated_isps = conn.execute("""
                SELECT DISTINCT i.id, i.name FROM isps i
                WHERE i.aktif=1
                  AND NOT EXISTS (
                      SELECT 1 FROM isp_urls u
                      WHERE u.isp_id=i.id AND u.aktif=1 AND u.cd_uuid IS NOT NULL
                  )
            """).fetchall()
            for isp in deactivated_isps:
                conn.execute("UPDATE isps SET aktif=0 WHERE id=?", (isp["id"],))
                logging.warning(f"[CD sync] CD'de URL yok, ISS pasif edildi: {isp['name']}")
            conn.commit()

        conn.close()

        # CD'de olup isp_urls'de eşleşmeyen watch'ları mevcut ISS'lere domain bazlı ekle
        added = _add_unmatched_cd_watches(watches, dry_run) if not dry_run else []

        logging.info(
            f"[CD sync] {len(updated)} URL eşleşti, "
            f"{len(not_found)} CD'de yok (pasif edildi), "
            f"{migrated} migrate edildi, {len(added)} yeni CD URL eklendi"
        )
        return {"updated": updated, "not_found": not_found, "migrated": migrated, "added": added}


# ── Yardımcı ───────────────────────────────────────────────────────────────────

def _migrate_isps_to_isp_urls() -> int:
    """
    isps tablosundaki her aktif ISS için isp_urls kaydı yoksa oluşturur.
    Bu sayede sync_uuids_to_db() tüm ISS'leri kapsayabilir.
    Döndürür: eklenen kayıt sayısı.
    """
    from db import get_conn
    conn = get_conn()
    rows = conn.execute("""
        SELECT i.id, i.url FROM isps i
        WHERE i.aktif=1
          AND NOT EXISTS (
              SELECT 1 FROM isp_urls u WHERE u.isp_id = i.id AND u.aktif=1
          )
    """).fetchall()
    count = 0
    for row in rows:
        conn.execute(
            "INSERT OR IGNORE INTO isp_urls (isp_id, url, aktif) VALUES (?,?,1)",
            (row["id"], row["url"])
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def _add_unmatched_cd_watches(watches: dict, dry_run: bool = False) -> list:
    """
    CD'de olup isp_urls'de eşleşmeyen watch'ları domain bazlı mevcut ISS'lere ekler.
    Eşleşmeyen ve yeni ISS gerektirenleri loglar, eklemez (kullanıcı kararı).
    Döndürür: eklenen {url, isp_id, uuid} listesi.
    """
    from urllib.parse import urlparse
    from db import get_conn

    conn = get_conn()

    # Mevcut aktif isp_urls (normalized)
    existing_normalized = {
        _norm_url(r["url"])
        for r in conn.execute("SELECT url FROM isp_urls WHERE aktif=1").fetchall()
    }

    # Aktif ISS'lerin domain → isp_id eşlemesi
    isps = conn.execute("SELECT id, url FROM isps WHERE aktif=1").fetchall()
    domain_to_isp: dict[str, int] = {}
    for isp in isps:
        try:
            domain = urlparse(isp["url"]).netloc.lower().lstrip("www.")
            if domain:
                domain_to_isp[domain] = isp["id"]
        except Exception:
            pass

    added = []
    for uuid, w in watches.items():
        url = w.get("url", "")
        if not url:
            continue
        if _norm_url(url) in existing_normalized:
            continue  # Zaten var

        # Domain bazlı ISS eşleştir
        try:
            domain = urlparse(url).netloc.lower().lstrip("www.")
        except Exception:
            domain = ""

        isp_id = domain_to_isp.get(domain)
        if isp_id is None:
            logging.warning(f"[CD sync] ISS eşleşmedi, isp_urls'e eklenemiyor: {url}")
            continue

        if not dry_run:
            conn.execute(
                "INSERT OR IGNORE INTO isp_urls (isp_id, url, aktif, cd_uuid) VALUES (?,?,1,?)",
                (isp_id, url, uuid)
            )
            logging.info(f"[CD sync] Yeni CD URL eklendi (isp_id={isp_id}): {url}")
        added.append({"url": url, "isp_id": isp_id, "uuid": uuid})

    if not dry_run:
        conn.commit()
    conn.close()
    return added


def _norm_url(url: str) -> str:
    """URL'yi karşılaştırma için normalize eder (trailing slash, tam lowercase, fragment kaldır)."""
    url = url.strip()
    # Fragment kaldır (#pricing gibi)
    if "#" in url:
        url = url.split("#")[0]
    url = url.rstrip("/")
    # Tamamını lowercase
    return url.lower()


# ── Singleton ─────────────────────────────────────────────────────────────────

_bridge: ChangedetectionBridge | None = None


def get_bridge() -> ChangedetectionBridge:
    """Global singleton bridge döndürür."""
    global _bridge
    if _bridge is None:
        _bridge = ChangedetectionBridge()
    return _bridge
