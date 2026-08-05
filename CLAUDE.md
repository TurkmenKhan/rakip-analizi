# Rakip Analizi — Proje Bağlamı

## TL;DR (sonraki Claude session için)
- **Platform**: CachyOS Linux, kullanıcı `khan`, ana repo `/home/khan/rakip-analizi` (symlink → `~/Masaüstü/Rakip Analizi v2/repo`).
- **Ne yapıyor**: Türkiye ISP rakip analiz sistemi. 128+ ISS'yi izler, fiyat/paket değişimlerini tespit eder, Streamlit dashboard'da gösterir.
- **Nasıl ayakta durur**: `systemctl --user status rakip-*` — 3 unit (dashboard, main, backup timer). Docker Compose'da CD + Playwright ayrı çalışıyor (`/home/khan/docker/changedetection/`).
- **Şu anki durum (2026-08-05)**: LLM parse **AÇIK** — DeepSeek API kullanılıyor (`deepseek-chat`, ~2sn/parse). CD Telegram bildirimi de çalışıyor. Paket tablosu her turda güncelleniyor.
- **Detay operasyon**: [OPERATIONS.md](OPERATIONS.md).

## Mimari — ÖNEMLİ
**TÜM ISS'LER changedetection.io (CD) üzerinden beslenir — HİÇBİR ISS İÇİN DOĞRUDAN SİTEYE GİDİLMEZ**
- **CD** (`http://localhost:5000`, Docker) = Layer 1: scraping + değişim tespiti + Telegram bildirimi (Apprise `tgram://…`)
- **`changedetection_bridge.py`** → CD API köprüsü, snapshot çeker
- **`main.py`** → 30dk (rakip) / 2sa (tüm ISS) scheduler, CD'de değişen watch'ları yakalar, LLM'e gönderir, DB'ye yazar
- **`llm_parser.py`** → DeepSeek (`api.deepseek.com/v1/chat/completions`, `deepseek-chat` = v4-flash, OpenAI-uyumlu)
- **`regex_parser.py`** → tanımlı ama `main.py`'de çağrılmıyor (kullanılmıyor)
- **`alerts.py`** → paket diff → `alerts` tablosu (dashboard için; Telegram DEĞİL — o CD tarafında)
- **`push_db.py`** → her tur sonu DB'yi GitHub'a push eder (**şu an DISABLE_DB_PUSH=1**, PAT yok)
- **`db.py`** → SQLite WAL, `data/rakip_analizi.db`
- **`dashboard.py`** → Streamlit, light theme, Altair scatter, `localhost:8501`

## CD Entegrasyonu
- API Key: `.env`'de `CD_API_KEY=9f27a45aed03c826410dc5be255db03b` (yedekteki `changedetection.json`'dan geldi — CLAUDE.md'nin eski versiyonundaki `94953…` key farklı, o KULLANILMIYOR).
- Telegram config: `tgram://8814202038:.../-1003936786052` — Apprise + `htmlcolor` format + Türkçe title (`İçerik Değişti`). "🔴 header + ➕/➖ diff + 🔗 URL" formatı bu kombinasyonun çıktısıdır (extra script yok).
- `isp_urls.cd_uuid` → her URL'nin CD'deki UUID'si.
- `isp_urls.parse_pkg` → 0 = değişim tespiti var ama paket parse edilmez (duyuru sayfaları).
- `sync_uuids_to_db()` → CD URL'lerini `isp_urls` tablosuyla eşler (main.py başlarken 1 kez).

## ISS Kategorileri
- **rakip** (7): TÜRK TELEKOM(~88 pkg), TURKCELL SUPERONLİNE(12), VODAFONE(6), GİBİRNET(10), TURKSAT KABLONET(10), NETSPEED(izlenemiyor), TURKNET(selector yok)
- **diger** (~121): Küçük bölgesel ISS'ler.
- Toplam 142 ISS DB'de, 134 aktif watch CD'de.

## Önemli Teknik Detaylar
- Dedup key: `isp_id|hiz_mbps|teknoloji|sozlesme_suresi_ay|fiyat_ilk_donem|slug`
- 5G paketler: `hiz_mbps=None, teknoloji='5g'` — Karşılaştırma'da "5G / Kota" kademesi
- `get_stats()` sidebar `aktif_katlar` filtresine göre çalışır
- `load_alerts()` isp_url için `isp_urls` tablosunu kullanır (`isps.url` DEĞİL)
- Auto-refresh: 60 saniyede bir JavaScript reload
- Kablonet: tablo format, paket adı otomatik üretilir ("İnternet 100 Mbps")
- `parse_pkg=0` URL'ler: duyuru/kampanya sayfaları — hash değişimi kaydedilir ama paket çıkarılmaz

## Bilinen Sorunlar
- NETSPEED: digit-split anti-bot, CD de çekemiyor
- TURKNET: CD'de yok
- `icerik_degisim` alertler: TT selector geniş, navigation menu diff gürültülü
- **LLM sağlayıcı geçişi (2026-08-05)**: llm.gen.tr'de `gemini-2.5-flash` chat çağrısı hep 400 "Unknown model" dönüyordu (hesap seviyesinde model whitelisti). DeepSeek'e geçildi (`api.deepseek.com/v1`, `deepseek-chat`) — OpenAI-uyumlu, `llm_parser.py` kod değişikliği gerektirmedi, sadece `.env`.
- **GitHub PAT yok**: `~/.git-credentials` boş. `push_db.py` GitHub yedeği yapmıyor. PAT verildiğinde `~/.git-credentials`'a `https://TurkmenKhan:<PAT>@github.com` yazıp `.env`'de `DISABLE_DB_PUSH=0` yap.

## Sonraki Claude için: değişiklik yaparken dikkat
- **Path**: kodda ve unit dosyalarında `/home/khan/rakip-analizi` kullan (symlink). Türkçe karakter/boşluk sorun çıkarıyor systemd'de.
- **Servis kontrolü**: `systemctl --user restart rakip-main` ile main.py yeniden başlar (30dk sonraki turu beklemez, hemen `run_once` çalışır).
- **`.env` değişikliği**: servis EnvironmentFile ile okuyor — değişiklikten sonra `systemctl --user restart` şart.
- **Log'lar**: `/home/khan/rakip-analizi/logs/` altında (main.service.log, dashboard.log, backup-cd.log + main.py'nin kendi günlük log dosyaları `YYYY-MM-DD.log`).
- **CD yedeği**: `~/rakip-analizi/backups/cd/` altında günlük tar.zst, 14 gün retention.
