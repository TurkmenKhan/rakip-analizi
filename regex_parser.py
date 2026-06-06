"""
Selector metninden regex ile paket verisi çıkarır.
LLM kullanmaz — DOM'dan gelen temiz metni doğrudan parse eder.

Girdi: fetch_selector() çıktısı (--- ile ayrılmış kartlar)
Çıktı: parser.py ile aynı format (packages listesi)
"""
import re


# ── Regex kalıpları ────────────────────────────────────────────────────────────

SPEED_RE    = re.compile(r'(\d+)\s*(?:Mbps|Gbps|mbps|gbps)', re.I)
PRICE_RE    = re.compile(r'(?:(?<!\w)(\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:TL|₺)|(?:TL|₺)\s*(\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?))', re.I)
SPEED_KADAR = re.compile(r"(\d+)\s*Mbps'?e?\s*[Kk]adar", re.I)  # "200 Mbps'e Kadar"
CONTRACT_RE = re.compile(
    r'(\d+)\s*Ay\s*(?:Taahhüt\w*|Sözünüze|sabit\s*fiyat\s*garantili)',
    re.I
)
FIRST_RE    = re.compile(r'(?:İlk|ilk)\s*(\d+)\s*Ay', re.I)
FIBER_RE    = re.compile(r'\bfiber\b', re.I)
VDSL_RE     = re.compile(r'\bvdsl\b', re.I)
ADSL_RE     = re.compile(r'\badsl\b', re.I)
GBPS_RE     = re.compile(r'(\d+)\s*Gbps', re.I)

# 5G / kota paketleri (Vodafone RedBox gibi — Mbps yok, GB kota var)
KOTA_GB_RE  = re.compile(r'(\d+)\s*GB\b(?!\s*[pP]s)', re.I)   # "300GB", "500 GB" (Gbps değil)
KOTA_TB_RE  = re.compile(r'(\d+)\s*TB\b', re.I)                # "1TB"
KOTA_SIN_RE = re.compile(r'\bsınırsız\b', re.I)                 # "Sınırsız"
G5_RE       = re.compile(r'\b5[Gg]\b|\bRedBox\b', re.I)

# Fiyat olmayan satırlar (indirim, cayma bedeli vs.)
PRICE_NOISE = re.compile(r'indirim|cayma|bedel|kampanya(?!\s*fiyat)|bonus|hediye|avantaj', re.I)

# Paket adı olmayan satırları filtrele (navigasyon, promo, vergi, başlık vs.)
_NAME_SKIP = re.compile(
    # UI / navigasyon elemanları
    r'\bFiyat\b|\bPaket\s+Hızı\b|\bPaket\s+İçeriği\b|\bİçerik\b|'
    r'\bDetayl[ıi]\b|\bDetaylar?\b|\bAbone\s+Ol\b|\bİncele\b|\bSipariş\b|'
    r'\bTaahhütsüz\b|\bTaahhütlü\b|\bLimitsiz\b|\bSınırsız\b|'
    r'\bAy\s+(?:Sabit|Taahhüt)\b|'
    # * veya + ile başlayan promosyon/navigasyon satırları
    r'^\s*[*+]\s*|'
    # Vergi / yasal bilgi
    r'\bKDV\b|\bÖİV\b|\bvergi\b|'
    # CTA / buton ifadeleri
    r'\bseç\b|\bseçin\b|\bkeşfet\b|\bOku\b|\bDaha\s+Fazla\b|\bHemen\s+Al\b|'
    r'\bBaşvur\b|'
    # Sayfa / bölüm / navigasyon başlıkları
    r'\bİnternet\s+Paketleri\b|\bHakkımızda\b|\bAnasayfa\b|Kurumsal|'
    r'\bİletişim\b|\bİşlemler?\b|\bVeri\s+Merkezi\b|'
    r'\bBireysel\s+Tarife|\bTarifeler?\s*$|\bPaketler?\s*$|'
    r'^Kampanyalar?\s*$|^Öne\s+Çıkan\b|'
    # Sosyal medya / footer / auth metinleri
    r'\bTakip\s+Edin\b|\bhesaplar\w*\s+bizi\b|'
    r'\bGiriş\s+Yap\b|\bÜye\s+Ol\b|\bSıkça\s+Sorulan\b|'
    r'\bKatılım\s+Şartları\b|\bBaşvurusu\b|\bBaşvuru\s+Formu\b|'
    # Uzun promosyon/bilgi cümleleri (abonelik, e-devlet vs. geçen açıklama satırları)
    r'\babonelik\b|\be-devlet\b|'
    # Teknoloji kategori etiketleri (paket adı değil)
    r'^ADSL\s*[&/ve]+\s*VDSL$|^4\.5G\s+Hız|'
    # Tarih / son başvuru bilgisi
    r'\bSon\s+Başvuru\b|\bBaşvuru\s+Tarihi\b|'
    # Slogan / promo cümleleri
    r'\bÖdemeyin\b|\bMobil\s+Uygulama|\byapay\s+zeka\b|'
    # Soru işareti ile biten blog/makale başlıkları
    r'\?\s*$|'
    # Çoklu boşluk → tablo başlık satırı (TARIFE   CİHAZ KİRALAMA)
    r' {3,}|'
    # Açıklama cümleleri (paket adı değil)
    r'\b(?:isteyenlere|isteyen|için\b|olan\b|eden\b|'
    r'olanlar|edenler|sunar|sağlar|verir)\b|'
    r'(?:özel|uygun|hızlı|yüksek)\s+\w+\s+paketi?\b|'
    r'\bpaketi?\s+(?:içeriği|fiyatı|bilgisi)\b',
    re.I | re.MULTILINE
)

