"""
LLM ile ISS paket parse eder.
llm.gen.tr OpenAI-uyumlu API — Gemini 2.5 Flash kullanır.

Çıktı: upsert_package() ile uyumlu dict listesi.
"""
import json
import logging
import os
import re
import time

import requests

LLM_URL   = os.environ.get("LLM_API_URL",  "https://llm.gen.tr/v1/chat/completions")
LLM_KEY   = os.environ.get("LLM_API_KEY",  "")
LLM_MODEL = os.environ.get("LLM_MODEL",    "gemini-2.5-flash")

_TIMEOUT    = 90   # saniye
_MAX_CHARS  = 20_000  # max snapshot uzunluğu (LLM'e gönderilecek)

_SYSTEM = """Sen bir Türk ISS (internet servis sağlayıcı) web sayfası analiz asistanısın.
Verilen metin içeriğinden ev interneti paketlerini çıkar.

KURALLAR:
- SADECE geçerli JSON döndür, başka açıklama veya markdown ekleme
- Navigasyon menüsü, footer, cookie uyarısı, sosyal medya linklerini yoksay
- Sadece gerçek ev interneti paketi bilgilerini çıkar (mobil, TV hariç)
- Fiyatlar TL (Türk Lirası) cinsinden, KDV dahil
- Hız Mbps cinsinden tam sayı (1 Gbps = 1000 Mbps)
- Paket bulunamazsa: {"paketler": []}
- fiyat_baslangic = ilk dönem / kampanya / indirimli fiyat
- fiyat_ortalama = taahhüt süresi boyunca aylık ortalama (hesapla, yoksa null)
- fiyat_sonraki = indirim bittikten sonraki normal fiyat
- Taahhütsüz paketlerde taahhut_ay = 0
- Üzeri çizili/eski fiyatı ALMA, geçerli/güncel fiyatı al"""

_USER_TMPL = """ISS adı: {isp_name}

---SAYFA İÇERİĞİ---
{text}
---

Şu JSON formatında döndür (başka hiçbir şey yazma):
{{
  "paketler": [
    {{
      "paket_adi": "paket adı veya null",
      "hiz_mbps": hız sayısı veya null,
      "teknoloji": "fiber|vdsl|adsl|5g|uydu|belirsiz",
      "fiyat_baslangic": ilk dönem fiyatı TL veya null,
      "fiyat_ortalama": ortalama aylık fiyat TL veya null,
      "fiyat_sonraki": taahhüt sonrası normal fiyat TL veya null,
      "taahhut_ay": taahhüt süresi ay sayısı (0=taahhütsüz),
      "modem": "ucretsiz|kiralik|satin_alma|belirsiz",
      "modem_ucreti_aylik": aylık modem ücreti TL veya null,
      "kurulum_ucreti": kurulum ücreti TL (0=ücretsiz, bilinmiyorsa 0),
      "bolge": "bölge adı veya null",
      "kampanya_bitis": "YYYY-MM-DD formatında veya null"
    }}
  ]
}}"""


