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

from db import (
    get_active_isps, get_isp_url_selectors_with_cd,
    get_last_parsed_ts, update_last_parsed_ts,
    save_snapshot, add_alert, mark_packages_inactive,
)
from llm_parser              import parse_with_llm
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

    kontrol = degisim = llm_cagri = hata = 0

    for isp in isps:
        isp_id   = isp["id"]
        isp_name = isp["name"]

        try:
            url_infos = get_isp_url_selectors_with_cd(isp_id)

            # CD'de UUID'si olan URL'ler
            cd_all   = [(i["cd_uuid"], i["url"]) for i in url_infos if i["cd_uuid"]]
            cd_parse = [(i["cd_uuid"], i["url"]) for i in url_infos if i["cd_uuid"] and i.get("parse_pkg", 1)]

            if not cd_all:
                # CD'de hiç URL'si yok → paketleri pasif yap
                mark_packages_inactive(isp_id, [])
                logging.info(f"[−] {isp_name} — CD'de yok, paketler pasif edildi")
                continue

            # CD'nin last_changed timestamp'ini al (tüm URL'ler arasında en yeni)
            max_last_changed = max(
                int(watches.get(uuid, {}).get("last_changed") or 0)
                for uuid, _ in cd_all
            )

            last_parsed = get_last_parsed_ts(isp_id)

            # ISS'in parse_paketler=0 kontrolü (diff-only mod, ör. TT)
            try:
                parse_paketler = isp["parse_paketler"]
            except (IndexError, KeyError):
                parse_paketler = 1

            if max_last_changed > 0 and max_last_changed <= last_parsed:
                # CD'de değişim yok — atla
                logging.debug(f"[=] {isp_name} — değişim yok")
                kontrol += 1
                continue

            # Değişim var (veya hiç parse edilmemiş)
            logging.info(f"[~] {isp_name} — CD değişimi tespit edildi, işleniyor...")
            degisim += 1

            # parse_paketler=0 → sadece timestamp güncelle, LLM çağırma
            if not parse_paketler:
                update_last_parsed_ts(isp_id, max_last_changed)
                save_snapshot(isp_id)
                logging.info(f"[✓] {isp_name} — diff-only mod (paket parse yok)")
                kontrol += 1
                continue

            # Snapshot'ı CD'den çek (sadece parse_pkg=1 URL'ler)
            fetch_pairs = cd_parse if cd_parse else cd_all
            snapshot_text, _ = bridge.get_multi_snapshot_with_urls(fetch_pairs)

            if not snapshot_text:
                logging.warning(f"[!] {isp_name} — CD snapshot boş, atlanıyor")
                hata += 1
                continue

            # LLM ile parse et
            try:
                packages = parse_with_llm(snapshot_text, isp_name)
                llm_cagri += 1
                if not packages:
                    logging.warning(f"[!] {isp_name} — LLM 0 paket döndü")

                parse_json = json.dumps({"paketler": packages}, ensure_ascii=False)
                save_snapshot(isp_id, parse_json=parse_json, llm_cagrildi=1)

                process(isp_id, isp_name, packages)
                update_last_parsed_ts(isp_id, max_last_changed)

                logging.info(f"[✓] {isp_name} — {len(packages)} paket (LLM)")

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