# Tablo başlığı / navigasyon içeren sahte kart tespiti
HEADER_NOISE = re.compile(
    r'^(paket\s*hız|fiyat\s*$|hız\s*fiyat|anasayfa|kurumsal|iletişim|hakkımızda|'
    r'online\s*işlem|menüyü|altyapı|abone\s*ol)',
    re.I | re.MULTILINE
)


def _parse_price(raw: str) -> float:
    """
    Türkçe fiyat formatını float'a çevirir.
    1.350 → 1350.0   (nokta = binlik ayırıcı)
    799,90 → 799.9   (virgül = ondalık)
    800    → 800.0
    """
    s = raw.strip()
    # 1.234,56 → virgül ondalık, nokta binlik
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    # 1.234 → nokta binlik (virgül yok)
    elif '.' in s and s.index('.') < len(s) - 3:
        s = s.replace('.', '')
    # 799,90 → virgül ondalık
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


def _extract_prices(card: str) -> list[float]:
    """Karttaki fiyatları çıkarır, gürültülü satırları atlar."""
    prices = []
    for line in card.split('\n'):
        line = line.strip()
        if PRICE_NOISE.search(line):
            continue
        for m in PRICE_RE.finditer(line):
            raw = m.group(1) or m.group(2)  # grup1: sayı TL, grup2: ₺ sayı
            if raw:
                val = _parse_price(raw)
                if val > 0:
                    prices.append(val)
    return prices


def _normalize_card(card: str) -> str:
    """
    Kart metnini normalize eder.
    "900\nTL" → "900 TL"  (fiyat iki satırda geldiğinde birleştir)
    "1\nGbps" → "1 Gbps"
    "16\nMbps'e\nKadar Hız" → "16 Mbps'e Kadar Hız"  (ORİS/ŞOKNET formatı)
    """
    # Önce çok satırlı hız kalıplarını birleştir:
    # "16\nMbps'e\nKadar Hız" veya "16\nMbps'e Kadar Hız"
    card = re.sub(
        r'(\d+)\s*\n\s*(Mbps\'?e?)\s*\n\s*([Kk]adar\b[^\n]*)',
        r'\1 \2 \3', card
    )
    card = re.sub(
        r'(\d+)\s*\n\s*(Mbps\'?e?\s*[Kk]adar\b[^\n]*)',
        r'\1 \2', card
    )

    lines = card.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Sadece rakam olan satırın arkasında TL/₺/Mbps/Gbps var mı?
        if re.match(r'^\d+[\d.,]*$', line) and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if re.match(r'^(TL|₺|Mbps|Gbps)$', nxt, re.I):
                out.append(f"{line} {nxt}")
                i += 2
                continue
        out.append(line)
        i += 1
    return '\n'.join(out)


