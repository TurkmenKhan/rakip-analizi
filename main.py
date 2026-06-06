"""
Ana scheduler.
  - Rakip/büyük ISS'ler: her 30 dakikada bir
  - Diğer ISS'ler: her 2 saatte bir

Değişim tespiti: CD'nin last_changed timestamp'i ile.
LLM sadece gerçek içerik değişiminde çağrılır.
"""
import json
import time
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from concurrent.futures import ThreadPoolExecutor, as_completed

from db import (
    get_active_isps, get_isp_url_selectors_with_cd,
    get_last_parsed_ts, update_last_parsed_ts,
    update_url_last_parsed_ts,
    save_snapshot, add_alert, mark_packages_inactive,
)
from llm_parser              import parse_with_llm, map_pkg_with_url
from alerts                  import process
from push_db                 import push_db_to_github
from changedetection_bridge  import get_bridge

INTERVAL_RAKIP_DK   = 30
INTERVAL_DIGER_SAAT = 2
RAKIP_KATEGORILER   = {"rakip", "buyuk"}
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logging():
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(LOG_DIR, f"{today}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )


_URL_BATCH_THRESHOLD = 15   # Bu kadar URL'den fazlası → per-URL LLM modu


def _parse_per_url(bridge, infos: list[dict], isp_name: str) -> list[dict]:
    """
    Çok URL'li ISS'ler (ör. TT) için her URL'yi ayrı LLM çağrısıyla parse eder.
    infos: get_isp_url_selectors_with_cd() çıktısı (id, cd_uuid, url, ...)
    Sonuçları birleştirip döndürür; hız+taahhüt bazlı deduplikasyon uygular.
    """
    def _fetch_and_parse(info):
        uuid = info["cd_uuid"]
        url  = info["url"]
        text = bridge.get_latest_snapshot(uuid)
        if not text:
            return []
        pkgs = parse_with_llm(text, isp_name)
        # Her pakete kaynak URL'yi ekle
        for p in pkgs:
            p["kaynak_url"] = url
        return pkgs

    all_packages = []
    seen_keys = set()

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_fetch_and_parse, info): info for info in infos}
        for fut in as_completed(futures):
            try:
                pkgs = fut.result()
                for p in pkgs:
                    key = (p.get("hiz_mbps"), p.get("sozlesme_suresi_ay"), int(p.get("fiyat_ilk_donem") or 0))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_packages.append(p)
            except Exception as e:
                logging.warning(f"[per-URL parse hata] {e}")

    return all_packages


