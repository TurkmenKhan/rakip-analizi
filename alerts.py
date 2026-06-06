"""
Yeni snapshot ile mevcut packages tablosunu karşılaştırır,
değişimleri package_history ve alerts tablolarına yazar.
"""
import json
from db import (get_conn, upsert_package, mark_packages_inactive,
                add_alert, add_package_history)

IZLENEN_ALANLAR = [
    # Sadece LLM'in güvenilir şekilde çıkardığı sayısal/boolean alanlar.
    # one_cikan_ifadeler ve ek_paketler kaldırıldı — LLM bunları her çalıştırmada
    # farklı şekilde ifade edebilir → sahte alarm üretir.
    # İçerik değişimleri artık selector diff (icerik_degisim) ile yakalanıyor.
    ("fiyat_ilk_donem",     "Fiyat (ilk dönem)"),
    ("fiyat_sonraki_donem", "Fiyat (sonraki dönem)"),
    ("ilk_donem_ay",        "İlk dönem süresi (ay)"),
    ("modem",               "Modem"),
    ("modem_ucreti_aylik",  "Modem ücreti"),
    ("taahhut_var",         "Taahhüt"),
    ("sozlesme_suresi_ay",  "Sözleşme süresi"),
    ("sadece_yeni_musteri", "Sadece yeni müşteri"),
    ("kampanya_bitis",      "Kampanya bitiş"),
]


def process(isp_id: int, isp_name: str, new_packages: list[dict], partial: bool = False):
    """partial=True ise bazı URL'ler başarısız olmuştur; mevcut paketleri silme."""
    if not new_packages:
        return

    conn = get_conn()
    existing_rows = conn.execute(
        "SELECT * FROM packages WHERE isp_id=? AND aktif=1", (isp_id,)
    ).fetchall()
    conn.close()

    existing_map = {row["paket_key"]: dict(row) for row in existing_rows}

    # Oscillasyon koruması: parse edilen paket sayısı mevcut aktif sayının
    # %60'ının altına düştüyse, parse güvenilir değil — paket silme yapma.
    if not partial and existing_map and len(new_packages) < len(existing_map) * 0.60:
        partial = True

    new_keys = []

    for pkg in new_packages:
        paket_key, old_row = upsert_package(isp_id, pkg)
        new_keys.append(paket_key)

        sozlesme = pkg.get('sozlesme_suresi_ay', 0) or 0
        sozlesme_str = "Taahhütsüz" if sozlesme == 0 else f"{sozlesme}ay"
        label = f"{isp_name} | {pkg.get('hiz_mbps')}Mbps {pkg.get('teknoloji', '')} {sozlesme_str}"

        if old_row is None:
            # Fiyatsız ve 5G olmayan paket → parse güvenilmez, alert üretme
            fiyat = pkg.get('fiyat_ilk_donem')
            if fiyat is None and pkg.get('teknoloji') != '5g':
                continue
            fiyat_str = f"{fiyat:,.0f}₺" if fiyat is not None else "fiyat bilinmiyor"
            add_alert(
                isp_id, "yeni_paket",
                f"YENİ PAKET: {label} — {fiyat_str}",
                paket_key
            )
            continue

        # Mevcut paket — alan bazlı karşılaştır (sadece sayısal/güvenilir alanlar)
        for alan, alan_label in IZLENEN_ALANLAR:
            eski_raw = old_row.get(alan)
            yeni_raw = pkg.get(alan)

            if str(eski_raw) == str(yeni_raw):
                continue
            eski_str = str(eski_raw)
            yeni_str = str(yeni_raw)

            # Gürültü filtresi: belirsiz → somut değer gerçek değişim sayılmaz
            # (LLM önceden kararsız kalmış, şimdi daha kesin — alarm üretme)
            if eski_str in ("belirsiz", "None", "null", "") and yeni_str not in ("belirsiz", "None", "null", ""):
                add_package_history(isp_id, paket_key, alan, eski_str, yeni_str,
                                    f"{label} | {alan_label}: {eski_str} → {yeni_str} (sessiz güncelleme)")
                continue  # history'e yaz ama alarm üretme

            # Modem için sadece anlamlı değişim: ucretsiz ↔ kiralik/satin_alim
            if alan == "modem":
                anlamsiz = {
                    ("belirsiz", "ucretsiz"), ("ucretsiz", "belirsiz"),
                    ("belirsiz", "kiralik"),  ("kiralik", "belirsiz"),
                    ("None", "ucretsiz"),     ("ucretsiz", "None"),
                }
                if (eski_str, yeni_str) in anlamsiz:
                    add_package_history(isp_id, paket_key, alan, eski_str, yeni_str,
                                        f"{label} | Modem: {eski_str} → {yeni_str} (sessiz)")
                    continue

            add_package_history(isp_id, paket_key, alan, eski_str, yeni_str,
                                f"{label} | {alan_label}: {eski_str} → {yeni_str}")

            # Fiyat değişimlerinde alert oluştur
            if alan == "fiyat_ilk_donem":
                try:
                    delta = float(yeni_raw or 0) - float(eski_raw or 0)
                    tur   = "fiyat_dustu" if delta < 0 else "fiyat_yukseldi"
                    add_alert(isp_id, tur,
                              f"{label}: {eski_raw}₺ → {yeni_raw}₺ ({delta:+.2f}₺)",
                              paket_key)
                except (TypeError, ValueError):
                    pass


    if partial:
        # Bazı URL'ler başarısız — mevcut paketleri silme, yanlış alarm üretme
        return

    # Sayfadan kalkan paketleri işaretle
    removed = set(existing_map.keys()) - set(new_keys)
    for key in removed:
        row   = existing_map[key]
        # Fiyatsız (None) ve 5G olmayan paket kaldırılınca alert üretme — parse artefaktı
        fiyat = row.get('fiyat_ilk_donem')
        if fiyat is None and row.get('teknoloji') != '5g':
            continue
        soz   = row.get('sozlesme_suresi_ay') or 0
        soz_s = "Taahhütsüz" if soz == 0 else f"{soz}ay"
        label = f"{isp_name} | {row.get('hiz_mbps')}Mbps {row.get('teknoloji', '')} {soz_s}"
        fiyat_str = f"{fiyat:,.0f}₺" if fiyat is not None else "fiyat bilinmiyor"
        add_alert(isp_id, "paket_kaldirildi",
                  f"PAKET KALDIRILDI: {label} — son fiyat {fiyat_str}",
                  key)

    mark_packages_inactive(isp_id, new_keys)