def _extract_from_card(card: str) -> dict | None:
    """Tek bir kart metninden paket bilgisi çıkarır."""
    card = _normalize_card(card.strip())
    if not card or len(card) < 15:
        return None

    # Hız — Gbps, "X Mbps'e Kadar" de destekle
    gbps = GBPS_RE.search(card)
    speed_kadar = SPEED_KADAR.search(card)
    speed_m = SPEED_RE.search(card)
    is_5g = False
    if gbps:
        hiz = int(gbps.group(1)) * 1000
    elif speed_kadar:
        hiz = int(speed_kadar.group(1))
    elif speed_m:
        hiz = int(speed_m.group(1))
    else:
        # Mbps yok — 5G / kota paketi mi? (RedBox, 300GB, 1TB, Sınırsız gibi)
        if G5_RE.search(card) or KOTA_GB_RE.search(card) or KOTA_TB_RE.search(card) or KOTA_SIN_RE.search(card):
            hiz = None   # hız_mbps = None, teknoloji = 5g
            is_5g = True
        else:
            return None

    # Fiyatlar
    prices = _extract_prices(card)
    if not prices:
        return None
    # 50₺ altı değerler gerçek paket fiyatı değil (tablo artefaktı)
    prices = [p for p in prices if p >= 50]
    if not prices:
        return None

    # İlk dönem / sonraki dönem
    first_m = FIRST_RE.search(card)
    # "X Ay Fiyat Garantisi" de ilk dönem sayılır (ŞOKNET formatı)
    garanti_m = re.search(r'(\d+)\s*Ay\s+Fiyat\s+Garantisi', card, re.I)
    ilk_donem_ay = int(first_m.group(1)) if first_m else (int(garanti_m.group(1)) if garanti_m else None)

    if len(prices) >= 2 and ilk_donem_ay:
        fiyat_ilk     = min(prices[0], prices[1])
        fiyat_sonraki = max(prices[0], prices[1])
        fiyat_sabit   = False
    elif len(prices) >= 2 and not ilk_donem_ay:
        # İki fiyat var ama dönem yok → üzeri fiyat / indirimli fiyat (ŞOKNET gibi)
        # Gerçek fiyat en düşük olanıdır
        fiyat_ilk     = min(prices)
        fiyat_sonraki = None
        fiyat_sabit   = True
        ilk_donem_ay  = None
    else:
        fiyat_ilk     = prices[0]
        fiyat_sonraki = None
        fiyat_sabit   = True
        ilk_donem_ay  = None

    # Taahhüt
    contract_m  = CONTRACT_RE.search(card)
    sozlesme    = int(contract_m.group(1)) if contract_m else 0

    # Teknoloji
    if is_5g or G5_RE.search(card):
        teknoloji = '5g'
    elif FIBER_RE.search(card) or (hiz is not None and hiz >= 100):
        teknoloji = 'fiber'
    elif VDSL_RE.search(card):
        teknoloji = 'vdsl'
    elif ADSL_RE.search(card):
        teknoloji = 'adsl'
    else:
        teknoloji = 'belirsiz'

    # Paket adı çıkarma
    lines = [l.strip() for l in card.split('\n') if l.strip() and len(l.strip()) > 3]
    name  = ''

    if is_5g:
        # 5G/kota paketleri: "RedBox 300GB", "5G RedBox Sınırsız" gibi satırı bul
        for line in lines:
            if (G5_RE.search(line) or KOTA_GB_RE.search(line) or
                    KOTA_TB_RE.search(line) or KOTA_SIN_RE.search(line)):
                # Fiyat içermeyen, makul uzunlukta, tire ile başlamayan, promo olmayan satır
                if (not PRICE_RE.search(line) and len(line) <= 60
                        and not line.startswith('-') and not _NAME_SKIP.search(line)):
                    name = line
                    break
    else:
        # Standart: hız satırından önce gelen anlamlı satır
        # CD snapshot'larında paket adı hızdan daha uzak olabilir → max 15 satır geriye bak
        for i, line in enumerate(lines):
            if SPEED_RE.search(line) or GBPS_RE.search(line):
                for j in range(i - 1, max(i - 15, -1), -1):
                    cand = lines[j]
                    if len(cand) > 60:
                        continue
                    if not PRICE_RE.search(cand) and not re.match(r'^\d', cand) and len(cand) > 5:
                        if '\t' in cand or _NAME_SKIP.search(cand):
                            continue
                        name = cand
                        break
                break


    # Modem
    cl = card.lower()
    if 'modem' in cl:
        if any(k in cl for k in ('ücretsiz', 'bedava', 'dahil', 'hediye')):
            modem = 'ucretsiz'
        elif any(k in cl for k in ('kiralik', 'kiralık')):
            modem = 'kiralik'
        else:
            modem = 'belirsiz'
    else:
        modem = 'belirsiz'

    return {
        'paket_adi':            name or None,
        'hiz_mbps':             hiz,
        'hiz_yukleme_mbps':     None,
        'teknoloji':            teknoloji,
        'fiyat_ilk_donem':      fiyat_ilk,
        'fiyat_sonraki_donem':  fiyat_sonraki,
        'ilk_donem_ay':         ilk_donem_ay,
        'fiyat_sabit_mi':       fiyat_sabit,
        'sozlesme_suresi_ay':   sozlesme,
        'taahhut_var':          sozlesme > 0,
        'modem':                modem,
        'modem_ucreti_aylik':   0,
        'sadece_yeni_musteri':  True,
        'kurulum_ucreti':       0,
        'one_cikan_ifadeler':   [],
        'ek_paketler':          [],
        'bolge_kisiti':         None,
        'kampanya_bitis':       None,
        'ham_metin':            card[:300],
    }