def run_once(sadece_rakip: bool = False):
    tum_isps = get_active_isps()
    if sadece_rakip:
        isps = [i for i in tum_isps if i["kategori"] in RAKIP_KATEGORILER]
        logging.info(f"=== Rakip kontrolü — {len(isps)} ISS ===")
    else:
        isps = tum_isps
        logging.info(f"=== Tam kontrol — {len(isps)} ISS ===")

    bridge = get_bridge()

    # CD'deki tüm watch durumlarını TEK seferde çek
    try:
        watches = bridge.get_all_watches()
    except Exception as e:
        logging.error(f"CD watches alınamadı: {e}")
        watches = {}

    # uuid → last_changed eşleme tablosu (hızlı lookup)
    uuid_ts: dict[str, int] = {
        uuid: int(w.get("last_changed") or 0)
        for uuid, w in watches.items()
        if isinstance(w, dict)
    }

    kontrol = degisim = llm_cagri = hata = 0

    for isp in isps:
        isp_id   = isp["id"]
        isp_name = isp["name"]

        try:
            url_infos = get_isp_url_selectors_with_cd(isp_id)

            # CD'de UUID'si olan URL'ler
            cd_infos = [i for i in url_infos if i["cd_uuid"]]

            if not cd_infos:
                # CD'de hiç URL'si yok → paketleri pasif yap
                mark_packages_inactive(isp_id, [])
                logging.info(f"[−] {isp_name} — CD'de yok, paketler pasif edildi")
                continue

            # Hangi URL'ler gerçekten değişti? (per-URL timestamp karşılaştırması)
            changed_infos = [
                i for i in cd_infos
                if uuid_ts.get(i["cd_uuid"], 0) > i["last_parsed_ts"]
            ]

            if not changed_infos:
                logging.debug(f"[=] {isp_name} — değişim yok")
                kontrol += 1
                continue

            logging.info(f"[~] {isp_name} — {len(changed_infos)}/{len(cd_infos)} URL değişti")
            degisim += 1

            # parse_pkg=1 olan değişen URL'ler → LLM'e gidecek
            parse_infos = [i for i in changed_infos if i.get("parse_pkg", 1)]

            # parse_pkg=0 URL'ler değiştiyse sadece timestamp güncelle
            diff_only_infos = [i for i in changed_infos if not i.get("parse_pkg", 1)]
            for i in diff_only_infos:
                update_url_last_parsed_ts(i["id"], uuid_ts.get(i["cd_uuid"], 0))

            if not parse_infos:
                # Sadece duyuru/diff-only URL'ler değişti
                save_snapshot(isp_id)
                logging.info(f"[✓] {isp_name} — diff-only URL değişimi kaydedildi")
                kontrol += 1
                continue

            # LLM ile parse et
            try:
                if len(parse_infos) > _URL_BATCH_THRESHOLD:
                    # Çok URL'li ISS → her URL ayrı LLM çağrısı (paralel, 3 worker)
                    logging.info(f"  {isp_name}: {len(parse_infos)} URL → per-URL mod")
                    packages = _parse_per_url(bridge, parse_infos, isp_name)
                    llm_cagri += len(parse_infos)
                else:
                    fetch_pairs = [(i["cd_uuid"], i["url"]) for i in parse_infos]
                    snapshot_text, _ = bridge.get_multi_snapshot_with_urls(fetch_pairs)
                    if not snapshot_text:
                        logging.warning(f"[!] {isp_name} — CD snapshot boş, atlanıyor")
                        hata += 1
                        continue
                    packages = parse_with_llm(snapshot_text, isp_name)
                    # Batch modda kaynak URL: tüm URL'leri virgülle birleştir
                    batch_url = ", ".join(i["url"] for i in parse_infos)
                    for p in packages:
                        if not p.get("kaynak_url"):
                            p["kaynak_url"] = batch_url
                    llm_cagri += 1

                if not packages:
                    logging.warning(f"[!] {isp_name} — LLM 0 paket döndü")

                parse_json = json.dumps({"paketler": packages}, ensure_ascii=False)
                save_snapshot(isp_id, parse_json=parse_json, llm_cagrildi=1)

                process(isp_id, isp_name, packages)

                # Başarılıysa parse_pkg=1 URL'lerin timestamp'ini güncelle
                for i in parse_infos:
                    update_url_last_parsed_ts(i["id"], uuid_ts.get(i["cd_uuid"], 0))

                logging.info(f"[✓] {isp_name} — {len(packages)} paket (LLM, {len(parse_infos)} URL)")

            except Exception as e:
                logging.error(f"[PARSE HATA] {isp_name}: {e}")
                save_snapshot(isp_id, hata=str(e))
                hata += 1

            kontrol += 1

        except Exception as e:
            logging.warning(f"[HATA] {isp_name}: {e}")
            save_snapshot(isp_id, hata=str(e))
            hata += 1

    logging.info(
        f"=== Kontrol bitti — {kontrol} kontrol, {degisim} değişim, "
        f"{llm_cagri} LLM çağrısı, {hata} hata ==="
    )
    push_db_to_github()


def main():
    setup_logging()
    logging.info("Rakip analizi başlatıldı.")

    # CD UUID'lerini DB ile senkronize et
    logging.info("CD UUID sync başlıyor...")
    try:
        bridge = get_bridge()
        result = bridge.sync_uuids_to_db()
        logging.info(
            f"CD sync tamamlandı — {len(result['updated'])} eşleşti, "
            f"{len(result['not_found'])} eşleşmedi, {result['migrated']} migrate edildi"
        )
    except Exception as e:
        logging.error(f"CD sync hatası: {e}")

    son_tam_kontrol: datetime | None = None

    while True:
        now = datetime.now()
        tam_kontrol_vakti = (
            son_tam_kontrol is None or
            (now - son_tam_kontrol).total_seconds() >= INTERVAL_DIGER_SAAT * 3600
        )

        try:
            if tam_kontrol_vakti:
                run_once(sadece_rakip=False)
                son_tam_kontrol = datetime.now()
            else:
                run_once(sadece_rakip=True)
        except Exception as e:
            logging.critical(f"Döngü hatası: {e}", exc_info=True)

        logging.info(f"Sonraki kontrol {INTERVAL_RAKIP_DK} dakika sonra...")
        time.sleep(INTERVAL_RAKIP_DK * 60)


if __name__ == "__main__":
    main()
