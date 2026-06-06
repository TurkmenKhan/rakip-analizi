# Rakip Analizi — Proje Bağlamı

## Ne yapıyor?
Türkiye ISP (internet servis sağlayıcı) rakip analiz sistemi. 128 ISS'yi izler, fiyat/paket değişimlerini tespit eder, Streamlit dashboard'da gösterir.

## Çalıştırma
- **main.py**: Arka planda çalışıyor (30dk rakip, 2sa tüm ISS)
- **Dashboard**: `streamlit run dashboard.py` → `localhost:8501`
- **GitHub**: `https://github.com/TurkmenKhan/rakip-analizi.git` (Streamlit Cloud'a bağlı)

## Mimari — ÖNEMLİ
**TÜM ISS'LER changedetection.io (CD) üzerinden beslenir — HİÇBİR ISS İÇİN DOĞRUDAN SİTEYE GİDİLMEZ**
- CD (`http://localhost:5000`) = Layer 1: scraping + değişim tespiti
- `changedetection_bridge.py` → CD API köprüsü, snapshot çeker
- `regex_parser.py` → hız+fiyat+sözleşme regex (LLM fallback sadece küçük "diger" ISS, CD snapshot'ı parse eder)
- `alerts.py` → paket diff → alerts tablosu
- `db.py` → SQLite WAL mode
- `dashboard.py` → Streamlit light theme, Altair scatter, custom HTML bar charts
- `scraper.py` / Playwright → KULLANILMIYOR (CD tüm sayfaları kendisi çeker)

## CD Entegrasyonu
- API Key: `94953b40b50ba1361b9ae457b52bfb93`
- `isp_urls.cd_uuid` → her URL'nin CD'deki UUID'si
- `isp_urls.parse_pkg` → 0 = değişim tespiti var ama paket parse edilmez (duyuru sayfaları)
- `sync_uuids_to_db()` → CD URL'lerini isp_urls tablosuyla eşler
- Paralel fetch: ThreadPoolExecutor (15 worker) ile tüm URL'ler aynı anda çekilir

## ISS Kategorileri
- **rakip** (7): TÜRK TELEKOM(~88 pkg), TURKCELL SUPERONLİNE(12), VODAFONE(6), GİBİRNET(10), TURKSAT KABLONET(10), NETSPEED(izlenemiyor), TURKNET(selector yok)
- **diger** (~121): Küçük bölgesel ISS'ler, LLM ile parse edilir

## Önemli Teknik Detaylar
- Dedup key: `isp_id|hiz_mbps|teknoloji|sozlesme_suresi_ay|fiyat_ilk_donem|slug`
- 5G paketler: `hiz_mbps=None, teknoloji='5g'` — Karşılaştırma'da "5G / Kota" kademesi
- `get_stats()` sidebar `aktif_katlar` filtresine göre çalışır
- `load_alerts()` isp_url için `isp_urls` tablosunu kullanır (isps.url değil)
- Auto-refresh: 60 saniyede bir JavaScript reload
- Kablonet: tablo format, paket adı otomatik üretilir ("İnternet 100 Mbps")
- parse_pkg=0 URL'ler: duyuru/kampanya sayfaları — hash değişimi kaydedilir ama paket çıkarılmaz

## Bilinen Sorunlar
- NETSPEED: digit-split anti-bot, CD de çekemiyor
- TURKNET: CD'de yok
- `icerik_degisim` alertler: TT selector geniş, navigation menu diff gürültülü
