import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from db import get_conn
try:
    import altair as alt
    _HAS_ALTAIR = True
except ImportError:
    _HAS_ALTAIR = False

st.set_page_config(
    page_title="ISP Analytics",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Otomatik yenileme — 60 saniyede bir ────────────────────────────────────
st.markdown(
    '<script>setTimeout(function(){window.location.reload();}, 60000);</script>',
    unsafe_allow_html=True,
)

# ── Font + global CSS ────────────────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600'
    '&family=JetBrains+Mono:wght@400;500;700&family=Geist:wght@400;600;700;800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown("""
<style>
/* ─── GLOBAL ─────────────────────────────────────────────────────── */
html, body, .stApp {
  background: #f8fafc !important;
  font-family: 'Inter', sans-serif !important;
  color: #0f172a !important;
}
[data-testid="stAppViewContainer"] { background: #f8fafc !important; }
[data-testid="stHeader"] { background: transparent !important; border-bottom: none !important; }
[data-testid="stToolbar"] { display: none; }
p, span, li { color: #0f172a; font-family: 'Inter', sans-serif; font-size: 14px; }

/* ─── SIDEBAR ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #f1f5f9 !important;
  border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebarContent"] { padding-top: 0 !important; }

/* nav radio */
[data-testid="stSidebar"] .stRadio > label { display: none; }
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio label {
  background: transparent !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 10px 16px !important;
  color: #64748b !important;
  font-size: 13px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
  letter-spacing: 0.02em !important;
  transition: background 0.15s, color 0.15s !important;
  width: 100% !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: #e2e8f0 !important;
  color: #0f172a !important;
}
[data-testid="stSidebar"] hr { border-color: #e2e8f0 !important; margin: 8px 0 !important; }
[data-testid="stSidebar"] .stCaption { color: #94a3b8 !important; font-size: 12px !important; }
[data-testid="stSidebar"] p { color: #94a3b8 !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] { background: rgba(8,145,178,0.1) !important; color: #0891b2 !important; font-size: 12px !important; }
[data-testid="stSidebar"] .stButton button {
  background: transparent !important;
  border: 1px solid #e2e8f0 !important;
  color: #64748b !important;
  font-size: 13px !important;
  border-radius: 8px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
  transition: all 0.2s !important;
}
[data-testid="stSidebar"] .stButton button:hover {
  border-color: #0891b2 !important;
  color: #0891b2 !important;
}

/* ─── HEADINGS ────────────────────────────────────────────────────── */
h1, h2, h3, h4 { font-family: 'Geist', sans-serif !important; color: #0f172a !important; letter-spacing: -0.01em !important; }

/* ─── INPUTS ──────────────────────────────────────────────────────── */
input, textarea {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  color: #0f172a !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
  border-radius: 8px !important;
}
input:focus { border-color: #0891b2 !important; box-shadow: 0 0 0 2px rgba(8,145,178,0.12) !important; }
[data-baseweb="select"] > div { background: #ffffff !important; border-color: #e2e8f0 !important; color: #0f172a !important; border-radius: 8px !important; }
[data-baseweb="popover"] { background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important; }
[data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="option"] { color: #374151 !important; background: transparent !important; font-size: 14px !important; }
[data-baseweb="option"]:hover { background: #f1f5f9 !important; color: #0f172a !important; }
[data-baseweb="tag"] { background: rgba(8,145,178,0.1) !important; color: #0891b2 !important; font-size: 12px !important; border-radius: 100px !important; }

/* ─── EXPANDER ────────────────────────────────────────────────────── */
[data-testid="stExpander"] { background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
[data-testid="stExpander"] summary { color: #374151 !important; font-size: 14px !important; font-weight: 600 !important; }

/* ─── DATAFRAMES ──────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 8px !important; overflow: hidden; border: 1px solid #e2e8f0 !important; }
[data-testid="stDataFrame"] iframe { border-radius: 8px !important; }

/* ─── DIVIDERS ────────────────────────────────────────────────────── */
hr { border-color: #e2e8f0 !important; }

/* ─── CAPTION ─────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] { color: #94a3b8 !important; font-size: 12px !important; }

/* ─── CHECKBOX ────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label { color: #374151 !important; font-size: 14px !important; }

/* ─── NUMBER INPUT ────────────────────────────────────────────────── */
[data-testid="stNumberInput"] input { background: #ffffff !important; border-color: #e2e8f0 !important; }
[data-testid="stNumberInput"] button { background: #ffffff !important; border-color: #e2e8f0 !important; color: #94a3b8 !important; }

/* ─── MULTISELECT ─────────────────────────────────────────────────── */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div { background: #ffffff !important; }

/* ─── SCROLLBAR ───────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* ─── PAGE HEADER ─────────────────────────────────────────────────── */
.pg-header { border-bottom: 1px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px; }
.pg-title { font-family: 'Geist', sans-serif; font-size: 28px; font-weight: 700; color: #0f172a; letter-spacing: -0.01em; line-height: 1.2; }
.pg-sub { font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; color: #94a3b8; margin-top: 4px; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── METRIC CARD ─────────────────────────────────────────────────── */
.m-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px 16px 16px; position: relative; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.m-label { font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
.m-value { font-family: 'Geist', sans-serif; font-size: 36px; font-weight: 700; line-height: 1; letter-spacing: -0.02em; }
.m-icon { position: absolute; top: 16px; right: 16px; font-size: 18px; opacity: 0.2; }

/* ─── ISS CARD ────────────────────────────────────────────────────── */
.isp-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 8px; transition: border-color 0.2s, box-shadow 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.isp-card:hover { border-color: #0891b2; box-shadow: 0 4px 12px rgba(8,145,178,0.1); }
.isp-name { font-family: 'Geist', sans-serif; font-weight: 700; font-size: 15px; color: #0f172a; }
.price-main { font-family: 'Geist', sans-serif; font-size: 28px; font-weight: 700; color: #0891b2; letter-spacing: -0.02em; }
.price-unit { font-size: 13px; color: #94a3b8; font-weight: 400; }
.price-next { font-size: 13px; color: #dc2626; margin-left: 6px; }
.isp-paket { font-size: 13px; color: #64748b; margin: 6px 0 10px; min-height: 18px; font-family: 'Inter', sans-serif; line-height: 1.4; }
.isp-extras { font-size: 12px; color: #94a3b8; margin-top: 8px; border-top: 1px solid #f1f5f9; padding-top: 8px; }

/* ─── ALERT BOXES ─────────────────────────────────────────────────── */
.alert-box { background: #ffffff; border: 1px solid #e2e8f0; border-left: 3px solid #cbd5e1; padding: 14px 16px; border-radius: 8px; margin: 6px 0; color: #374151; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.alert-red  { border-left-color: #dc2626 !important; background: #fef2f2 !important; }
.alert-green{ border-left-color: #059669 !important; background: #f0fdf4 !important; }
.alert-cyan { border-left-color: #0891b2 !important; background: #f0f9ff !important; }

/* ─── DIFF ────────────────────────────────────────────────────────── */
.diff-wrap { margin-top: 10px; }
.diff-old  { background: #fef2f2; border-left: 2px solid #dc2626; padding: 5px 10px; border-radius: 4px; margin: 3px 0; color: #991b1b; font-size: 13px; }
.diff-new  { background: #f0fdf4; border-left: 2px solid #059669; padding: 5px 10px; border-radius: 4px; margin: 3px 0; color: #065f46; font-size: 13px; }
.diff-label { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .08em; margin-top: 8px; }

/* ─── BADGES ──────────────────────────────────────────────────────── */
.badge { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 100px; font-weight: 600; margin: 2px 2px 0 0; font-family: 'Inter', sans-serif; letter-spacing: 0.02em; }
.badge-fiber{ background: #e0f2fe; color: #0369a1; }
.badge-vdsl { background: #f3e8ff; color: #7e22ce; }
.badge-adsl { background: #dcfce7; color: #15803d; }
.badge-5g   { background: #dcfce7; color: #15803d; }
.badge-other{ background: #f1f5f9; color: #64748b; }
.badge-taah { background: #fee2e2; color: #b91c1c; }
.badge-free { background: #dcfce7; color: #15803d; }
.badge-kur  { background: #f3e8ff; color: #7e22ce; }

/* ─── RANK ────────────────────────────────────────────────────────── */
.rank-gold  { border-top: 2px solid #f59e0b !important; }
.rank-silver{ border-top: 2px solid #94a3b8 !important; }
.rank-bronze{ border-top: 2px solid #d97706 !important; }

/* ─── LIVE DOT ────────────────────────────────────────────────────── */
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.live-dot { display:inline-block; width:7px; height:7px; border-radius:2px; background:#059669; animation:pulse 2s ease-in-out infinite; margin-right:8px; vertical-align:middle; }

/* ─── STAT CARD (profil sayfası) ──────────────────────────────────── */
.stat-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.stat-num  { font-family: 'Geist', sans-serif; font-size: 28px; font-weight: 700; margin: 4px 0 0; letter-spacing: -0.02em; }
.stat-lbl  { font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600; color: #94a3b8; margin: 4px 0 0; text-transform: uppercase; letter-spacing: .05em; }
</style>
""", unsafe_allow_html=True)


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _parse_val(raw):
    if raw is None or str(raw).strip() in ("", "None", "nan"):
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return " · ".join(str(x) for x in parsed) if parsed else None
        return str(parsed)
    except Exception:
        return str(raw).strip() or None


def pg_header(title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="pg-header">'
        f'<div class="pg-title">{title}</div>'
        + (f'<div class="pg-sub">{subtitle}</div>' if subtitle else "")
        + '</div>',
        unsafe_allow_html=True,
    )


def metric_card(col, icon: str, val, label: str, accent: str):
    col.markdown(
        f'<div class="m-card" style="border-top:2px solid {accent}">'
        f'<div class="m-icon">{icon}</div>'
        f'<div class="m-label">{label}</div>'
        f'<div class="m-value" style="color:{accent}">{val}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_alert(row, compact=False):
    tur = row["tur"]

    # Tip konfigürasyonu
    TUR_CFG = {
        "fiyat_dustu":      ("↓", "#059669", "#f0fdf4", "#dcfce7", "Fiyat Düştü"),
        "fiyat_yukseldi":   ("↑", "#dc2626", "#fff7f7", "#fee2e2", "Fiyat Yükseldi"),
        "yeni_paket":       ("+", "#0891b2", "#f0f9ff", "#e0f2fe", "Yeni Paket"),
        "paket_kaldirildi": ("✕", "#64748b", "#f8fafc", "#f1f5f9", "Paket Kaldırıldı"),
        "icerik_degisim":   ("≠", "#7c3aed", "#faf5ff", "#f3e8ff", "İçerik Değişti"),
        "kampanya_degisti": ("~", "#d97706", "#fffbeb", "#fef3c7", "Kampanya Değişti"),
    }
    icon, accent, bg, badge_bg, tur_lbl = TUR_CFG.get(
        tur, ("·", "#94a3b8", "#f8fafc", "#f1f5f9", tur))

    ts    = str(row.get("olusma_zamani", ""))
    zaman = ts[-8:] if compact else ts[5:19].replace("T", " ")

    # Fiyat değişimi — mesajdan parse et (package_history JOIN yanlış zaman verebilir)
    fiyat_html = ""
    if tur in ("fiyat_dustu", "fiyat_yukseldi"):
        import re as _re
        mesaj_raw = str(row.get("mesaj", ""))
        m = _re.search(r'([\d,.]+)₺\s*→\s*([\d,.]+)₺', mesaj_raw)
        if m:
            try:
                e = float(m.group(1).replace(",", ""))
                y = float(m.group(2).replace(",", ""))
                diff = y - e
                diff_str = f"+{diff:,.0f}₺" if diff > 0 else f"{diff:,.0f}₺"
                diff_color = "#dc2626" if diff > 0 else "#059669"
                fiyat_html = (
                    f'<div style="display:flex;align-items:center;gap:10px;margin-top:8px;'
                    f'background:{badge_bg};border-radius:6px;padding:8px 12px">'
                    f'<span style="font-size:15px;color:#94a3b8;text-decoration:line-through">{e:,.0f}₺</span>'
                    f'<span style="color:#94a3b8">→</span>'
                    f'<span style="font-family:\'Geist\',sans-serif;font-size:18px;font-weight:700;color:{accent}">{y:,.0f}₺</span>'
                    f'<span style="font-size:13px;font-weight:600;color:{diff_color};margin-left:4px">{diff_str}</span>'
                    f'</div>'
                )
            except Exception:
                pass

    # Mesaj + diff bloğu
    import re as _re2
    mesaj = str(row.get("mesaj", ""))
    diff_html = ""

    if tur == "icerik_degisim":
        # URL: ve PAKET: satırlarını çıkar
        degisen_urls = []
        paket_adlari = []
        for _ in range(2):
            if mesaj.startswith("URL: "):
                url_line, mesaj = mesaj.split("\n", 1)
                degisen_urls = [u.strip() for u in url_line[5:].split("|") if u.strip()]
            elif mesaj.startswith("PAKET: "):
                pkg_line, mesaj = mesaj.split("\n", 1)
                paket_adlari = [p.strip() for p in pkg_line[7:].split("·") if p.strip()]
        diff_raw = _re2.sub(r'^Sayfa içeriği değişti:\n?', '', mesaj).strip()
        lines = diff_raw.splitlines()
        plus_lines  = [l for l in lines if l.startswith("+") and len(l.strip()) > 1]
        minus_lines = [l for l in lines if l.startswith("-") and len(l.strip()) > 1]

        # Özet
        parts = []
        if plus_lines:  parts.append(f"<b style='color:#059669'>+{len(plus_lines)}</b>")
        if minus_lines: parts.append(f"<b style='color:#dc2626'>−{len(minus_lines)}</b>")
        mesaj = (" ".join(parts) + " satır değişti") if parts else "İçerik değişti"

        MAX_EACH = 6

        # Sadece sayı / birim olan anlamsız DOM parçalarını filtrele
        _GURULTU = _re2.compile(
            r'^(\d+|Mbps|Gbps|TL|İndirme\s*Hızı|Yükleme\s*Hızı|İncele|Detaylar?|'
            r'Limitsiz|Limitsiz\s*Kota|Ek\s*Bilgiler?|---+)$', _re2.I
        )

        def _clean(raw_lines):
            seen, out = set(), []
            for l in raw_lines:
                t = l[1:].lstrip("-+ ").strip()
                if t and not _GURULTU.match(t) and t not in seen:
                    seen.add(t)
                    out.append(t)
            return out

        removed_lines = _clean(l for l in lines if l.startswith("-") and len(l.strip()) > 1)
        added_lines   = _clean(l for l in lines if l.startswith("+") and len(l.strip()) > 1)

        rows_html = []
        if removed_lines or added_lines:
            # Her iki tarafta da aynı olan satırları çıkar — sadece gerçek farkı göster
            added_set   = set(added_lines)
            removed_set = set(removed_lines)
            removed_lines = [l for l in removed_lines if l not in added_set]
            added_lines   = [l for l in added_lines   if l not in removed_set]

            # Tek kolon ise hepsini göster; iki kolon ise MAX_EACH ile kırp
            both = bool(removed_lines and added_lines)
            MAX_SHOW = MAX_EACH if both else 20

            def _col(lines, clr_bg, clr_txt, clr_hdr_bg, clr_hdr_txt, label):
                rows = [f'<div style="font-size:10px;font-weight:700;color:{clr_hdr_txt};padding:3px 8px;background:{clr_hdr_bg}">{label}</div>']
                for t in lines[:MAX_SHOW]:
                    rows.append(f'<div style="background:{clr_bg};color:{clr_txt};padding:2px 8px;font-size:11px;font-family:JetBrains Mono,monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t}</div>')
                if len(lines) > MAX_SHOW:
                    rows.append(f'<div style="color:#94a3b8;font-size:10px;padding:2px 8px">… {len(lines)-MAX_SHOW} satır daha</div>')
                return "".join(rows)

            if removed_lines and added_lines:
                # İkisi de var → yan yana karşılaştırma
                left  = _col(removed_lines, "#fff7f7", "#991b1b", "#ffe4e4", "#7f1d1d", f"ÖNCE ({len(removed_lines)} satır)")
                right = _col(added_lines,   "#f0fdf4", "#166534", "#dcfce7", "#14532d", f"SONRA ({len(added_lines)} satır)")
                diff_html = (
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;'
                    f'border:1px solid {badge_bg};border-radius:6px;overflow:hidden;margin-top:8px">'
                    f'<div>{left}</div><div style="border-left:1px solid {badge_bg}">{right}</div>'
                    f'</div>'
                )
            elif removed_lines:
                diff_html = f'<div style="border:1px solid #fecaca;border-radius:6px;overflow:hidden;margin-top:8px">{_col(removed_lines, "#fff7f7", "#991b1b", "#ffe4e4", "#7f1d1d", f"KALDIRILAN İÇERİK ({len(removed_lines)} satır)")}</div>'
            else:
                diff_html = f'<div style="border:1px solid #bbf7d0;border-radius:6px;overflow:hidden;margin-top:8px">{_col(added_lines, "#f0fdf4", "#166534", "#dcfce7", "#14532d", f"EKLENEN İÇERİK ({len(added_lines)} satır)")}</div>'

        # Paket adı — diff bloğunun altına küçük etiket
        if paket_adlari:
            pkg_str = " · ".join(paket_adlari)
            diff_html += (
                f'<div style="font-size:11px;color:{accent};margin-top:5px;'
                f'font-weight:600">📦 {pkg_str}</div>'
            )

        # Değişen sayfa linkleri — diff bloğunun altına ekle
        if degisen_urls:
            url_links = " ".join(
                f'<a href="{u}" target="_blank" style="font-size:11px;color:{accent};'
                f'text-decoration:none;background:{badge_bg};padding:2px 8px;'
                f'border-radius:100px;margin-right:4px;display:inline-block;margin-top:6px">'
                f'↗ sayfa {i+1}</a>'
                for i, u in enumerate(degisen_urls)
            )
            diff_html += f'<div>{url_links}</div>'
    elif "|" in mesaj:
        parts = mesaj.split("|", 1)
        mesaj = parts[1].strip() if len(parts) > 1 else mesaj
        mesaj = mesaj[:140] + ("…" if len(mesaj) > 140 else "")
    else:
        mesaj = mesaj[:140] + ("…" if len(mesaj) > 140 else "")

    unread = (
        f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
        f'background:{accent};margin-left:6px;vertical-align:middle"></span>'
        if not row.get("goruldu") else ""
    )
    isp_url = row.get("isp_url") or ""
    url_html = (
        f'<a href="{isp_url}" target="_blank" style="color:{accent};text-decoration:none;'
        f'font-size:12px;margin-left:6px" title="Siteye git">↗</a>'
        if isp_url and not compact else ""
    )

    st.markdown(
        f'<div style="background:{bg};border:1px solid {badge_bg};border-left:3px solid {accent};'
        f'border-radius:8px;padding:12px 16px;margin:4px 0">'
        # Üst satır: tip badge + ISS adı + zaman
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'  <div style="display:flex;align-items:center;gap:8px">'
        f'    <span style="background:{badge_bg};color:{accent};font-size:11px;font-weight:700;'
        f'    padding:2px 8px;border-radius:100px">{icon} {tur_lbl}</span>'
        f'    <span style="font-family:\'Geist\',sans-serif;font-weight:700;font-size:14px;'
        f'    color:#0f172a">{row["iss"]}</span>'
        f'    {unread}{url_html}'
        f'  </div>'
        f'  <span style="font-size:12px;color:#94a3b8">{zaman}</span>'
        f'</div>'
        # Alt satır: mesaj
        f'<div style="font-size:13px;color:#64748b;line-height:1.4">{mesaj}</div>'
        f'{fiyat_html}'
        f'{diff_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _tech_badge(teknoloji):
    t = str(teknoloji).lower()
    css = {"fiber": "badge-fiber", "vdsl": "badge-vdsl", "adsl": "badge-adsl",
           "5g": "badge-5g"}.get(t, "badge-other")
    return f'<span class="badge {css}">{teknoloji.upper()}</span>'


def _fmt_fiyat(v):
    if pd.isna(v) or v == 0:
        return "—"
    return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"


def _fmt_hiz(v):
    if pd.isna(v) or v == "" or v == 0:
        return "—"
    try:
        return f"{int(v):,}"
    except (ValueError, TypeError):
        return str(v)  # "5G" gibi string değerler


_FMT = {
    "Fiyat":          _fmt_fiyat,
    "Sonraki Fiyat":  lambda v: _fmt_fiyat(v) if pd.notna(v) else "",
    "Toplam/ay":      _fmt_fiyat,
    "Modem/ay":       _fmt_fiyat,
    "Hız":            _fmt_hiz,
    "Hız (Mbps)":     _fmt_hiz,
    "Taahhüt(ay)":    lambda v: "" if pd.isna(v) else str(int(v)),
    "Min":            _fmt_fiyat,
    "Max":            _fmt_fiyat,
    "Ort. Fiyat":     _fmt_fiyat,
    "Medyan Fiyat":   _fmt_fiyat,
}

_KURUMSAL_KW = [
    "kobi", "kobı", "işyeri", "is yeri", "esnaf", "kurumsal", "ticari",
    "ofis", "business", "metro ethernet", "simetri", "prime", "elite", "vip",
    "gurbetçi", "diaspora",
]

def _is_kurumsal(paket_adi: str) -> bool:
    return any(k in str(paket_adi).lower() for k in _KURUMSAL_KW)

def _kat_badge(kat: str) -> str:
    return {"rakip": "BÜYÜK/RAKİP", "diger": "DİĞER"}.get(kat, kat or "—")

def _apply_fmt(styler):
    fmt = {col: fn for col, fn in _FMT.items() if col in styler.data.columns}
    return styler.format(fmt) if fmt else styler

def _grad_style(series: pd.Series) -> list:
    mn, mx = series.min(), series.max()
    out = []
    for v in series:
        if pd.isna(v) or mx == mn:
            out.append("")
            continue
        ratio = (v - mn) / (mx - mn)
        r = int(55 + ratio * 170)
        g = int(180 - ratio * 130)
        out.append(f"background-color: rgba({r},{g},55,0.25)")
    return out

def _taahhut_badge(ay):
    try:
        ay = int(ay)
    except (TypeError, ValueError):
        ay = 0
    if ay == 0:
        return '<span class="badge badge-free">TAAHHÜTSÜZ</span>'
    return f'<span class="badge badge-taah">{ay}AY</span>'

def _fiyatli(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["fiyat_ilk_donem"].notna() & (df["fiyat_ilk_donem"] > 0)]

def _dedup_alerts(alerts_df: pd.DataFrame) -> dict:
    shown = {}
    for _, row in alerts_df.iterrows():
        aid = row["id"]
        if aid not in shown:
            shown[aid] = row.to_dict()
        elif not shown[aid].get("eski_deger") and row.get("eski_deger"):
            shown[aid]["eski_deger"] = row["eski_deger"]
            shown[aid]["yeni_deger"] = row["yeni_deger"]
    return shown


# ── Veri yükleme ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_packages() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT i.name AS iss, i.kategori,
               p.paket_adi, p.hiz_mbps, p.hiz_yukleme_mbps, p.teknoloji,
               p.fiyat_ilk_donem, p.fiyat_sonraki_donem, p.ilk_donem_ay,
               p.fiyat_sabit_mi, p.sozlesme_suresi_ay, p.taahhut_var,
               p.modem, p.modem_ucreti_aylik, p.sadece_yeni_musteri,
               p.kurulum_ucreti, p.one_cikan_ifadeler, p.ek_paketler,
               p.bolge_kisiti, p.kampanya_bitis, p.son_guncelleme, p.paket_key
        FROM packages p JOIN isps i ON i.id = p.isp_id
        WHERE p.aktif = 1 AND i.aktif = 1
        ORDER BY p.hiz_mbps, p.fiyat_ilk_donem
    """, conn)
    conn.close()
    df["one_cikan_ifadeler"] = df["one_cikan_ifadeler"].apply(
        lambda x: ", ".join(json.loads(x)) if x and x != "[]" else "")
    df["ek_paketler"] = df["ek_paketler"].apply(
        lambda x: ", ".join(json.loads(x)) if x and x != "[]" else "")
    df["toplam_aylik"] = df.apply(
        lambda r: (r["fiyat_ilk_donem"] or 0) + (r["modem_ucreti_aylik"] or 0)
        if pd.notna(r["fiyat_ilk_donem"]) and r["fiyat_ilk_donem"] > 0 else None, axis=1)
    import re as _re
    def _fallback_ilk(row):
        if pd.notna(row.get("ilk_donem_ay")) and row["ilk_donem_ay"]: return row["ilk_donem_ay"]
        m = _re.search(r"ilk\s+(\d+)\s*ay", str(row.get("one_cikan_ifadeler") or ""), _re.I)
        return int(m.group(1)) if m else None
    df["ilk_donem_ay"] = df.apply(_fallback_ilk, axis=1)
    def _spd(row):
        if pd.notna(row["hiz_mbps"]) and row["hiz_mbps"] > 0: return row["hiz_mbps"]
        for txt in [row.get("paket_adi",""), row.get("one_cikan_ifadeler","")]:
            if not txt: continue
            m = _re.search(r"(\d[\d\.]*)\s*(g|gbps|gb/s)", str(txt), _re.I)
            if m: return int(float(m.group(1).replace(".",""))*1000)
            m = _re.search(r"(\d+)\s*(m|mbps|mb/s)", str(txt), _re.I)
            if m: return int(m.group(1))
        return row["hiz_mbps"]
    df["hiz_mbps"] = df.apply(_spd, axis=1)
    return df


@st.cache_data(ttl=30)
def load_alerts(limit: int = 100) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(f"""
        SELECT a.id, i.name AS iss, i.kategori,
               COALESCE(
                   (SELECT iu.url FROM isp_urls iu
                    WHERE iu.isp_id = i.id AND iu.aktif = 1
                    ORDER BY iu.id LIMIT 1),
                   i.url
               ) AS isp_url,
               a.paket_key, a.tur, a.mesaj, a.olusma_zamani, a.goruldu,
               ph.alan AS diff_alan, ph.eski_deger, ph.yeni_deger
        FROM alerts a JOIN isps i ON i.id = a.isp_id
        LEFT JOIN package_history ph
            ON ph.paket_key = a.paket_key
            AND ph.alan IN ('fiyat_ilk_donem','fiyat_sonraki_donem','modem','sozlesme_suresi_ay')
            AND ph.degisim_zamani = (
                SELECT MAX(ph2.degisim_zamani) FROM package_history ph2
                WHERE ph2.paket_key = a.paket_key AND ph2.alan = ph.alan)
        ORDER BY a.olusma_zamani DESC LIMIT {limit}
    """, conn)
    conn.close()
    return df


@st.cache_data(ttl=60)
def load_history(paket_key: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT ph.degisim_zamani, ph.alan, ph.eski_deger, ph.yeni_deger, ph.aciklama
        FROM package_history ph WHERE ph.paket_key = ?
        ORDER BY ph.degisim_zamani DESC LIMIT 50
    """, conn, params=(paket_key,))
    conn.close()
    return df


@st.cache_data(ttl=60)
def load_price_trend(isp_name: str, hiz: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT ph.degisim_zamani AS tarih, CAST(ph.yeni_deger AS REAL) AS fiyat
        FROM package_history ph
        JOIN packages p ON p.paket_key = ph.paket_key
        JOIN isps i ON i.id = p.isp_id
        WHERE i.name = ? AND p.hiz_mbps = ? AND ph.alan = 'fiyat_ilk_donem'
        ORDER BY ph.degisim_zamani
    """, conn, params=(isp_name, hiz))
    conn.close()
    return df


def mark_all_read():
    conn = get_conn()
    conn.execute("UPDATE alerts SET goruldu=1 WHERE goruldu=0")
    conn.commit(); conn.close()
    st.cache_data.clear()


@st.cache_data(ttl=60)
def get_stats(kategoriler: tuple = ()) -> dict:
    conn = get_conn()
    s = {}

    def q(sql, params=()):
        return conn.execute(sql, list(params)).fetchone()[0]

    if kategoriler:
        ph = ",".join("?" * len(kategoriler))
        k  = list(kategoriler)
        s["toplam_iss"]    = q(f"SELECT COUNT(DISTINCT p.isp_id) FROM packages p JOIN isps i ON i.id=p.isp_id WHERE p.aktif=1 AND i.aktif=1 AND i.kategori IN ({ph})", k)
        s["toplam_paket"]  = q(f"SELECT COUNT(*) FROM packages p JOIN isps i ON i.id=p.isp_id WHERE p.aktif=1 AND i.aktif=1 AND i.kategori IN ({ph})", k)
        s["yeni_alert"]    = q(f"SELECT COUNT(*) FROM alerts a JOIN isps i ON i.id=a.isp_id WHERE a.goruldu=0 AND i.kategori IN ({ph})", k)
        s["son_kontrol"]   = q("SELECT value FROM meta WHERE key='last_run_ts'") or "—"
        s["degisim_bugun"] = q(f"SELECT COUNT(DISTINCT ph.isp_id) FROM package_history ph JOIN isps i ON i.id=ph.isp_id WHERE date(ph.degisim_zamani)=date('now','localtime') AND i.kategori IN ({ph})", k)
        for tur, key in [("fiyat_dustu","fiyat_dustu_7g"),("fiyat_yukseldi","fiyat_yukseldi_7g"),
                         ("yeni_paket","yeni_paket_7g"),("paket_kaldirildi","paket_kaldi_7g")]:
            s[key] = q(f"SELECT COUNT(*) FROM alerts a JOIN isps i ON i.id=a.isp_id WHERE a.tur=? AND a.olusma_zamani>=datetime('now','-7 days','localtime') AND i.kategori IN ({ph})", [tur]+k)
    else:
        s["toplam_iss"]    = q("SELECT COUNT(DISTINCT isp_id) FROM packages WHERE aktif=1")
        s["toplam_paket"]  = q("SELECT COUNT(*) FROM packages WHERE aktif=1")
        s["yeni_alert"]    = q("SELECT COUNT(*) FROM alerts WHERE goruldu=0")
        s["son_kontrol"]   = q("SELECT value FROM meta WHERE key='last_run_ts'") or "—"
        s["degisim_bugun"] = q("SELECT COUNT(DISTINCT isp_id) FROM package_history WHERE date(degisim_zamani)=date('now','localtime')")
        for tur, key in [("fiyat_dustu","fiyat_dustu_7g"),("fiyat_yukseldi","fiyat_yukseldi_7g"),
                         ("yeni_paket","yeni_paket_7g"),("paket_kaldirildi","paket_kaldi_7g")]:
            s[key] = q("SELECT COUNT(*) FROM alerts WHERE tur=? AND olusma_zamani>=datetime('now','-7 days','localtime')", (tur,))

    conn.close()
    return s


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

KAT_LABEL = {"rakip": "🏢 Büyük ve Rakip", "diger": "🌐 Diğer"}

with st.sidebar:
    st.markdown(
        '<div style="padding:24px 16px 16px">'
        '<div style="font-family:\'Geist\',sans-serif;font-size:22px;font-weight:800;'
        'color:#0f172a;letter-spacing:-0.01em">'
        '<span class="live-dot"></span>ISP INTEL</div>'
        '<div style="font-family:\'Inter\',sans-serif;font-size:12px;font-weight:600;'
        'color:#94a3b8;letter-spacing:0.05em;text-transform:uppercase;margin-top:2px">'
        'Market Intelligence</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="border-top:1px solid #1e293b;margin:0 0 8px"></div>', unsafe_allow_html=True)

    sayfa = st.radio("", [
        "📊 Genel Bakış",
        "🏆 Karşılaştırma",
        "📦 Tüm Paketler",
        "🏢 ISS Profili",
        "🔔 Bildirimler",
        "📈 Fiyat Trendi",
    ], label_visibility="collapsed")

    st.markdown('<div style="border-top:1px solid #1e293b;margin:8px 0"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.65em;color:#334155;'
                'text-transform:uppercase;letter-spacing:0.08em;padding:0 14px 4px">ISS Filtre</div>',
                unsafe_allow_html=True)
    kat_filtre = st.multiselect(
        "", ["🏢 Büyük ve Rakip", "🌐 Diğer"],
        default=["🏢 Büyük ve Rakip", "🌐 Diğer"],
        label_visibility="collapsed",
    )
    _kat_secim = {v: k for k, v in KAT_LABEL.items()}
    aktif_katlar = [_kat_secim[l] for l in kat_filtre if l in _kat_secim]

    st.markdown('<div style="border-top:1px solid #e2e8f0;margin:8px 0 4px"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;padding:2px 4px 6px">'
        f'<span style="font-size:11px;color:#94a3b8">{datetime.now().strftime("%H:%M:%S")}</span>'
        f'<span id="cdown" style="font-size:11px;color:#cbd5e1">60s</span></div>'
        f'<script>var t=60,el=document.getElementById("cdown"),'
        f'iv=setInterval(function(){{t--;if(el)el.textContent=t+"s";'
        f'if(t<=0)clearInterval(iv);}},1000);</script>',
        unsafe_allow_html=True,
    )
    if st.button("Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # bottom user strip
    st.markdown(
        '<div style="position:fixed;bottom:0;left:0;width:244px;border-top:1px solid #e2e8f0;'
        'background:#f1f5f9;padding:12px 16px;display:flex;align-items:center;gap:10px">'
        '<div style="width:32px;height:32px;border-radius:8px;background:#e2e8f0;'
        'display:flex;align-items:center;justify-content:center;font-size:14px">👤</div>'
        '<div><div style="font-family:\'Inter\',sans-serif;font-size:13px;font-weight:600;color:#374151">'
        'Analist</div>'
        '<div style="font-family:\'Inter\',sans-serif;font-size:11px;color:#94a3b8;margin-top:1px">'
        'Sistem Hazır</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── GENEL BAKIŞ ───────────────────────────────────────────────────────────────

if sayfa == "📊 Genel Bakış":
    stats = get_stats(tuple(aktif_katlar) if aktif_katlar else ())
    pg_header("MARKET OVERVIEW", "REAL-TIME COMPETITIVE INTELLIGENCE")

    # Metric cards
    c1, c2, c3, c4, c5 = st.columns(5)
    alert_accent = "#ff6b7a" if stats["yeni_alert"] > 0 else "#4edea3"
    son_k = stats["son_kontrol"]
    son_k_fmt = son_k[-8:] if son_k != "—" else "—"
    metric_card(c1, "📡", stats["toplam_iss"],   "Aktif ISS",       "#2fd9f4")
    metric_card(c2, "📦", stats["toplam_paket"], "Aktif Paket",     "#cbb5ff")
    metric_card(c3, "🔔", stats["yeni_alert"],   "Okunmamış Alert",  alert_accent)
    metric_card(c4, "🔁", stats["degisim_bugun"],"Bugün Değişen",   "#f59e0b")
    metric_card(c5, "⟳",  son_k_fmt,             "Son Kontrol",     "#475569")

    st.markdown("<br>", unsafe_allow_html=True)

    # 7-günlük nabız
    pulse_items = [
        (stats.get("fiyat_dustu_7g",    0), "↓", "fiyat düştü",   "#065f46", "#dcfce7"),
        (stats.get("fiyat_yukseldi_7g", 0), "↑", "fiyat yükseldi","#991b1b", "#fee2e2"),
        (stats.get("yeni_paket_7g",     0), "+", "yeni paket",    "#075985", "#e0f2fe"),
        (stats.get("paket_kaldi_7g",    0), "✕", "paket kalktı",  "#374151", "#f1f5f9"),
    ]
    badges = "".join(
        f'<span style="background:{bg};color:{fg};padding:6px 14px;border-radius:100px;'
        f'font-family:\'Inter\',sans-serif;font-size:13px;font-weight:600;'
        f'white-space:nowrap">{arrow} {cnt} {lbl}</span>'
        for cnt, arrow, lbl, fg, bg in pulse_items if cnt > 0
    )
    if badges:
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:12px 16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;'
            f'box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
            f'<span style="font-family:\'Inter\',sans-serif;font-size:12px;font-weight:600;'
            f'color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap">Son 7 Gün</span>'
            f'<span style="color:#e2e8f0">│</span>'
            f'{badges}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    df = load_packages()
    if aktif_katlar:
        df = df[df["kategori"].isin(aktif_katlar)]
    if df.empty:
        st.info("Henüz paket verisi yok.")
        st.stop()

    # ── Chart yardımcısı ──
    def _section_label(text):
        st.markdown(
            f'<div style="font-size:12px;font-weight:600;color:#94a3b8;text-transform:uppercase;'
            f'letter-spacing:.05em;margin-bottom:10px">{text}</div>',
            unsafe_allow_html=True)

    def _hbar(items, color="#0891b2", label_width=90):
        """Yatay bar chart — custom HTML"""
        if not items: return ""
        max_v = max(v for _, v in items) or 1
        TEK_COLORS = {"fiber":"#0891b2","vdsl":"#7e22ce","adsl":"#059669",
                      "5g":"#d97706","belirsiz":"#94a3b8","sabit_kablosuz":"#dc2626"}
        rows = []
        for lbl, val in items:
            bar_color = TEK_COLORS.get(str(lbl).lower(), color)
            pct = val / max_v * 100
            rows.append(
                f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0">'
                f'<span style="font-size:12px;color:#374151;width:{label_width}px;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap" title="{lbl}">{lbl}</span>'
                f'<div style="flex:1;background:#f1f5f9;border-radius:3px;height:8px">'
                f'<div style="width:{pct:.1f}%;background:{bar_color};border-radius:3px;height:100%">'
                f'</div></div>'
                f'<span style="font-size:12px;color:#94a3b8;min-width:24px;text-align:right">{val}</span>'
                f'</div>'
            )
        return (
            '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;'
            'padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
            + "".join(rows) + "</div>"
        )

    # Scatter + sağ kolon
    col_sc, col_tk = st.columns([3, 2])

    with col_sc:
        sc_src = _fiyatli(df[df["hiz_mbps"].notna() & (df["hiz_mbps"] > 0)].copy())

        if _HAS_ALTAIR and not sc_src.empty:
            TEK_DOMAIN = ["fiber","vdsl","adsl","5g","belirsiz","sabit_kablosuz"]
            TEK_RANGE  = ["#0891b2","#7e22ce","#059669","#f59e0b","#94a3b8","#dc2626"]

            # Outlier sayısını göster
            n_total   = len(sc_src)
            n_clipped = len(sc_src[sc_src["hiz_mbps"] <= 1500])
            clip_note = (
                f'<span style="font-size:11px;color:#94a3b8;margin-left:8px">'
                f'(+{n_total - n_clipped} outlier gizli — zoom ile görün)</span>'
                if n_total > n_clipped else ""
            )
            st.markdown(
                f'<div style="font-size:12px;font-weight:600;color:#94a3b8;text-transform:uppercase;'
                f'letter-spacing:.05em;margin-bottom:4px">Hız × Fiyat Haritası{clip_note}</div>',
                unsafe_allow_html=True)

            chart = (
                alt.Chart(sc_src)
                .mark_circle(size=80, opacity=0.8, stroke="white", strokeWidth=1.5)
                .encode(
                    x=alt.X("hiz_mbps:Q", title="Hız (Mbps)",
                        scale=alt.Scale(zero=True, domainMax=1500),
                        axis=alt.Axis(labelFont="Inter", titleFont="Inter",
                            labelFontSize=11, titleFontSize=12,
                            labelColor="#94a3b8", titleColor="#64748b",
                            gridColor="#f1f5f9", domainColor="#e2e8f0",
                            tickColor="#e2e8f0", format=",.0f")),
                    y=alt.Y("fiyat_ilk_donem:Q", title="Fiyat (₺)",
                        scale=alt.Scale(zero=True),
                        axis=alt.Axis(labelFont="Inter", titleFont="Inter",
                            labelFontSize=11, titleFontSize=12,
                            labelColor="#94a3b8", titleColor="#64748b",
                            gridColor="#f1f5f9", domainColor="#e2e8f0",
                            tickColor="#e2e8f0", format=",.0f")),
                    color=alt.Color("teknoloji:N", title=None,
                        scale=alt.Scale(domain=TEK_DOMAIN, range=TEK_RANGE),
                        legend=alt.Legend(
                            labelFont="Inter", labelFontSize=12,
                            labelColor="#374151", orient="bottom",
                            columns=6, symbolSize=80,
                            padding=8, columnPadding=16,
                        )),
                    tooltip=[
                        alt.Tooltip("iss:N",              title="ISS"),
                        alt.Tooltip("hiz_mbps:Q",         title="Hız (Mbps)",  format=",.0f"),
                        alt.Tooltip("fiyat_ilk_donem:Q",  title="Fiyat (₺)",   format=",.0f"),
                        alt.Tooltip("teknoloji:N",         title="Teknoloji"),
                        alt.Tooltip("paket_adi:N",         title="Paket"),
                    ]
                )
                .properties(height=260, background="transparent")
                .interactive()
                .configure_view(stroke=None, fill="transparent")
                .configure_axis(labelPadding=6)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            sc_r = sc_src.rename(columns={"hiz_mbps":"Hız (Mbps)","fiyat_ilk_donem":"Fiyat (₺)","teknoloji":"Teknoloji"})
            st.scatter_chart(sc_r, x="Hız (Mbps)", y="Fiyat (₺)", color="Teknoloji", height=280)

    with col_tk:
        _section_label("Teknoloji Dağılımı")
        tek_items = (
            df.groupby("teknoloji")["iss"].nunique()
            .sort_values(ascending=False).items()
        )
        st.markdown(_hbar(list(tek_items)), unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        _section_label("ISS Başına Paket Sayısı")
        iss_items = (
            df[df["hiz_mbps"].notna() & (df["hiz_mbps"] > 0)]
            .groupby("iss").size()
            .sort_values(ascending=False).head(7).items()
        )
        st.markdown(_hbar(list(iss_items), color="#7e22ce"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Fiyat aralığı barları
    st.markdown(
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#475569;'
        'text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">HIZ KADEMESİ FİYAT DAĞILIMI</div>'
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.64em;color:#334155;'
        'margin-bottom:12px">Kurumsal/KOBİ hariç · Dikey çizgi = medyan</div>',
        unsafe_allow_html=True)

    df_g = _fiyatli(df[~df["paket_adi"].apply(_is_kurumsal)]).copy()
    df_g["fg"] = df_g.apply(
        lambda r: r["fiyat_sonraki_donem"]
        if (r["fiyat_ilk_donem"] < 50 and pd.notna(r["fiyat_sonraki_donem"]) and r["fiyat_sonraki_donem"] > 50)
        else r["fiyat_ilk_donem"], axis=1)
    avg_f = df_g.groupby("hiz_mbps")["fg"].agg(["median","min","max","count"]).reset_index().sort_values("hiz_mbps")

    if not avg_f.empty:
        gmax  = avg_f["max"].max() or 2000
        scale = 86.0 / gmax
        rows  = []
        for _, r in avg_f.iterrows():
            hiz  = int(r["hiz_mbps"])
            minp = r["min"]; maxp = r["max"]; medp = r["median"]; cnt = int(r["count"])
            hs   = f"{hiz:,} Mbps" if hiz < 1000 else f"{hiz//1000} Gbps"
            bl   = minp * scale
            bw   = max((maxp - minp) * scale, 1.5)
            mp   = medp * scale
            rows.append(
                f'<div style="display:grid;grid-template-columns:88px 1fr 90px;gap:12px;'
                f'align-items:center;padding:10px 0;border-bottom:1px solid #f1f5f9">'
                f'  <span style="font-family:\'Inter\',sans-serif;font-size:12px;font-weight:600;'
                f'color:#0891b2;background:#e0f2fe;padding:3px 8px;border-radius:100px;'
                f'white-space:nowrap">{hs}</span>'
                f'  <div>'
                f'    <div style="position:relative;height:6px;background:#f1f5f9;border-radius:3px">'
                f'      <div style="position:absolute;left:{bl:.1f}%;width:{bw:.1f}%;height:100%;'
                f'background:linear-gradient(90deg,#059669,#f59e0b,#dc2626);border-radius:3px;opacity:0.7"></div>'
                f'      <div style="position:absolute;left:{mp:.1f}%;top:-4px;width:2px;height:14px;'
                f'background:#0891b2;border-radius:1px"></div>'
                f'    </div>'
                f'    <div style="display:flex;justify-content:space-between;margin-top:5px;'
                f'font-family:\'Inter\',sans-serif;font-size:11px;color:#94a3b8">'
                f'      <span>{int(minp):,}₺</span>'
                f'      <span style="color:#0891b2;font-weight:600">{int(medp):,}₺</span>'
                f'      <span>{int(maxp):,}₺</span>'
                f'    </div>'
                f'  </div>'
                f'  <span style="font-family:\'Inter\',sans-serif;font-size:12px;'
                f'color:#94a3b8;text-align:right">{cnt} ISS</span>'
                f'</div>'
            )
        st.markdown(
            '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;'
            'padding:4px 20px 8px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">'
            + "".join(rows) + '</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Son değişimler
    st.markdown(
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#475569;'
        'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">SON DEĞİŞİMLER</div>',
        unsafe_allow_html=True)
    alerts_df = load_alerts(20)
    if alerts_df.empty:
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:20px;'
            'text-align:center;font-size:13px;color:#94a3b8">'
            '✓ &nbsp;Henüz değişim yok</div>', unsafe_allow_html=True)
    else:
        seen = set()
        for _, row in alerts_df.iterrows():
            uid = (row["id"], row.get("diff_alan"))
            if uid in seen or len(seen) >= 8: break
            seen.add(uid)
            render_alert(row, compact=True)


# ── KARŞILAŞTIRMA ─────────────────────────────────────────────────────────────

elif sayfa == "🏆 Karşılaştırma":
    pg_header("SPEED TIER BENCHMARKS", "ISS FİYAT KARŞILAŞTIRMASI")

    df = load_packages()
    if aktif_katlar:
        df = df[df["kategori"].isin(aktif_katlar)]
    if df.empty:
        st.info("Henüz veri yok.")
        st.stop()

    # Hız listesi: sayısal değerler + "5G / Kota" (hiz_mbps=None olanlar)
    _has_5g = df["hiz_mbps"].isna().any() or (df["teknoloji"] == "5g").any()
    hizlar_mevcut = sorted([h for h in df["hiz_mbps"].dropna().unique() if h > 0])
    hiz_secenekler = hizlar_mevcut + (["5G / Kota"] if _has_5g else [])

    fc1, fc2, fc3 = st.columns([2, 2, 2])
    default_idx = hizlar_mevcut.index(100) if 100 in hizlar_mevcut else 0
    secili_hiz  = fc1.selectbox("Hız (Mbps)", hiz_secenekler, index=default_idx)
    tek_filter  = fc2.selectbox("Teknoloji", ["Tümü"] + sorted(df["teknoloji"].dropna().unique().tolist()))
    siralama    = fc3.selectbox("Sırala", ["Ucuzdan Pahalıya", "Pahalıdan Ucuza", "ISS Adı"])

    if secili_hiz == "5G / Kota":
        hiz_df = _fiyatli(df[df["hiz_mbps"].isna() | (df["teknoloji"] == "5g")].copy())
    else:
        hiz_df = _fiyatli(df[df["hiz_mbps"] == secili_hiz].copy())
    if tek_filter != "Tümü":
        hiz_df = hiz_df[hiz_df["teknoloji"] == tek_filter]

    if siralama == "Ucuzdan Pahalıya":
        en_ucuz = hiz_df.sort_values("toplam_aylik").reset_index(drop=True)
    elif siralama == "Pahalıdan Ucuza":
        en_ucuz = hiz_df.sort_values("toplam_aylik", ascending=False).reset_index(drop=True)
    else:
        en_ucuz = hiz_df.sort_values(["iss","toplam_aylik"]).reset_index(drop=True)

    n_iss = en_ucuz["iss"].nunique()
    st.markdown(
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.68em;color:#334155;'
        f'margin-bottom:12px">{n_iss} ISS · {len(en_ucuz)} paket · {int(secili_hiz):,} Mbps kademesi</div>',
        unsafe_allow_html=True)

    RANK_CSS   = {0: "rank-gold", 1: "rank-silver", 2: "rank-bronze"}
    RANK_LABEL = {0: "#1 UCUZ", 1: "#2", 2: "#3"}

    for chunk_start in range(0, len(en_ucuz), 3):
        chunk = en_ucuz.iloc[chunk_start:chunk_start + 3]
        cols  = st.columns(3)
        for col_i, (_, pkg) in enumerate(chunk.iterrows()):
            rank     = chunk_start + col_i
            rank_css = RANK_CSS.get(rank, "")
            rank_lbl = RANK_LABEL.get(rank, f"#{rank+1}")
            fiyat    = pkg["fiyat_ilk_donem"]
            fiyat_str = f"{fiyat:,.0f} ₺" if pd.notna(fiyat) else "—"
            sonraki   = pkg["fiyat_sonraki_donem"]
            ilk_ay    = pkg.get("ilk_donem_ay")
            if pd.notna(sonraki) and sonraki != fiyat:
                ay_str    = f"{int(ilk_ay)}ay → " if pd.notna(ilk_ay) and ilk_ay else ""
                next_html = f'<span class="price-next">{ay_str}{sonraki:,.0f}₺</span>'
            else:
                next_html = ""
            paket_adi  = pkg.get("paket_adi") or ""
            one_cikan  = pkg.get("one_cikan_ifadeler") or ""
            ek         = pkg.get("ek_paketler") or ""
            modem_str  = "📦 Modem ücretsiz" if str(pkg.get("modem","")).lower() == "ucretsiz" else ""
            yeni_str   = "🆕 Sadece yeni müşteri" if pkg.get("sadece_yeni_musteri") else ""
            bolge      = pkg.get("bolge_kisiti") or ""
            kur_badge  = '<span class="badge badge-kur">KRZ</span> ' if _is_kurumsal(paket_adi) else ""
            kat_mono   = (
                f'<span style="font-size:11px;color:#94a3b8;letter-spacing:.04em">'
                f'{_kat_badge(pkg.get("kategori",""))}</span>'
            )
            bolge_html = (
                f'<div style="margin-top:6px;display:inline-block;background:#fef3c7;color:#92400e;'
                f'font-size:11px;font-weight:600;padding:2px 8px;border-radius:100px">📍 {bolge}</div>'
                if bolge else ""
            )
            extras = " · ".join(x for x in [one_cikan, ek, modem_str, yeni_str] if x)
            extras_html = f'<div class="isp-extras">{extras}</div>' if extras else ""

            with cols[col_i]:
                st.markdown(
                    f'<div class="isp-card {rank_css}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">'
                    f'  <div>'
                    f'    <div class="isp-name">{pkg["iss"]}</div>'
                    f'    <div style="margin-top:2px">{kat_mono}'
                    f'    <span style="font-size:11px;font-weight:700;color:#0891b2;margin-left:6px">{rank_lbl}</span></div>'
                    f'  </div>'
                    f'  <div style="text-align:right">'
                    f'    <span class="price-main">{fiyat_str}</span>'
                    f'    <span class="price-unit">/ay</span>'
                    f'    {next_html}'
                    f'  </div>'
                    f'</div>'
                    f'<div class="isp-paket">{paket_adi}</div>'
                    f'{kur_badge}{_tech_badge(pkg.get("teknoloji","belirsiz"))} '
                    f'{_taahhut_badge(pkg.get("sozlesme_suresi_ay",0))}'
                    f'{bolge_html}'
                    f'{extras_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ── TÜM PAKETLER ──────────────────────────────────────────────────────────────

elif sayfa == "📦 Tüm Paketler":
    pg_header("PAKET VERİTABANI", "TÜM AKTİF PAKETLER")

    df = load_packages()
    if aktif_katlar:
        df = df[df["kategori"].isin(aktif_katlar)]
    if df.empty:
        st.info("Henüz veri yok.")
        st.stop()

    with st.expander("⚙  Filtrele", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        tek_secim  = fc1.multiselect("Teknoloji", df["teknoloji"].dropna().unique().tolist())
        hiz_secim  = fc2.multiselect("Hız (Mbps)", sorted(df["hiz_mbps"].dropna().unique().tolist()))
        max_fiyat  = fc3.number_input("Maks. fiyat (₺)", value=int(df["fiyat_ilk_donem"].max() or 2000), step=50)
        sadece_sbt = fc4.checkbox("Sabit fiyatlı")
        taahhut_yok = fc4.checkbox("Taahhütsüz")
        iss_ara    = st.text_input("ISS adı ara")

    filtered = df.copy()
    if tek_secim:   filtered = filtered[filtered["teknoloji"].isin(tek_secim)]
    if hiz_secim:   filtered = filtered[filtered["hiz_mbps"].isin(hiz_secim)]
    if max_fiyat:   filtered = filtered[filtered["fiyat_ilk_donem"] <= max_fiyat]
    if sadece_sbt:  filtered = filtered[filtered["fiyat_sabit_mi"] == 1]
    if taahhut_yok: filtered = filtered[filtered["taahhut_var"] == 0]
    if iss_ara:     filtered = filtered[filtered["iss"].str.contains(iss_ara, case=False, na=False)]

    st.markdown(
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.68em;color:#334155;'
        f'margin-bottom:6px">{len(filtered)} paket</div>', unsafe_allow_html=True)

    filtered["kurumsal"] = filtered["paket_adi"].apply(lambda x: "💼" if _is_kurumsal(x) else "")
    goster = filtered[[
        "iss","paket_adi","kurumsal","hiz_mbps","teknoloji",
        "fiyat_ilk_donem","fiyat_sonraki_donem","sozlesme_suresi_ay",
        "modem","sadece_yeni_musteri","bolge_kisiti","kampanya_bitis","son_guncelleme",
    ]].rename(columns={
        "iss":"ISS","paket_adi":"Paket","kurumsal":"","hiz_mbps":"Hız",
        "teknoloji":"Teknoloji","fiyat_ilk_donem":"Fiyat",
        "fiyat_sonraki_donem":"Sonraki Fiyat","sozlesme_suresi_ay":"Taahhüt(ay)",
        "modem":"Modem","sadece_yeni_musteri":"Sadece Yeni",
        "bolge_kisiti":"Bölge","kampanya_bitis":"Kampanya Bitiş","son_guncelleme":"Güncelleme",
    })

    def _color_by_group(df_in):
        styles = pd.DataFrame("", index=df_in.index, columns=df_in.columns)
        for _, grp in df_in.groupby("Hız"):
            vals = grp["Fiyat"].dropna()
            if len(vals) < 2: continue
            mn, mx = vals.min(), vals.max()
            if mx == mn: continue
            for idx in grp.index:
                v = df_in.at[idx, "Fiyat"]
                if pd.isna(v): continue
                ratio = (v - mn) / (mx - mn)
                r = int(55 + ratio * 170); g = int(180 - ratio * 130)
                styles.at[idx, "Fiyat"] = f"background-color:rgba({r},{g},55,0.2)"
        return styles

    styled = goster.style.apply(_color_by_group, axis=None)
    st.dataframe(_apply_fmt(styled), use_container_width=True, hide_index=True, height=480)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        goster.to_excel(writer, index=False, sheet_name="Paketler")
    st.download_button(
        "⬇  Excel İndir", data=buf.getvalue(),
        file_name=f"rakip_analizi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── ISS PROFİLİ ───────────────────────────────────────────────────────────────

elif sayfa == "🏢 ISS Profili":
    pg_header("ISS PROFİLİ", "DETAYLI ISS ANALİZİ")

    df = load_packages()
    if aktif_katlar:
        df = df[df["kategori"].isin(aktif_katlar)]
    if df.empty:
        st.info("Henüz veri yok.")
        st.stop()

    secili_iss = st.selectbox("ISS seç", sorted(df["iss"].unique().tolist()))
    iss_df  = df[df["iss"] == secili_iss].copy()
    iss_kat = iss_df["kategori"].iloc[0] if not iss_df.empty else ""

    conn = get_conn()
    _isp_row  = conn.execute("SELECT id, url FROM isps WHERE name=?", (secili_iss,)).fetchone()
    if _isp_row:
        _extra_urls = conn.execute(
            "SELECT url, etiket FROM isp_urls WHERE isp_id=? AND aktif=1", (_isp_row["id"],)
        ).fetchall()
        _scrape_urls = [(r["url"], r["etiket"] or "") for r in _extra_urls] or [(_isp_row["url"], "")]
    else:
        _scrape_urls = []
    conn.close()

    _existing_urls = {u for u, _ in _scrape_urls}
    url_chips = " ".join(
        f'<a href="{u}" target="_blank" style="font-family:\'JetBrains Mono\',monospace;'
        f'font-size:0.7em;color:#2fd9f4;background:rgba(47,217,244,0.08);padding:3px 10px;'
        f'border-radius:3px;text-decoration:none;border:1px solid rgba(47,217,244,0.2)">'
        f'↗ {e if e else "site"}</a>'
        for u, e in _scrape_urls
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:16px">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.68em;color:#334155;'
        f'text-transform:uppercase;letter-spacing:.08em">{_kat_badge(iss_kat)}</span>'
        f'<span style="color:#1e293b">│</span>'
        f'{url_chips}</div>',
        unsafe_allow_html=True,
    )

    # Otomatik üst dizin önerisi
    from urllib.parse import urlparse as _urlparse
    _auto = []
    for _u, _ in _scrape_urls:
        _p = _urlparse(_u); _parts = _p.path.rstrip("/").rsplit("/", 1)
        if len(_parts) == 2 and _parts[0]:
            _parent = f"{_p.scheme}://{_p.netloc}{_parts[0]}/"
            if _parent not in _existing_urls and _parent not in _auto:
                _auto.append(_parent)
    if _auto:
        st.markdown(
            '<div style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.2);'
            'border-radius:4px;padding:10px 14px;margin-bottom:12px;font-size:0.82em">'
            '<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.72em;color:#f59e0b;'
            'text-transform:uppercase;letter-spacing:.06em">⚠ Önerilen URL\'ler</span>'
            + "".join(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.8em;'
                      f'color:#64748b;margin-top:4px">• {s}</div>' for s in _auto)
            + '</div>', unsafe_allow_html=True)

    # Tarife keşfi
    _disc_key = f"disc_{secili_iss}"
    btn_col, _ = st.columns([2, 5])
    if btn_col.button("🔍 Tarife sayfalarını keşfet", key="discover_btn"):
        with st.spinner("Taranıyor..."):
            import subprocess, sys, json as _json, os as _os
            _dir = _os.path.dirname(_os.path.abspath(__file__))
            _isp_url = _isp_row["url"] if _isp_row else ""
            _script = (
                f"import sys, json; sys.path.insert(0,{repr(_dir)}); "
                f"from scraper import discover_tariff_urls; "
                f"print(json.dumps(discover_tariff_urls({repr(_isp_url)})))"
            )
            try:
                _proc = subprocess.run([sys.executable,"-c",_script], capture_output=True, text=True, timeout=90)
                st.session_state[_disc_key] = _json.loads(_proc.stdout.strip()) if _proc.stdout.strip() else []
            except Exception as _e:
                st.session_state[_disc_key] = []; st.error(str(_e))

    if _disc_key in st.session_state:
        _found = st.session_state[_disc_key]
        if _found:
            st.markdown(f"**{len(_found)} sayfa bulundu:**")
            _selected = []
            for _u in _found:
                _already = _u in _existing_urls or _u.rstrip("/") in {x.rstrip("/") for x in _existing_urls}
                _label   = f"~~{_u}~~ *(zaten ekli)*" if _already else _u
                if st.checkbox(_label, value=not _already, disabled=_already, key=f"chk_{_u}"):
                    _selected.append(_u)
            if st.button("✅ Seçilenleri ekle", key="add_disc") and _selected:
                from db import add_isp_url
                if not _extra_urls and _isp_row:
                    try: add_isp_url(secili_iss, _isp_row["url"])
                    except: pass
                for _u in _selected:
                    try: add_isp_url(secili_iss, _u)
                    except: pass
                st.success(f"{len(_selected)} URL eklendi.")
                del st.session_state[_disc_key]; st.rerun()
        else:
            st.info("Bulunamadı."); del st.session_state[_disc_key]

    with st.expander("Elle URL ekle"):
        _m_url = st.text_input("URL", placeholder="https://ornek.com/tarifeler/", key="manuel_url")
        _m_et  = st.text_input("Etiket (opsiyonel)", key="manuel_etiket")
        if st.button("Ekle", key="manuel_ekle") and _m_url:
            from db import add_isp_url
            try:
                if not _extra_urls and _isp_row: add_isp_url(secili_iss, _isp_row["url"])
                add_isp_url(secili_iss, _m_url.strip(), _m_et.strip() or None)
                st.success("URL eklendi."); st.rerun()
            except Exception as ex:
                st.error(str(ex))

    st.markdown('<div style="border-top:1px solid #e2e8f0;margin:16px 0"></div>', unsafe_allow_html=True)

    min_f  = iss_df["fiyat_ilk_donem"].min(); max_f = iss_df["fiyat_ilk_donem"].max()
    tekler = sorted(iss_df["teknoloji"].dropna().unique().tolist())
    hiz_df_valid = iss_df[iss_df["hiz_mbps"].notna() & (iss_df["hiz_mbps"] > 0)]
    has_5g = (iss_df["teknoloji"] == "5g").any()
    min_h  = hiz_df_valid["hiz_mbps"].min() if not hiz_df_valid.empty else None
    max_h  = hiz_df_valid["hiz_mbps"].max() if not hiz_df_valid.empty else None
    if min_h and max_h:
        hiz_aralik = f"{int(min_h):,}–{int(max_h):,} Mbps" + (" + 5G" if has_5g else "")
    elif has_5g:
        hiz_aralik = "5G / Kota"
    else:
        hiz_aralik = "—"

    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "📦", str(len(iss_df)),   "Aktif Paket",   "#0891b2")
    metric_card(c2, "💰", f"{min_f:,.0f}–{max_f:,.0f}₺", "Fiyat Aralığı", "#7e22ce")
    metric_card(c3, "⚡", hiz_aralik,          "Hız Aralığı",   "#059669")

    # Teknolojiler — badge listesi (long text taşmaz)
    TEK_BADGE_COLORS = {"fiber":"#e0f2fe|#0369a1","vdsl":"#f3e8ff|#7e22ce",
                        "adsl":"#dcfce7|#15803d","5g":"#fef3c7|#92400e",
                        "belirsiz":"#f1f5f9|#64748b","sabit_kablosuz":"#fee2e2|#b91c1c"}
    tek_badges = " ".join(
        f'<span style="background:{TEK_BADGE_COLORS.get(t,"#f1f5f9|#374151").split("|")[0]};'
        f'color:{TEK_BADGE_COLORS.get(t,"#f1f5f9|#374151").split("|")[1]};'
        f'font-size:11px;font-weight:600;padding:2px 8px;border-radius:100px;'
        f'white-space:nowrap">{t}</span>'
        for t in tekler
    ) if tekler else "—"
    c4.markdown(
        f'<div class="m-card" style="border-top:2px solid #f59e0b">'
        f'<div class="m-icon">🔧</div>'
        f'<div class="m-label">Teknolojiler</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">{tek_badges}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#475569;'
            'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">PAKETLER</div>',
            unsafe_allow_html=True)
        g = iss_df[["paket_adi","hiz_mbps","teknoloji","fiyat_ilk_donem",
                    "fiyat_sonraki_donem","sozlesme_suresi_ay","modem",
                    "bolge_kisiti","kampanya_bitis"]].copy().rename(columns={
            "paket_adi":"Paket","hiz_mbps":"Hız","teknoloji":"Teknoloji",
            "fiyat_ilk_donem":"Fiyat","fiyat_sonraki_donem":"Sonraki Fiyat",
            "sozlesme_suresi_ay":"Taahhüt(ay)","modem":"Modem",
            "bolge_kisiti":"Bölge","kampanya_bitis":"Kampanya Bitiş"})
        # 5G paketlerinde hız "5G" olarak göster
        g["Hız"] = g.apply(
            lambda r: "5G" if (pd.isna(r["Hız"]) and r["Teknoloji"] == "5g")
                      else r["Hız"], axis=1
        )
        styled_g = g.style.apply(_grad_style, subset=["Fiyat"]) if len(g) > 1 else g.style
        st.dataframe(_apply_fmt(styled_g), use_container_width=True, hide_index=True)
        if len(iss_df) > 1:
            chart_df = iss_df[iss_df["hiz_mbps"].notna() & iss_df["fiyat_ilk_donem"].notna()].sort_values("hiz_mbps")[[
                "hiz_mbps","fiyat_ilk_donem"]].rename(columns={"hiz_mbps":"Hız (Mbps)","fiyat_ilk_donem":"Fiyat (₺)"})
            st.scatter_chart(chart_df, x="Hız (Mbps)", y="Fiyat (₺)", height=200)

    with col_right:
        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#475569;'
            'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">SON DEĞİŞİMLER</div>',
            unsafe_allow_html=True)
        alerts_df = load_alerts(300)
        iss_alerts = alerts_df[alerts_df["iss"] == secili_iss]
        if iss_alerts.empty:
            st.markdown(
                '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;'
                'text-align:center;font-size:13px;color:#94a3b8">'
                '✓ &nbsp;Bu ISS için değişim kaydı yok</div>', unsafe_allow_html=True)
        else:
            for row_dict in list(_dedup_alerts(iss_alerts).values())[:15]:
                render_alert(row_dict)


# ── BİLDİRİMLER ───────────────────────────────────────────────────────────────

elif sayfa == "🔔 Bildirimler":
    pg_header("DEĞİŞİM BİLDİRİMLERİ", "COMPETITIVE ALERTS FEED")

    alerts_df = load_alerts(200)
    if aktif_katlar:
        alerts_df = alerts_df[alerts_df["kategori"].isin(aktif_katlar)]

    col1, col2 = st.columns([3, 1])
    with col1:
        tur_filter = st.multiselect("Tür filtrele", [
            "fiyat_dustu","fiyat_yukseldi","yeni_paket","paket_kaldirildi","icerik_degisim"])
    with col2:
        st.write("")
        if st.button("Tümünü okundu"):
            mark_all_read(); st.rerun()

    if tur_filter:
        alerts_df = alerts_df[alerts_df["tur"].isin(tur_filter)]

    if alerts_df.empty:
        st.markdown(
            '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:36px;'
            'text-align:center">'
            '<div style="font-size:24px;margin-bottom:8px">✓</div>'
            '<div style="font-size:14px;font-weight:600;color:#059669">Tüm sistemler normal</div>'
            '<div style="font-size:12px;color:#86efac;margin-top:4px">Bildirim bulunmuyor</div>'
            '</div>',
            unsafe_allow_html=True)
    else:
        for row_dict in _dedup_alerts(alerts_df).values():
            render_alert(row_dict)

        st.markdown('<div style="border-top:1px solid #1e293b;margin:20px 0 12px"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#475569;'
            'text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">PAKET DEĞİŞİM GEÇMİŞİ</div>',
            unsafe_allow_html=True)
        secili_key = st.text_input("Paket key")
        if secili_key:
            hist = load_history(secili_key)
            if hist.empty:
                st.info("Bu paket için geçmiş kaydı yok.")
            else:
                st.dataframe(hist, use_container_width=True, hide_index=True)


# ── FİYAT TRENDİ ──────────────────────────────────────────────────────────────

elif sayfa == "📈 Fiyat Trendi":
    pg_header("FİYAT TRENDİ", "TARİHSEL FİYAT ANALİZİ")
    st.markdown(
        '<div style="background:rgba(47,217,244,0.05);border:1px solid rgba(47,217,244,0.15);'
        'border-radius:4px;padding:10px 14px;font-family:\'JetBrains Mono\',monospace;'
        'font-size:0.75em;color:#475569;margin-bottom:16px">'
        'ℹ Veri birikmesi için sistemin bir süre çalışması gerekir.</div>',
        unsafe_allow_html=True)

    conn = get_conn()
    iss_listesi = [r[0] for r in conn.execute(
        "SELECT DISTINCT i.name FROM package_history ph "
        "JOIN packages p ON p.paket_key=ph.paket_key "
        "JOIN isps i ON i.id=p.isp_id ORDER BY i.name"
    ).fetchall()]
    conn.close()

    if not iss_listesi:
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:32px;'
            'text-align:center;font-size:13px;color:#94a3b8">'
            '📈 &nbsp;Henüz fiyat geçmişi yok — sistem bir süre çalıştıktan sonra burada görünecek</div>',
            unsafe_allow_html=True)
        st.stop()

    c1, c2 = st.columns(2)
    secili_iss = c1.selectbox("ISS", iss_listesi)
    conn2 = get_conn()
    hizlar = [r[0] for r in conn2.execute(
        "SELECT DISTINCT p.hiz_mbps FROM packages p JOIN isps i ON i.id=p.isp_id "
        "WHERE i.name=? ORDER BY p.hiz_mbps", (secili_iss,)
    ).fetchall()]
    conn2.close()
    secili_hiz = c2.selectbox("Hız (Mbps)", hizlar)

    trend = load_price_trend(secili_iss, secili_hiz)
    if trend.empty:
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:24px;'
            'text-align:center;font-size:13px;color:#94a3b8">'
            '📈 &nbsp;Bu paket için henüz fiyat değişimi kaydedilmedi</div>',
            unsafe_allow_html=True)
    else:
        trend["tarih"] = pd.to_datetime(trend["tarih"])
        st.line_chart(trend.set_index("tarih")["fiyat"])
        st.dataframe(trend, use_container_width=True, hide_index=True)