def _extract_table_packages(card: str) -> list[dict]:
    """
    Tek blokta çok sayıda hız+fiyat satırı olan tablo formatı için.
    Örn: Kablonet internet-tarifeler — her satır ayrı bir paket.

    Satır formatı: "16 Mbps'e kadar\t5 Mbps\t5 Mbps\t960,00 TL/Ay"
    """
    # "X Mbps'e kadar(Eve Kadar Fiber\nGPON)" gibi sarılmış satırları birleştir
    card = re.sub(r'\([^\n]*\n[^\n]*\)', ' ', card)

    # Tablo başlık bağlamını yakala (ör: "Kablo İnternet (DOCSIS)", "Eve Kadar Fiber")
    _TABLO_BASLIK_RE = re.compile(
        r'(Kablo\s+İnternet.*?DOCSIS|Eve\s+Kadar\s+Fiber|FTTH|GPON|DSL.*?Fiber|Fiber\s+Sınırsız)',
        re.I
    )
    section_prefix = ''
    for ln in card.split('\n'):
        m = _TABLO_BASLIK_RE.search(ln.strip())
        if m and not PRICE_RE.search(ln) and not SPEED_KADAR.search(ln):
            raw = m.group(0).strip()
            # "Kablo İnternet (DOCSIS)" → "Kablo İnternet"
            section_prefix = re.sub(r'\s*\(.*?\)', '', raw).strip()
            break

    packages = []
    for line in card.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Satırda hem hız hem fiyat olmak zorunda
        speed_m = SPEED_KADAR.search(line) or GBPS_RE.search(line) or SPEED_RE.search(line)
        if not speed_m:
            continue
        if PRICE_NOISE.search(line):
            continue
        price_matches = list(PRICE_RE.finditer(line))
        if not price_matches:
            continue

        # Hız — Gbps önce, sonra "X Mbps'e Kadar", sonra sade Mbps
        if GBPS_RE.search(line):
            hiz = int(GBPS_RE.search(line).group(1)) * 1000
        elif SPEED_KADAR.search(line):
            hiz = int(SPEED_KADAR.search(line).group(1))
        else:
            hiz = int(SPEED_RE.search(line).group(1))

        # Fiyat — tab-ayrımlı tablolarda son eşleşme asıl fiyat
        raw = price_matches[-1].group(1) or price_matches[-1].group(2)
        if not raw:
            continue
        fiyat = _parse_price(raw)
        if fiyat <= 0:
            continue

        # Paket adı: "Kablo İnternet 16 Mbps" veya "100 Mbps İnternet"
        hiz_str = f"{hiz:,} Mbps" if hiz < 1000 else f"{hiz//1000} Gbps"
        if section_prefix:
            paket_adi = f"{section_prefix} {hiz_str}"
        else:
            paket_adi = f"İnternet {hiz_str}"

        packages.append({
            'paket_adi':            paket_adi,
            'hiz_mbps':             hiz,
            'hiz_yukleme_mbps':     None,
            'teknoloji':            'fiber' if hiz >= 100 else 'belirsiz',
            'fiyat_ilk_donem':      fiyat,
            'fiyat_sonraki_donem':  None,
            'ilk_donem_ay':         None,
            'fiyat_sabit_mi':       True,
            'sozlesme_suresi_ay':   0,
            'taahhut_var':          False,
            'modem':                'belirsiz',
            'modem_ucreti_aylik':   0,
            'sadece_yeni_musteri':  True,
            'kurulum_ucreti':       0,
            'one_cikan_ifadeler':   [],
            'ek_paketler':          [],
            'bolge_kisiti':         None,
            'kampanya_bitis':       None,
            'ham_metin':            line[:300],
        })
    return packages