def parse_with_llm(text: str, isp_name: str = "") -> list[dict]:
    """
    CD snapshot metnini LLM'e gönderir, yapılandırılmış paket listesi döndürür.
    Hata durumunda boş liste döner (exception fırlatmaz).
    """
    if not text or not text.strip():
        return []

    # Uzun snapshot'ları kırp
    snippet = text[:_MAX_CHARS]

    prompt = _USER_TMPL.format(isp_name=isp_name or "bilinmiyor", text=snippet)

    headers = {
        "Authorization": f"Bearer {LLM_KEY}",
        "Content-Type":  "application/json",
    }
    body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens":  16384,
    }

    # 429 için retry (3 deneme, artan bekleme)
    for attempt in range(3):
        try:
            resp = requests.post(LLM_URL, headers=headers, json=body, timeout=_TIMEOUT)
            if resp.status_code == 429:
                wait = (attempt + 1) * 5
                logging.debug(f"[LLM] 429 rate limit ({isp_name}), {wait}sn bekleniyor...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            break
        except Exception as e:
            if attempt == 2:
                logging.warning(f"[LLM] API hatası ({isp_name}): {e}")
                return []
            time.sleep((attempt + 1) * 3)
    else:
        logging.warning(f"[LLM] 429 — tüm denemeler tükendi ({isp_name})")
        return []

    # JSON çıkar (```json ... ``` bloğu olabilir)
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # Kesik JSON kurtarma: "paketler" listesinin geçerli kısmını al
        data = _rescue_truncated_json(raw)
        if data is None:
            logging.warning(f"[LLM] JSON parse hatası ({isp_name}): {e}\nHam: {raw[:300]}")
            return []

    paketler = data.get("paketler", [])
    if not isinstance(paketler, list):
        return []

    return [_map_pkg(p) for p in paketler if isinstance(p, dict)]


def _rescue_truncated_json(raw: str) -> dict | None:
    """
    Kesik JSON'dan geçerli paket listesini kurtarmaya çalışır.
    Son tam nesneden sonrasını keser ve listeyi kapatır.
    """
    # "paketler": [ ... içindeki son tam nesneyi bul
    start = raw.find('"paketler"')
    if start == -1:
        return None
    bracket = raw.find('[', start)
    if bracket == -1:
        return None

    # Son } bulunana kadar kes
    last_brace = raw.rfind('}')
    if last_brace == -1:
        return None

    truncated = raw[bracket:last_brace + 1] + ']}'
    # Wrap with key
    candidate = '{"paketler":' + raw[bracket:last_brace + 1] + ']}'
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Daha agresif: son tam } } bloğunu bul
        try:
            trimmed = raw[:last_brace + 1]
            # Açık braket sayısını dengele
            open_b = trimmed.count('{') - trimmed.count('}')
            trimmed += '}' * open_b + ']}'
            return json.loads('{"paketler":' + raw[bracket:last_brace + 1] + ']}')
        except Exception:
            return None


def _map_pkg(p: dict) -> dict:
    """LLM çıktısını upsert_package() formatına dönüştürür."""
    taahhut = int(p.get("taahhut_ay") or 0)
    fiyat_b = _to_float(p.get("fiyat_baslangic"))
    fiyat_s = _to_float(p.get("fiyat_sonraki"))
    fiyat_o = _to_float(p.get("fiyat_ortalama"))

    return {
        "paket_adi":            p.get("paket_adi") or None,
        "hiz_mbps":             _to_int(p.get("hiz_mbps")),
        "hiz_yukleme_mbps":     None,
        "teknoloji":            _norm_tek(p.get("teknoloji")),
        "fiyat_ilk_donem":      fiyat_b,
        "fiyat_ortalama":       fiyat_o,
        "fiyat_sonraki_donem":  fiyat_s,
        "ilk_donem_ay":         taahhut if (fiyat_b and fiyat_s and fiyat_b != fiyat_s) else None,
        "fiyat_sabit_mi":       fiyat_s is None or fiyat_b == fiyat_s,
        "sozlesme_suresi_ay":   taahhut,
        "taahhut_var":          taahhut > 0,
        "modem":                _norm_modem(p.get("modem")),
        "modem_ucreti_aylik":   _to_float(p.get("modem_ucreti_aylik")) or 0,
        "sadece_yeni_musteri":  False,
        "kurulum_ucreti":       _to_float(p.get("kurulum_ucreti")) or 0,
        "one_cikan_ifadeler":   [],
        "ek_paketler":          [],
        "bolge_kisiti":         p.get("bolge") or None,
        "kampanya_bitis":       p.get("kampanya_bitis") or None,
        "ham_metin":            None,
    }


def _to_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _norm_tek(v: str | None) -> str:
    if not v:
        return "belirsiz"
    v = v.lower().strip()
    mapping = {
        "fiber": "fiber", "vdsl": "vdsl", "adsl": "adsl",
        "5g": "5g", "uydu": "uydu",
    }
    return mapping.get(v, "belirsiz")


def _norm_modem(v: str | None) -> str:
    if not v:
        return "belirsiz"
    v = v.lower().strip()
    if v in ("ucretsiz", "ücretsiz", "free", "dahil"):
        return "ucretsiz"
    if v in ("kiralik", "kiralık", "rental"):
        return "kiralik"
    if v in ("satin_alma", "satın_alma", "purchase"):
        return "satin_alma"
    return "belirsiz"