def _split_into_cards(text: str) -> list[str]:
    """
    Metni paket kartlarına böler.
    Önce --- separator'ını dener (Playwright/selector çıktısı).
    --- yoksa CD snapshot formatı için "Abone Ol" / "Sipariş Ver" / çoklu boş satır kullanır.
    """
    if '---' in text:
        return text.split('---')

    # CD snapshot formatı: kart sonu butonlarını yakala
    # Satır başı/sonu dışında da (Tarife Detayları Hemen Başvur Hemen Başvur) gelebilir
    card_end = re.compile(
        r'\n[^\n]*\b(?:Abone\s+Ol|Sipariş\s+Ver|SATIN\s+AL|Satın\s+Al'
        r'|Hemen\s+Başvur|Tarife\s+Detaylar[ıi])\b[^\n]*\n',
        re.I
    )
    parts = card_end.split(text)
    if len(parts) > 1:
        return parts

    # "İncele" kart bitişi (daha dikkatli — kısa satırda olmalı)
    card_end2 = re.compile(r'\n\s*İncele\s*\n', re.I)
    parts = card_end2.split(text)
    if len(parts) > 1:
        return parts

    # Son çare: iki+ ardışık boş satır
    return re.split(r'\n{3,}', text)


def parse_packages_regex(selector_text: str) -> list[dict]:
    """
    Selector veya CD snapshot metninden tüm paketleri çıkarır.
    --- ile ayrılmış kartları işler; CD formatı için otomatik bölme yapar.
    """
    # URL başlıklarını temizle (=== https://... ===)
    text = re.sub(r'={3,}[^\n]+={3,}\n?', '', selector_text)

    cards    = _split_into_cards(text)
    packages = []
    seen     = set()

    for card in cards:
        # Farklı unique hız sayısını ölç
        unique_speeds = set(int(m.group(1)) for m in SPEED_KADAR.finditer(card))
        unique_speeds |= set(int(m.group(1)) for m in GBPS_RE.finditer(card))

        if len(unique_speeds) >= 4:
            # Tablo modu: Kablonet tarife sayfası gibi çok satırlı tablo
            for pkg in _extract_table_packages(card):
                key = (pkg['hiz_mbps'], pkg['fiyat_ilk_donem'], pkg['sozlesme_suresi_ay'])
                if key not in seen:
                    seen.add(key)
                    packages.append(pkg)
        else:
            pkg = _extract_from_card(card)
            if not pkg:
                continue
            # hız=None (5G/kota) → paket adı + fiyat ile deduplikasyon
            # hız varsa → hız + fiyat + sözleşme + paket adı
            if pkg['hiz_mbps'] is None:
                key = (None, pkg['fiyat_ilk_donem'], pkg['sozlesme_suresi_ay'], pkg.get('paket_adi'))
            else:
                key = (pkg['hiz_mbps'], pkg['fiyat_ilk_donem'], pkg['sozlesme_suresi_ay'], pkg.get('paket_adi'))
            if key in seen:
                continue
            seen.add(key)
            packages.append(pkg)

    return packages


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys, json
    sys.stdout.reconfigure(encoding='utf-8')

    # TT kart örneği
    sample = """
Fiber Hız Evde Kampanyası
1000 Mbps
Fiber İnternet
Limitsiz
Türk Telekom'a Geçenlere 1100TL indirim
Ücretsiz Kurulum
Modem ücreti dahil değildir
18 Ay Taahhütlü
900 TL
İlk 6 Ay
1.350 TL
Son 12 Ay
---
Online'a Özel Efsane İndirim Kampanyası
500 Mbps
Fiber İnternet
Limitsiz
18 Ay Taahhütlü
575 TL
---
Fiberde 1000 Mbps Mega Fırsat
1000 Mbps
12 Ay Taahhüt
Limitsiz
800 TL/Ay
"""
    pkgs = parse_packages_regex(sample)
    print(f'{len(pkgs)} paket:')
    for p in pkgs:
        print(f"  {p['paket_adi']} | {p['hiz_mbps']}Mbps | {p['fiyat_ilk_donem']}TL | {p['sozlesme_suresi_ay']}ay")
