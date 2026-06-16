import streamlit as st
import pandas as pd
import json
import re as _re
import numpy as _np
from datetime import datetime
from db import get_conn
try:
    import altair as alt
    _HAS_ALTAIR = True
except ImportError:
    _HAS_ALTAIR = False

st.set_page_config(
    page_title="ISP INTEL",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    '<script>setTimeout(function(){window.location.reload();}, 60000);</script>',
    unsafe_allow_html=True,
)
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
    '&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown("""
<style>
/* ── RESET & BASE ── */
html, body, .stApp {
  background: #0a0f12 !important;
  font-family: 'Inter', sans-serif !important;
  color: #e2e8f0 !important;
}
[data-testid="stAppViewContainer"] { background: #0a0f12 !important; }
[data-testid="stHeader"] { background: transparent !important; display:none; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
p, span, li, label { color: #e2e8f0 !important; font-family: 'Inter', sans-serif !important; }
h1,h2,h3,h4 { color: #f8fafc !important; }
.block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
  background: #0d1520 !important;
  border-right: 1px solid #1e2d3d !important;
  min-width: 200px !important;
  max-width: 200px !important;
}
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] hr { border-color: #1e2d3d !important; margin: 6px 12px !important; }

/* Nav radio: genel label gizle */
[data-testid="stSidebar"] .stRadio > label { display: none !important; }

/* Radio circle / görsel indicator'ı tamamen gizle */
[data-testid="stSidebar"] [data-baseweb="radio"] { display: none !important; }

/* Nav item container */
[data-testid="stSidebar"] .stRadio > div { gap: 0 !important; padding: 0 !important; }

/* Her nav item */
[data-testid="stSidebar"] .stRadio label {
  display: flex !important; align-items: center !important;
  background: transparent !important; border: none !important;
  border-radius: 8px !important; padding: 10px 14px !important;
  color: #64748b !important; font-size: 13px !important;
  font-weight: 500 !important; width: calc(100% - 16px) !important;
  transition: background 0.15s, color 0.15s !important;
  cursor: pointer !important; margin: 1px 8px !important;
  white-space: nowrap !important; overflow: hidden !important;
  text-overflow: ellipsis !important;
}
[data-testid="stSidebar"] .stRadio label p {
  white-space: nowrap !important; overflow: hidden !important;
  text-overflow: ellipsis !important; margin: 0 !important;
  font-size: 13px !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: #1a2d3d !important; color: #e2e8f0 !important;
}
/* Aktif nav item — :has() modern browser */
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: rgba(76,215,246,0.12) !important; color: #4cd7f6 !important;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) p {
  color: #4cd7f6 !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {
  background: #0f1d2a !important; border-color: #1e2d3d !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
  background: rgba(76,215,246,0.15) !important; color: #4cd7f6 !important;
}
[data-testid="stSidebar"] .stButton button {
  background: #0f1d2a !important; border: 1px solid #1e2d3d !important;
  color: #94a3b8 !important; border-radius: 8px !important;
  font-size: 12px !important;
}
[data-testid="stSidebar"] .stButton button:hover {
  border-color: #4cd7f6 !important; color: #4cd7f6 !important;
}
[data-testid="stSidebar"] p { color: #94a3b8 !important; }

/* ── MAIN AREA ── */
.main-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 24px; padding-bottom: 16px;
  border-bottom: 1px solid #1e2d3d;
}
.main-header h1 {
  font-size: 22px !important; font-weight: 700 !important;
  color: #f8fafc !important; margin: 0 !important;
  letter-spacing: 0.04em !important; text-transform: uppercase !important;
}
.main-header .subtitle {
  font-size: 12px !important; color: #4cd7f6 !important;
  text-transform: uppercase; letter-spacing: 0.1em;
}

/* ── METRIC CARDS ── */
.m-card {
  background: #0d1520; border: 1px solid #1e2d3d;
  border-radius: 12px; padding: 20px 18px;
  min-height: 100px; position: relative;
}
.m-card:hover { border-color: #2d4a6a; }
.m-label {
  font-size: 11px; color: #64748b; text-transform: uppercase;
  letter-spacing: 0.1em; font-weight: 600; margin-bottom: 8px;
}
.m-value {
  font-size: 32px; font-weight: 700; line-height: 1;
  font-family: 'JetBrains Mono', monospace;
}
.m-sub { font-size: 12px; color: #64748b; margin-top: 6px; }
.m-accent-bar {
  position: absolute; top: 0; left: 0; right: 0;
  height: 2px; border-radius: 12px 12px 0 0;
}

/* ── ALERT CARDS ── */
.alert-card {
  background: #0d1520; border: 1px solid #1e2d3d;
  border-left: 3px solid #1e2d3d;
  border-radius: 10px; padding: 14px 16px;
  margin-bottom: 8px; display: flex; align-items: flex-start; gap: 14px;
}
.alert-card:hover { border-color: #2d4a6a; border-left-color: inherit; }
.alert-down  { border-left-color: #4edea3 !important; }
.alert-up    { border-left-color: #f87171 !important; }
.alert-new   { border-left-color: #fbbf24 !important; }
.alert-rem   { border-left-color: #64748b !important; }
.isp-badge {
  width: 40px; height: 40px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
}
.alert-body { flex: 1; min-width: 0; }
.alert-title { font-size: 13px; font-weight: 600; color: #e2e8f0; }
.alert-desc { font-size: 12px; color: #64748b; margin-top: 2px; }
.alert-time { font-size: 11px; color: #475569; margin-top: 4px; }
.price-change {
  font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace;
  white-space: nowrap; flex-shrink: 0;
}
.price-down { color: #4edea3; }
.price-up   { color: #f87171; }
.price-new  { color: #fbbf24; }
.price-rem  { color: #94a3b8; }

/* ── TECH BADGES ── */
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
}
.badge-fiber { background: rgba(76,215,246,0.15); color: #4cd7f6; }
.badge-vdsl  { background: rgba(251,191,36,0.15);  color: #fbbf24; }
.badge-adsl  { background: rgba(148,163,184,0.15); color: #94a3b8; }
.badge-5g    { background: rgba(167,139,250,0.15); color: #a78bfa; }
.badge-other { background: rgba(148,163,184,0.15); color: #94a3b8; }
.badge-free  { background: rgba(78,222,163,0.15);  color: #4edea3; }
.badge-taah  { background: rgba(251,191,36,0.15);  color: #fbbf24; }

/* ── TABLES ── */
[data-testid="stDataFrame"] {
  background: #0d1520 !important; border: 1px solid #1e2d3d !important;
  border-radius: 8px !important;
}
.stDataFrame th {
  background: #0f1d2a !important; color: #94a3b8 !important;
  font-size: 11px !important; text-transform: uppercase !important;
  letter-spacing: 0.06em !important; border-color: #1e2d3d !important;
}
.stDataFrame td {
  background: #0d1520 !important; color: #e2e8f0 !important;
  border-color: #1e2d3d !important; font-size: 13px !important;
}
.stDataFrame tr:hover td { background: #111f2e !important; }

/* ── CHARTS ── */
.vega-embed { background: transparent !important; }

/* ── BUTTONS (global) ── */
.stButton button {
  background: #0f1d2a !important; border: 1px solid #1e2d3d !important;
  color: #94a3b8 !important; border-radius: 8px !important;
  font-size: 13px !important; font-weight: 500 !important;
}
.stButton button:hover {
  border-color: #4cd7f6 !important; color: #4cd7f6 !important;
  background: rgba(76,215,246,0.08) !important;
}

/* ── SELECTBOX / MULTISELECT ── */
/* Tetikleyici kutu */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div:focus-within {
  background: #0d1520 !important; border-color: #1e2d3d !important;
  color: #e2e8f0 !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] div { color: #e2e8f0 !important; }
[data-baseweb="select"] input { color: #e2e8f0 !important; background: transparent !important; }
[data-baseweb="tag"] { background: rgba(76,215,246,0.15) !important; color: #4cd7f6 !important; }

/* ── DROPDOWN PORTAL (body'e doğrudan açılır) ── */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] > div > div {
  background: #0f1a26 !important;
  border: 1px solid #1e2d3d !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.7) !important;
}
[data-baseweb="menu"],
[data-baseweb="menu"] > div,
[data-baseweb="menu"] ul {
  background: #0f1a26 !important;
  border: none !important;
}
/* Her seçenek */
[role="option"] {
  background: #0f1a26 !important;
  color: #94a3b8 !important;
  font-size: 13px !important;
}
[role="option"]:hover,
[role="option"]:focus,
[aria-selected="true"][role="option"] {
  background: #1a2d3d !important;
  color: #e2e8f0 !important;
}
/* Listbox container */
[role="listbox"] {
  background: #0f1a26 !important;
}
/* Multiselect arama input'u */
[data-baseweb="popover"] input,
[data-baseweb="popover"] input::placeholder {
  background: #0f1a26 !important;
  color: #64748b !important;
}
/* Slider */
[data-testid="stSlider"] [role="slider"] { background: #4cd7f6 !important; }
[data-testid="stSlider"] [data-testid="stTickBar"] { color: #64748b !important; }
/* Text input */
[data-testid="stTextInput"] input {
  background: #0d1520 !important; border-color: #1e2d3d !important;
  color: #e2e8f0 !important;
}
[data-testid="stTextInput"] input {
  background: #0d1520 !important; border-color: #1e2d3d !important;
  color: #e2e8f0 !important;
}
.stSlider [data-testid="stThumbValue"] { color: #4cd7f6 !important; }
.stSlider [data-baseweb="slider"] div[role="slider"] { background: #4cd7f6 !important; }
[data-testid="stCheckbox"] label { color: #e2e8f0 !important; }

/* ── SECTION HEADERS ── */
.section-title {
  font-size: 13px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.1em;
  margin: 20px 0 12px; padding-bottom: 8px;
  border-bottom: 1px solid #1e2d3d;
}

/* ── TIER CARD (Hız Kırılım) ── */
.tier-detail {
  max-height: 0; opacity: 0; overflow: hidden;
  transition: max-height 0.25s ease, opacity 0.2s ease, margin-top 0.2s ease;
}
.tier-card:hover .tier-detail {
  max-height: 60px; opacity: 1; margin-top: 6px;
}

/* ── PACKAGE CARD (Karsilastirma) ── */
.pkg-card {
  background: #0d1520; border: 1px solid #1e2d3d;
  border-radius: 12px; padding: 16px;
  transition: border-color 0.15s; height: 100%;
}
.pkg-card:hover { border-color: #2d4a6a; }
.pkg-iss { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; }
.pkg-price { font-size: 28px; font-weight: 700; color: #4cd7f6; font-family: 'JetBrains Mono', monospace; }
.pkg-price-sub { font-size: 11px; color: #475569; }
.pkg-name { font-size: 12px; color: #94a3b8; margin-top: 8px; }
.rank-gold   { border-top: 3px solid #fbbf24 !important; }
.rank-silver { border-top: 3px solid #94a3b8 !important; }
.rank-bronze { border-top: 3px solid #cd7c3a !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0f12; }
::-webkit-scrollbar-thumb { background: #1e2d3d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2d4a6a; }
</style>
""", unsafe_allow_html=True)

# ── YARDIMCI FONKSİYONLAR ─────────────────────────────────────────────────────

_KURUMSAL_KW = ["kobi","kobı","işyeri","is yeri","esnaf","kurumsal","ticari",
    "ofis","business","metro ethernet","simetri","prime","elite","vip","gurbetçi","diaspora"]

def _is_kurumsal(paket_adi): return any(k in str(paket_adi).lower() for k in _KURUMSAL_KW)

def _fmt_fiyat(v):
    if pd.isna(v) or v == 0: return "—"
    return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"

def _fmt_hiz(v):
    if pd.isna(v) or v == "" or v == 0: return "—"
    try: return f"{int(v):,}"
    except (ValueError, TypeError): return str(v)

def _tech_badge(tek):
    t = str(tek).lower()
    css = {"fiber":"badge-fiber","vdsl":"badge-vdsl","adsl":"badge-adsl","5g":"badge-5g"}.get(t,"badge-other")
    return f'<span class="badge {css}">{str(tek).upper()}</span>'

def _taahhut_badge(ay):
    try: ay = int(ay)
    except: ay = 0
    if ay == 0: return '<span class="badge badge-free">TAAHHÜTSÜZ</span>'
    return f'<span class="badge badge-taah">{ay}AY</span>'

def _fiyatli(df): return df[df["fiyat_ilk_donem"].notna() & (df["fiyat_ilk_donem"] > 0)]

def _isp_badge_color(name):
    colors = ["#1a3a5c","#1a3d2e","#3d1a2e","#2e2a1a","#1a2e3d","#2e1a3d","#3d2e1a","#1a3d3a"]
    idx = sum(ord(c) for c in str(name)) % len(colors)
    return colors[idx]

def _isp_abbr(name):
    parts = str(name).upper().split()
    if len(parts) >= 2: return parts[0][0] + parts[1][0]
    return str(name).upper()[:2]

def _time_ago(ts_str):
    try:
        ts = datetime.strptime(str(ts_str)[:19], "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - ts
        mins = int(diff.total_seconds() / 60)
        if mins < 60: return f"{mins} dk önce"
        if mins < 1440: return f"{mins//60} sa önce"
        return f"{mins//1440} gün önce"
    except: return str(ts_str)[:16]

def _dedup_alerts(df):
    shown = {}
    for _, row in df.iterrows():
        aid = row["id"]
        if aid not in shown: shown[aid] = row.to_dict()
        elif not shown[aid].get("eski_deger") and row.get("eski_deger"):
            shown[aid]["eski_deger"] = row["eski_deger"]
            shown[aid]["yeni_deger"] = row["yeni_deger"]
    return shown

# ── VERİ FONKSİYONLARI ───────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_stats(kategoriler=()):
    conn = get_conn()
    def q(sql, params=()):
        r = conn.execute(sql, list(params)).fetchone()
        return r[0] if r else 0
    s = {}
    if kategoriler:
        ph = ",".join("?"*len(kategoriler)); k = list(kategoriler)
        s["toplam_iss"]    = q(f"SELECT COUNT(DISTINCT p.isp_id) FROM packages p JOIN isps i ON i.id=p.isp_id WHERE p.aktif=1 AND i.aktif=1 AND i.kategori IN ({ph})", k)
        s["toplam_paket"]  = q(f"SELECT COUNT(*) FROM packages p JOIN isps i ON i.id=p.isp_id WHERE p.aktif=1 AND i.aktif=1 AND i.kategori IN ({ph})", k)
        s["yeni_alert"]    = q(f"SELECT COUNT(*) FROM alerts a JOIN isps i ON i.id=a.isp_id WHERE a.goruldu=0 AND i.kategori IN ({ph})", k)
        s["degisim_bugun"] = q(f"SELECT COUNT(DISTINCT ph.isp_id) FROM package_history ph JOIN isps i ON i.id=ph.isp_id WHERE date(ph.degisim_zamani)=date('now','localtime') AND i.kategori IN ({ph})", k)
        for tur, key in [("fiyat_dustu","fd"),("fiyat_yukseldi","fy"),("yeni_paket","yp"),("paket_kaldirildi","pk")]:
            s[key] = q(f"SELECT COUNT(*) FROM alerts a JOIN isps i ON i.id=a.isp_id WHERE a.tur=? AND a.olusma_zamani>=datetime('now','-7 days','localtime') AND i.kategori IN ({ph})", [tur]+k)
    else:
        s["toplam_iss"]    = q("SELECT COUNT(DISTINCT isp_id) FROM packages WHERE aktif=1")
        s["toplam_paket"]  = q("SELECT COUNT(*) FROM packages WHERE aktif=1")
        s["yeni_alert"]    = q("SELECT COUNT(*) FROM alerts WHERE goruldu=0")
        s["degisim_bugun"] = q("SELECT COUNT(DISTINCT isp_id) FROM package_history WHERE date(degisim_zamani)=date('now','localtime')")
        for tur, key in [("fiyat_dustu","fd"),("fiyat_yukseldi","fy"),("yeni_paket","yp"),("paket_kaldirildi","pk")]:
            s[key] = q("SELECT COUNT(*) FROM alerts WHERE tur=? AND olusma_zamani>=datetime('now','-7 days','localtime')", (tur,))
    s["son_kontrol"] = conn.execute("SELECT value FROM meta WHERE key='last_run_ts'").fetchone()
    s["son_kontrol"] = s["son_kontrol"][0] if s["son_kontrol"] else "—"
    conn.close()
    return s

@st.cache_data(ttl=60)
def load_packages():
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT i.name AS iss, i.kategori,
               p.paket_adi, p.hiz_mbps, p.teknoloji,
               p.fiyat_ilk_donem, p.fiyat_sonraki_donem, p.ilk_donem_ay,
               p.fiyat_sabit_mi, p.sozlesme_suresi_ay, p.taahhut_var,
               p.modem, p.modem_ucreti_aylik, p.sadece_yeni_musteri,
               p.kurulum_ucreti, p.one_cikan_ifadeler, p.ek_paketler,
               p.bolge_kisiti, p.kampanya_bitis, p.son_guncelleme, p.paket_key
        FROM packages p JOIN isps i ON i.id=p.isp_id
        WHERE p.aktif=1 AND i.aktif=1
        ORDER BY p.hiz_mbps, p.fiyat_ilk_donem
    """, conn)
    conn.close()
    df["one_cikan_ifadeler"] = df["one_cikan_ifadeler"].apply(lambda x: ", ".join(json.loads(x)) if x and x!="[]" else "")
    df["ek_paketler"]        = df["ek_paketler"].apply(lambda x: ", ".join(json.loads(x)) if x and x!="[]" else "")
    df["toplam_aylik"]       = df.apply(lambda r: (r["fiyat_ilk_donem"] or 0)+(r["modem_ucreti_aylik"] or 0) if pd.notna(r["fiyat_ilk_donem"]) and r["fiyat_ilk_donem"]>0 else None, axis=1)
    def _spd(row):
        if pd.notna(row["hiz_mbps"]) and row["hiz_mbps"]>0: return row["hiz_mbps"]
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
def load_alerts(limit=200):
    conn = get_conn()
    df = pd.read_sql_query(f"""
        SELECT a.id, i.name AS iss, i.kategori,
               COALESCE((SELECT iu.url FROM isp_urls iu WHERE iu.isp_id=i.id AND iu.aktif=1 ORDER BY iu.id LIMIT 1), i.url) AS isp_url,
               a.paket_key, a.tur, a.mesaj, a.olusma_zamani, a.goruldu,
               ph.alan AS diff_alan, ph.eski_deger, ph.yeni_deger
        FROM alerts a JOIN isps i ON i.id=a.isp_id
        LEFT JOIN package_history ph ON ph.paket_key=a.paket_key
            AND ph.alan IN ('fiyat_ilk_donem','fiyat_sonraki_donem','modem','sozlesme_suresi_ay')
            AND ph.degisim_zamani=(SELECT MAX(ph2.degisim_zamani) FROM package_history ph2 WHERE ph2.paket_key=a.paket_key AND ph2.alan=ph.alan)
        ORDER BY a.olusma_zamani DESC LIMIT {limit}
    """, conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_history(paket_key):
    conn = get_conn()
    df = pd.read_sql_query("SELECT degisim_zamani, alan, eski_deger, yeni_deger, aciklama FROM package_history WHERE paket_key=? ORDER BY degisim_zamani DESC LIMIT 50", conn, params=(paket_key,))
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_price_trend(isp_name, hiz):
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT ph.degisim_zamani AS tarih, CAST(ph.yeni_deger AS REAL) AS fiyat
        FROM package_history ph JOIN packages p ON p.paket_key=ph.paket_key
        JOIN isps i ON i.id=p.isp_id
        WHERE i.name=? AND p.hiz_mbps=? AND ph.alan='fiyat_ilk_donem'
        ORDER BY ph.degisim_zamani
    """, conn, params=(isp_name, hiz))
    conn.close()
    return df

def mark_all_read():
    conn = get_conn()
    conn.execute("UPDATE alerts SET goruldu=1 WHERE goruldu=0")
    conn.commit(); conn.close()
    st.cache_data.clear()

# ── ALERT KARTI ──────────────────────────────────────────────────────────────

def render_alert_card(row):
    tur = row.get("tur","")
    iss = row.get("iss","?")
    mesaj = row.get("mesaj","")
    zaman = _time_ago(row.get("olusma_zamani",""))
    eski = row.get("eski_deger")
    yeni = row.get("yeni_deger")
    color = _isp_badge_color(iss)
    abbr  = _isp_abbr(iss)

    border_cls = ""
    if tur == "fiyat_dustu":
        border_cls = "alert-down"
        try:
            diff = float(yeni or 0) - float(eski or 0)
            price_html = f'<div class="price-change price-down">{diff:+,.0f} TL</div>'
            desc = f"Fiyat güncellendi · {_fmt_fiyat(float(eski or 0))} → {_fmt_fiyat(float(yeni or 0))} TL"
        except:
            price_html = '<div class="price-change price-down">↓</div>'
            desc = mesaj
    elif tur == "fiyat_yukseldi":
        border_cls = "alert-up"
        try:
            diff = float(yeni or 0) - float(eski or 0)
            price_html = f'<div class="price-change price-up">+{abs(diff):,.0f} TL</div>'
            desc = f"Fiyat revizyonu · {_fmt_fiyat(float(eski or 0))} → {_fmt_fiyat(float(yeni or 0))} TL"
        except:
            price_html = '<div class="price-change price-up">↑</div>'
            desc = mesaj
    elif tur == "yeni_paket":
        border_cls = "alert-new"
        price_html = '<div class="price-change price-new">YENİ</div>'
        desc = mesaj
    elif tur == "paket_kaldirildi":
        border_cls = "alert-rem"
        price_html = '<div class="price-change price-rem">KALDIRILDI</div>'
        desc = mesaj
    else:
        price_html = ""
        desc = mesaj

    # Paket adını mesajdan çıkar
    title = mesaj.split("·")[0].strip() if "·" in mesaj else (mesaj[:60] + "..." if len(mesaj) > 60 else mesaj)

    goruldu_dot = "" if row.get("goruldu") else '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#4cd7f6;margin-left:6px;vertical-align:middle;"></span>'

    st.markdown(f"""
    <div class="alert-card {border_cls}">
      <div class="isp-badge" style="background:{color};color:#e2e8f0;">{abbr}</div>
      <div class="alert-body">
        <div class="alert-title">{iss}{goruldu_dot}</div>
        <div class="alert-desc">{desc}</div>
        <div class="alert-time">{zaman}</div>
      </div>
      {price_html}
    </div>
    """, unsafe_allow_html=True)

# ── SİDEBAR ──────────────────────────────────────────────────────────────────

KAT_LABEL = {"rakip": "🏢 Büyük ve Rakip", "diger": "🌐 Diğer"}

with st.sidebar:
    st.markdown("""
    <div style="padding:20px 16px 12px;">
      <div style="font-size:18px;font-weight:800;color:#4cd7f6;letter-spacing:0.1em;">ISP INTEL</div>
      <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.12em;margin-top:2px;">Market Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    sayfa = st.radio("", [
        "Genel Bakış",
        "Karşılaştırma",
        "Tüm Paketler",
        "ISS Profili",
        "Bildirimler",
        "Fiyat Trendi",
    ], label_visibility="collapsed")

    st.divider()
    st.markdown('<p style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.1em;padding:4px 16px 4px;">ISS FİLTRE</p>', unsafe_allow_html=True)
    kat_filtre = st.multiselect("", ["🏢 Büyük ve Rakip","🌐 Diğer"],
        default=["🏢 Büyük ve Rakip","🌐 Diğer"], label_visibility="collapsed")
    _kat_secim = {v: k for k, v in KAT_LABEL.items()}
    aktif_katlar = [_kat_secim[l] for l in kat_filtre if l in _kat_secim]

    st.divider()

    if st.button("⟳ Yenile", use_container_width=True):
        st.cache_data.clear(); st.rerun()

    stats = get_stats(tuple(aktif_katlar) if aktif_katlar else ())
    son_k = str(stats.get("son_kontrol","—"))
    son_k_fmt = son_k[-8:] if son_k != "—" else "—"
    st.markdown(f'<p style="text-align:center;margin-top:8px;">{son_k_fmt}</p>', unsafe_allow_html=True)

# ── SAYFA: GENEL BAKIŞ ───────────────────────────────────────────────────────

df_all = load_packages()
if aktif_katlar:
    df = df_all[df_all["kategori"].isin(aktif_katlar)]
else:
    df = df_all.copy()

if sayfa == "Genel Bakış":
    st.markdown("""
    <div class="main-header">
      <div>
        <div class="subtitle">Real-Time Competitive Intelligence</div>
        <h1>GENEL BAKIŞ</h1>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Metrik kartlar
    c1,c2,c3,c4,c5 = st.columns(5)
    cards = [
        (c1, "Aktif ISS",    stats["toplam_iss"],    "#4cd7f6"),
        (c2, "Aktif Paket",  stats["toplam_paket"],  "#a78bfa"),
        (c3, "Okunmamış Alert", stats["yeni_alert"], "#f87171"),
        (c4, "Bugün Değişen", stats["degisim_bugun"],"#fbbf24"),
        (c5, "Son Kontrol",  son_k_fmt,              "#64748b"),
    ]
    for col, label, val, color in cards:
        col.markdown(f"""
        <div class="m-card">
          <div class="m-accent-bar" style="background:{color};"></div>
          <div class="m-label">{label}</div>
          <div class="m-value" style="color:{color};">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # 7 günlük özet
    badges = [
        (stats.get("fd",0), "↓ Fiyat Düştü",   "#4edea3", "rgba(78,222,163,0.12)"),
        (stats.get("fy",0), "↑ Fiyat Yükseldi","#f87171",  "rgba(248,113,113,0.12)"),
        (stats.get("yp",0), "+ Yeni Paket",     "#fbbf24",  "rgba(251,191,36,0.12)"),
        (stats.get("pk",0), "✕ Kaldırıldı",    "#94a3b8",  "rgba(148,163,184,0.12)"),
    ]
    cols = st.columns([1,3])
    with cols[0]:
        st.markdown('<div class="section-title">Son 7 Gün</div>', unsafe_allow_html=True)
        badge_html = ""
        for cnt, label, color, bg in badges:
            badge_html += f'<span style="display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:20px;background:{bg};color:{color};font-size:12px;font-weight:600;margin:3px 3px;">{cnt} {label}</span>'
        st.markdown(badge_html, unsafe_allow_html=True)

    st.markdown("")

    # Tüm fiyatlı paketler (sidebar filtresi uygulanmış)
    df_fiy = _fiyatli(df)

    # Scatter: önce rakip ISS → az, temiz nokta; yoksa tüm filtrelenmiş
    df_sc_base = df_fiy[df_fiy["hiz_mbps"].notna() & (df_fiy["hiz_mbps"] <= 1200) & ~df_fiy["paket_adi"].apply(_is_kurumsal)].copy()
    df_rakip_sc = df_sc_base[df_sc_base["kategori"] == "rakip"]
    df_scatter  = (df_rakip_sc if len(df_rakip_sc) >= 3 else df_sc_base).copy()
    df_scatter["hiz_mbps"] = df_scatter["hiz_mbps"].astype(float)

    # Range bars da scatter ile aynı kaynak: sidebar filtresi + kurumsal hariç
    df_range = df_sc_base.copy()  # sidebar filtresi zaten uygulanmış

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <div>
            <div style="font-size:15px;font-weight:600;color:#e2e8f0;">Hız & Fiyat Dağılımı</div>
            <div style="font-size:11px;color:#475569;margin-top:2px;">Piyasadaki tüm aktif paketlerin Mbps başı maliyet analizi</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        if _HAS_ALTAIR and not df_scatter.empty:
            scatter = alt.Chart(df_scatter).mark_circle(size=100, opacity=0.85).encode(
                x=alt.X("hiz_mbps:Q", title="Hız (Mbps)",
                        axis=alt.Axis(labelColor="#64748b", titleColor="#64748b", gridColor="#1e2d3d", tickCount=6)),
                y=alt.Y("fiyat_ilk_donem:Q", title="Fiyat (TL)",
                        axis=alt.Axis(labelColor="#64748b", titleColor="#64748b", gridColor="#1e2d3d")),
                color=alt.Color("teknoloji:N", scale=alt.Scale(
                    domain=["fiber","vdsl","adsl","5g","belirsiz"],
                    range=["#4cd7f6","#fbbf24","#94a3b8","#a78bfa","#475569"]),
                    legend=None),
                tooltip=["iss","paket_adi","hiz_mbps","fiyat_ilk_donem","teknoloji"],
            )
            # Trend line — Python'da hesapla, Vega-Lite transform yok
            x_vals = df_scatter["hiz_mbps"].values.astype(float)
            y_vals = df_scatter["fiyat_ilk_donem"].values.astype(float)
            valid  = _np.isfinite(x_vals) & _np.isfinite(y_vals)
            layers = [scatter]
            if valid.sum() >= 4:
                try:
                    coeffs  = _np.polyfit(x_vals[valid], y_vals[valid], 2)
                    x_line  = _np.linspace(x_vals[valid].min(), x_vals[valid].max(), 80)
                    y_line  = _np.polyval(coeffs, x_line)
                    df_tr   = pd.DataFrame({"hiz_mbps": x_line, "fiyat_ilk_donem": y_line})
                    trend_c = alt.Chart(df_tr).mark_line(color="#4cd7f6", opacity=0.5, strokeWidth=2).encode(
                        x=alt.X("hiz_mbps:Q"), y=alt.Y("fiyat_ilk_donem:Q"))
                    layers = [trend_c, scatter]
                except Exception:
                    pass
            chart = alt.layer(*layers).properties(height=310).interactive().configure(background="transparent").configure_view(
                strokeOpacity=0, strokeWidth=0).configure_axis(domainColor="#1e2d3d", domainWidth=1)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Veri yok.")

    with col_r:
        # Hız Kırılım Analizi — sidebar filtresiyle senkronize
        st.markdown('<div style="font-size:15px;font-weight:600;color:#e2e8f0;margin-bottom:14px;">Hız Kırılım Analizi (TL)</div>', unsafe_allow_html=True)
        tierler = [16, 35, 50, 100, 200, 500, 1000]
        rang_html = ""
        global_max = df_range["fiyat_ilk_donem"].max() if not df_range.empty else 1
        global_max = global_max or 1
        for hiz in tierler:
            sub_t = df_range[df_range["hiz_mbps"] == hiz]
            if sub_t.empty:
                continue
            mn  = sub_t["fiyat_ilk_donem"].min()
            mx  = sub_t["fiyat_ilk_donem"].max()
            avg = sub_t["fiyat_ilk_donem"].mean()
            med = sub_t["fiyat_ilk_donem"].median()
            cnt = len(sub_t)
            cheapest_row = sub_t.loc[sub_t["fiyat_ilk_donem"].idxmin()]
            cheapest_iss = cheapest_row["iss"] if "iss" in cheapest_row else "—"
            cheapest_tek = cheapest_row.get("teknoloji", "") or ""
            bar_left  = mn / global_max * 100
            bar_right = max(0, 100 - mx / global_max * 100)
            dot_pos   = min(99, avg / global_max * 100)
            rang_html += f"""
            <div class="tier-card" style="margin-bottom:14px;cursor:default;">
              <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                <span style="font-size:12px;font-weight:600;color:#e2e8f0;">{hiz} Mbps</span>
                <span style="font-size:11px;color:#475569;">Min: {int(mn):,} | Max: {int(mx):,}</span>
              </div>
              <div style="position:relative;height:6px;background:#1e2d3d;border-radius:3px;">
                <div style="position:absolute;left:{bar_left:.1f}%;right:{bar_right:.1f}%;height:100%;background:#4cd7f6;border-radius:3px;opacity:0.4;"></div>
                <div style="position:absolute;left:{dot_pos:.1f}%;top:50%;transform:translate(-50%,-50%);width:10px;height:10px;background:#4cd7f6;border-radius:50%;border:2px solid #0a0f12;" title="Ort: {int(avg):,} TL"></div>
              </div>
              <div class="tier-detail">
                <div style="display:flex;gap:16px;flex-wrap:wrap;">
                  <span style="font-size:11px;color:#94a3b8;">Ort: <b style="color:#e2e8f0;">{int(avg):,} TL</b></span>
                  <span style="font-size:11px;color:#94a3b8;">Medyan: <b style="color:#e2e8f0;">{int(med):,} TL</b></span>
                  <span style="font-size:11px;color:#94a3b8;">{cnt} paket</span>
                  <span style="font-size:11px;color:#94a3b8;">En ucuz: <b style="color:#4cd7f6;">{cheapest_iss} {int(mn):,} TL</b> <span style="opacity:0.6;">({cheapest_tek})</span></span>
                </div>
              </div>
            </div>"""
        tier_css = """<style>
.tier-detail{max-height:0;opacity:0;overflow:hidden;
  transition:max-height .25s ease,opacity .2s ease,margin-top .2s ease;}
.tier-card:hover .tier-detail{max-height:60px;opacity:1;margin-top:6px;}
body{background:transparent;margin:0;font-family:sans-serif;}
</style>"""
        tier_content = rang_html or '<p style="color:#475569;">Veri yok.</p>'
        card_count = rang_html.count('tier-card')
        st.components.v1.html(tier_css + tier_content, height=card_count * 70 + 20, scrolling=False)

    # Son fiyat hareketleri
    st.markdown('<div class="section-title">Son Fiyat Hareketleri</div>', unsafe_allow_html=True)
    alerts_df = load_alerts(50)
    if aktif_katlar:
        alerts_df = alerts_df[alerts_df["kategori"].isin(aktif_katlar)]
    alerts_df = alerts_df[alerts_df["tur"].isin(["fiyat_dustu","fiyat_yukseldi","yeni_paket","paket_kaldirildi"])]
    shown = _dedup_alerts(alerts_df)
    rows = list(shown.values())[:12]
    if rows:
        col1, col2 = st.columns(2)
        for i, row in enumerate(rows):
            with (col1 if i % 2 == 0 else col2):
                render_alert_card(row)
    else:
        st.markdown('<p style="color:#475569;text-align:center;padding:24px;">Henüz fiyat hareketi yok.</p>', unsafe_allow_html=True)

# ── SAYFA: KARŞILAŞTIRMA ─────────────────────────────────────────────────────

elif sayfa == "Karşılaştırma":
    st.markdown("""
    <div class="main-header"><div>
      <div class="subtitle">Hız Kademesi Fiyat Analizi</div>
      <h1>KARŞILAŞTIRMA</h1>
    </div></div>
    """, unsafe_allow_html=True)

    df_fiy = _fiyatli(df)
    hizlar_num = sorted(df_fiy["hiz_mbps"].dropna().unique().astype(int).tolist())
    has_5g = (df_fiy["teknoloji"] == "5g").any()
    hiz_opts = [str(h) for h in hizlar_num] + (["5G / Kota"] if has_5g else [])

    ca, cb, cc = st.columns([2,2,2])
    secili_hiz = ca.selectbox("Hız Kademesi", hiz_opts)
    tek_opts = ["Tümü"] + sorted(df_fiy["teknoloji"].dropna().unique().tolist())
    secili_tek = cb.selectbox("Teknoloji", tek_opts)
    siralama = cc.selectbox("Sıralama", ["Ucuzdan Pahalıya","Pahalıdan Ucuza","ISS Adı"])

    if secili_hiz == "5G / Kota":
        sub = df_fiy[df_fiy["teknoloji"] == "5g"]
    else:
        sub = df_fiy[df_fiy["hiz_mbps"] == int(secili_hiz)]
    if secili_tek != "Tümü":
        sub = sub[sub["teknoloji"] == secili_tek]
    sub = sub[~sub["paket_adi"].apply(_is_kurumsal)]

    if siralama == "Ucuzdan Pahalıya": sub = sub.sort_values("fiyat_ilk_donem")
    elif siralama == "Pahalıdan Ucuya": sub = sub.sort_values("fiyat_ilk_donem", ascending=False)
    else: sub = sub.sort_values("iss")

    st.markdown(f'<div class="section-title">{secili_hiz} Mbps · {len(sub)} paket</div>', unsafe_allow_html=True)

    if sub.empty:
        st.info("Bu kriterde paket bulunamadı.")
    else:
        cols = st.columns(3)
        rank_cls = {0:"rank-gold",1:"rank-silver",2:"rank-bronze"}
        for i, (_, row) in enumerate(sub.iterrows()):
            with cols[i % 3]:
                rank = rank_cls.get(i, "")
                fiyat_str = f"₺{_fmt_fiyat(row['fiyat_ilk_donem'])}"
                sonraki_str = f"Sonraki: ₺{_fmt_fiyat(row['fiyat_sonraki_donem'])}" if pd.notna(row.get("fiyat_sonraki_donem")) and row["fiyat_sonraki_donem"] > 0 and not row.get("fiyat_sabit_mi") else ""
                st.markdown(f"""
                <div class="pkg-card {rank}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                      <div class="pkg-iss">{row['iss']}</div>
                      <div class="pkg-price">{fiyat_str}</div>
                      <div class="pkg-price-sub">/ay {sonraki_str}</div>
                    </div>
                    <div>{'#'+str(i+1) if i<3 else ""}</div>
                  </div>
                  <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">
                    {_tech_badge(row['teknoloji'])} {_taahhut_badge(row.get('sozlesme_suresi_ay',0))}
                  </div>
                  <div class="pkg-name">{row.get('paket_adi') or ''}</div>
                  {"<div class='pkg-name' style='color:#f87171;'>⚠ "+str(row['bolge_kisiti'])+"</div>" if pd.notna(row.get('bolge_kisiti')) and row['bolge_kisiti'] else ""}
                </div>
                """, unsafe_allow_html=True)
                st.markdown("")

# ── SAYFA: TÜM PAKETLER ──────────────────────────────────────────────────────

elif sayfa == "Tüm Paketler":
    st.markdown("""
    <div class="main-header"><div>
      <div class="subtitle">Tam Paket Veritabanı</div>
      <h1>TÜM PAKETLER</h1>
    </div></div>
    """, unsafe_allow_html=True)

    fa, fb, fc, fd = st.columns([2,2,2,2])
    tek_filtre = fa.multiselect("Teknoloji", sorted(df["teknoloji"].dropna().unique().tolist()))
    hiz_filtre = fb.multiselect("Hız (Mbps)", sorted([int(h) for h in df["hiz_mbps"].dropna().unique() if h > 0]))
    max_fiyat  = fc.slider("Maks Fiyat (₺)", 0, 5000, 5000, 50)
    iss_ara    = fd.text_input("ISS Ara", placeholder="ISS adı...")

    fe, ff = st.columns([2,6])
    sabit_mi   = fe.checkbox("Sabit fiyatlı")
    taahhut_yok= ff.checkbox("Taahhütsüz")

    sub = df.copy()
    if tek_filtre:  sub = sub[sub["teknoloji"].isin(tek_filtre)]
    if hiz_filtre:  sub = sub[sub["hiz_mbps"].isin(hiz_filtre)]
    if sabit_mi:    sub = sub[sub["fiyat_sabit_mi"]==1]
    if taahhut_yok: sub = sub[sub["sozlesme_suresi_ay"]==0]
    if iss_ara:     sub = sub[sub["iss"].str.contains(iss_ara, case=False, na=False)]
    sub = sub[sub["fiyat_ilk_donem"] <= max_fiyat]
    sub = sub[~sub["paket_adi"].apply(_is_kurumsal)]

    st.markdown(f'<div class="section-title">{len(sub)} paket listeleniyor</div>', unsafe_allow_html=True)

    display = sub[["iss","paket_adi","hiz_mbps","teknoloji","fiyat_ilk_donem","fiyat_sonraki_donem","sozlesme_suresi_ay","modem","bolge_kisiti","kampanya_bitis","son_guncelleme"]].copy()
    display.columns = ["ISS","Paket","Hız","Teknoloji","Fiyat","Sonraki","Taahhüt(ay)","Modem","Bölge","Kamp. Bitiş","Güncelleme"]
    display["Fiyat"]     = display["Fiyat"].apply(_fmt_fiyat)
    display["Sonraki"]   = display["Sonraki"].apply(lambda v: _fmt_fiyat(v) if pd.notna(v) else "")
    display["Hız"]       = display["Hız"].apply(_fmt_hiz)
    display["Taahhüt(ay)"] = display["Taahhüt(ay)"].apply(lambda v: "" if pd.isna(v) else str(int(v)))
    st.dataframe(display, use_container_width=True, hide_index=True)

    import io as _io
    buf = _io.BytesIO()
    sub.to_excel(buf, index=False)
    st.download_button("⬇ Excel İndir", buf.getvalue(), "paketler.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── SAYFA: ISS PROFİLİ ───────────────────────────────────────────────────────

elif sayfa == "ISS Profili":
    iss_list = sorted(df["iss"].unique().tolist())
    secili_iss = st.selectbox("ISS Seç", iss_list, label_visibility="collapsed")
    iss_df = df[df["iss"] == secili_iss]

    conn = get_conn()
    iss_row = conn.execute("SELECT id, url, kategori FROM isps WHERE name=? AND aktif=1", (secili_iss,)).fetchone()
    url_rows = conn.execute("SELECT url, etiket, parse_pkg FROM isp_urls WHERE isp_id=? AND aktif=1", (iss_row["id"],)).fetchall() if iss_row else []
    conn.close()

    fiy_df = _fiyatli(iss_df)
    color  = _isp_badge_color(secili_iss)
    abbr   = _isp_abbr(secili_iss)
    kat    = iss_row["kategori"] if iss_row else "diger"
    kat_label = "RAKİP" if kat == "rakip" else "DİĞER"
    kat_color = "#4cd7f6" if kat == "rakip" else "#64748b"

    # Teknoloji özeti
    tek_list = sorted(iss_df["teknoloji"].dropna().unique().tolist())
    tek_str  = " & ".join(t.upper() for t in tek_list[:3]) if tek_list else "—"

    # Son değişim
    conn2 = get_conn()
    son_deg = conn2.execute("""
        SELECT ph.degisim_zamani FROM package_history ph
        JOIN packages p ON p.paket_key=ph.paket_key
        JOIN isps i ON i.id=p.isp_id
        WHERE i.name=? ORDER BY ph.degisim_zamani DESC LIMIT 1
    """, (secili_iss,)).fetchone()
    conn2.close()
    son_deg_str = _time_ago(son_deg[0]) if son_deg else "—"

    # ── Header kartı ──
    st.markdown(f"""
    <div style="background:#0d1520;border:1px solid #1e2d3d;border-radius:12px;padding:20px 24px;margin-bottom:20px;display:flex;align-items:center;gap:18px;">
      <div class="isp-badge" style="background:{color};color:#e2e8f0;width:52px;height:52px;font-size:17px;flex-shrink:0;">{abbr}</div>
      <div style="flex:1;">
        <div style="font-size:20px;font-weight:700;color:#f8fafc;">{secili_iss}</div>
        <div style="font-size:12px;color:#64748b;margin-top:3px;">{'Ulusal' if kat=='rakip' else 'Bölgesel'} · {tek_str}</div>
      </div>
      <div style="display:flex;gap:8px;">
        <span style="padding:4px 12px;border-radius:6px;background:rgba(76,215,246,0.12);color:{kat_color};font-size:11px;font-weight:700;border:1px solid {kat_color}33;">{kat_label}</span>
        <span style="padding:4px 12px;border-radius:6px;background:rgba(78,222,163,0.1);color:#4edea3;font-size:11px;font-weight:700;border:1px solid #4edea333;">İZLENİYOR</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 4 Metrik ──
    ort_fiyat = fiy_df["fiyat_ilk_donem"].mean() if not fiy_df.empty else None
    min_fiyat = fiy_df["fiyat_ilk_donem"].min() if not fiy_df.empty else None
    m1,m2,m3,m4 = st.columns(4)
    for col, label, val, color2 in [
        (m1, "Paket Sayısı",    len(iss_df),                                          "#4cd7f6"),
        (m2, "Ortalama Fiyat",  f"₺{_fmt_fiyat(ort_fiyat)}" if ort_fiyat else "—",   "#a78bfa"),
        (m3, "En Düşük",        f"₺{_fmt_fiyat(min_fiyat)}" if min_fiyat else "—",   "#4edea3"),
        (m4, "Son Değişim",     son_deg_str,                                           "#fbbf24"),
    ]:
        col.markdown(f"""
        <div class="m-card">
          <div class="m-accent-bar" style="background:{color2};"></div>
          <div class="m-label">{label}</div>
          <div class="m-value" style="color:{color2};font-size:26px;">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Scatter — full width ──
    if len(fiy_df) >= 2 and _HAS_ALTAIR:
        fiy_df2 = fiy_df[fiy_df["hiz_mbps"].notna()].copy()
        fiy_df2["hiz_mbps"] = fiy_df2["hiz_mbps"].astype(float)
        sc = alt.Chart(fiy_df2).mark_circle(size=90, opacity=0.85).encode(
            x=alt.X("hiz_mbps:Q", title="Hız (Mbps)",
                    axis=alt.Axis(labelColor="#64748b", titleColor="#64748b", gridColor="#1e2d3d")),
            y=alt.Y("fiyat_ilk_donem:Q", title="Fiyat (TL)",
                    axis=alt.Axis(labelColor="#64748b", titleColor="#64748b", gridColor="#1e2d3d")),
            color=alt.Color("teknoloji:N", scale=alt.Scale(
                domain=["fiber","vdsl","adsl","5g","belirsiz"],
                range=["#4cd7f6","#fbbf24","#94a3b8","#a78bfa","#475569"]),
                legend=alt.Legend(orient="right", labelColor="#94a3b8", titleColor="#64748b", labelFontSize=11)),
            tooltip=["paket_adi","hiz_mbps","fiyat_ilk_donem","teknoloji","sozlesme_suresi_ay"],
        )
        iss_layers = [sc]
        x2 = fiy_df2["hiz_mbps"].values.astype(float)
        y2 = fiy_df2["fiyat_ilk_donem"].values.astype(float)
        v2 = _np.isfinite(x2) & _np.isfinite(y2)
        if v2.sum() >= 4:
            try:
                c2 = _np.polyfit(x2[v2], y2[v2], 2)
                xl = _np.linspace(x2[v2].min(), x2[v2].max(), 80)
                yl = _np.polyval(c2, xl)
                df_tr2 = pd.DataFrame({"hiz_mbps": xl, "fiyat_ilk_donem": yl})
                tr2 = alt.Chart(df_tr2).mark_line(color="#4cd7f6", opacity=0.45, strokeWidth=2).encode(
                    x=alt.X("hiz_mbps:Q"), y=alt.Y("fiyat_ilk_donem:Q"))
                iss_layers = [tr2, sc]
            except Exception:
                pass
        iss_chart = alt.layer(*iss_layers).properties(height=260).interactive().configure(background="transparent").configure_view(
            strokeOpacity=0, strokeWidth=0).configure_axis(domainColor="#1e2d3d")
        st.altair_chart(iss_chart, use_container_width=True)

    # ── Paket tablosu — Tüm Paketler sayfasıyla aynı detay ──
    st.markdown('<div class="section-title">Paketler</div>', unsafe_allow_html=True)

    disp = iss_df[["paket_adi","hiz_mbps","teknoloji","fiyat_ilk_donem","fiyat_sonraki_donem",
                   "sozlesme_suresi_ay","modem","bolge_kisiti","kampanya_bitis","son_guncelleme"]].copy()
    disp.columns = ["Paket","Hız","Teknoloji","Fiyat","Sonraki Fiyat","Taahhüt(ay)","Modem","Bölge","Kampanya Bitiş","Güncelleme"]
    disp["Fiyat"]        = disp["Fiyat"].apply(_fmt_fiyat)
    disp["Sonraki Fiyat"]= disp["Sonraki Fiyat"].apply(lambda v: _fmt_fiyat(v) if pd.notna(v) else "")
    disp["Hız"]          = disp["Hız"].apply(_fmt_hiz)
    disp["Taahhüt(ay)"]  = disp["Taahhüt(ay)"].apply(lambda v: "" if pd.isna(v) else str(int(v)))
    disp["Modem"]        = disp["Modem"].fillna("")
    disp["Bölge"]        = disp["Bölge"].fillna("")
    disp["Kampanya Bitiş"]= disp["Kampanya Bitiş"].fillna("")
    disp["Güncelleme"]   = disp["Güncelleme"].apply(lambda v: str(v)[:10] if pd.notna(v) else "")
    disp = disp.sort_values(["Teknoloji","Hız","Fiyat"])
    st.dataframe(disp, use_container_width=True, hide_index=True)

    # URL linkleri
    if url_rows:
        st.markdown("")
        chip_html = ""
        for ur in url_rows:
            label = ur["etiket"] or ur["url"].split("/")[2]
            chip_html += f'<a href="{ur["url"]}" target="_blank" style="display:inline-flex;align-items:center;gap:5px;padding:4px 12px;border-radius:20px;background:#0f1d2a;border:1px solid #1e2d3d;color:#4cd7f6;font-size:11px;text-decoration:none;margin:2px 2px;">🔗 {label}</a>'
        st.markdown(chip_html, unsafe_allow_html=True)

    # Son alertler
    alerts_df = load_alerts(100)
    iss_alerts = alerts_df[alerts_df["iss"] == secili_iss]
    if not iss_alerts.empty:
        st.markdown('<div class="section-title" style="margin-top:20px;">Son Değişimler</div>', unsafe_allow_html=True)
        shown = _dedup_alerts(iss_alerts)
        col1, col2 = st.columns(2)
        for i, row in enumerate(list(shown.values())[:8]):
            with (col1 if i % 2 == 0 else col2):
                render_alert_card(row)

# ── SAYFA: BİLDİRİMLER ───────────────────────────────────────────────────────

elif sayfa == "Bildirimler":
    st.markdown("""
    <div class="main-header"><div>
      <div class="subtitle">Fiyat Hareketleri & Değişimler</div>
      <h1>BİLDİRİMLER</h1>
    </div></div>
    """, unsafe_allow_html=True)

    ca, cb = st.columns([4, 1])
    tur_filtre = ca.multiselect("Tür Filtrele", ["fiyat_dustu","fiyat_yukseldi","yeni_paket","paket_kaldirildi","icerik_degisim"],
        default=["fiyat_dustu","fiyat_yukseldi","yeni_paket","paket_kaldirildi"])
    with cb:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        if st.button("✓ Tümünü Okundu", use_container_width=True):
            mark_all_read(); st.rerun()

    alerts_df = load_alerts(200)
    if aktif_katlar: alerts_df = alerts_df[alerts_df["kategori"].isin(aktif_katlar)]
    if tur_filtre:   alerts_df = alerts_df[alerts_df["tur"].isin(tur_filtre)]

    shown = _dedup_alerts(alerts_df)
    rows  = list(shown.values())
    if rows:
        st.markdown(f'<div class="section-title">{len(rows)} bildirim</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        for i, row in enumerate(rows):
            with (col1 if i % 2 == 0 else col2):
                render_alert_card(row)
    else:
        st.markdown('<p style="color:#475569;text-align:center;padding:40px;">Bildirim bulunamadı.</p>', unsafe_allow_html=True)

    # Paket geçmişi
    st.divider()
    st.markdown('<div class="section-title">Paket Geçmişi Sorgula</div>', unsafe_allow_html=True)
    conn_ph = get_conn()
    ph_isps = [r[0] for r in conn_ph.execute("""
        SELECT DISTINCT i.name
        FROM package_history ph
        JOIN isps i ON i.id = CAST(SUBSTR(ph.paket_key, 1, INSTR(ph.paket_key, '|') - 1) AS INTEGER)
        ORDER BY i.name
    """).fetchall()]
    conn_ph.close()
    if ph_isps:
        col_ph1, col_ph2 = st.columns([1, 2])
        ph_iss = col_ph1.selectbox("ISS", ["— Seçin —"] + ph_isps, key="ph_iss")
        if ph_iss != "— Seçin —":
            conn_ph2 = get_conn()
            ph_pkgs = conn_ph2.execute("""
                SELECT DISTINCT ph.paket_key,
                    COALESCE(p.paket_adi, ph.paket_key) as paket_adi,
                    p.hiz_mbps,
                    COALESCE(p.teknoloji, '') as teknoloji,
                    p.fiyat_ilk_donem
                FROM package_history ph
                LEFT JOIN packages p ON p.paket_key = ph.paket_key
                JOIN isps i ON i.id = CAST(SUBSTR(ph.paket_key, 1, INSTR(ph.paket_key, '|') - 1) AS INTEGER)
                WHERE i.name = ?
                ORDER BY p.hiz_mbps, p.fiyat_ilk_donem
            """, (ph_iss,)).fetchall()
            conn_ph2.close()
            pkg_labels = {f"{r[1] or ''} — {r[2] or '?'} Mbps {r[3] or ''} {int(r[4]) if r[4] else '?'} TL": r[0] for r in ph_pkgs}
            ph_pkg_label = col_ph2.selectbox("Paket", ["— Seçin —"] + list(pkg_labels.keys()), key="ph_pkg")
            if ph_pkg_label != "— Seçin —":
                hist = load_history(pkg_labels[ph_pkg_label])
                if not hist.empty:
                    st.dataframe(hist, use_container_width=True, hide_index=True)
                else:
                    st.info("Bu paket için geçmiş kaydı yok.")
    else:
        st.info("Henüz geçmiş kaydı bulunmuyor.")

# ── SAYFA: FİYAT TRENDİ ──────────────────────────────────────────────────────

elif sayfa == "Fiyat Trendi":
    st.markdown("""
    <div class="main-header"><div>
      <div class="subtitle">Tarihsel Fiyat Analizi</div>
      <h1>FİYAT TRENDİ</h1>
    </div></div>
    """, unsafe_allow_html=True)

    conn = get_conn()
    iss_list_trend = [r[0] for r in conn.execute("""
        SELECT DISTINCT i.name FROM package_history ph
        JOIN packages p ON p.paket_key=ph.paket_key
        JOIN isps i ON i.id=p.isp_id
        WHERE ph.alan='fiyat_ilk_donem' ORDER BY i.name
    """).fetchall()]
    conn.close()

    if not iss_list_trend:
        st.info("Henüz geçmiş fiyat verisi yok.")
    else:
        ca, cb = st.columns(2)
        secili_iss = ca.selectbox("ISS", iss_list_trend)

        conn2 = get_conn()
        hiz_list = [r[0] for r in conn2.execute("""
            SELECT DISTINCT p.hiz_mbps FROM package_history ph
            JOIN packages p ON p.paket_key=ph.paket_key
            JOIN isps i ON i.id=p.isp_id
            WHERE i.name=? AND ph.alan='fiyat_ilk_donem' ORDER BY p.hiz_mbps
        """, (secili_iss,)).fetchall()]
        conn2.close()

        secili_hiz = cb.selectbox("Hız (Mbps)", hiz_list) if hiz_list else None

        if secili_hiz:
            trend = load_price_trend(secili_iss, secili_hiz)
            if not trend.empty and _HAS_ALTAIR:
                trend["tarih"] = pd.to_datetime(trend["tarih"])
                line = alt.Chart(trend).mark_line(color="#4cd7f6", strokeWidth=2).encode(
                    x=alt.X("tarih:T", title="Tarih", axis=alt.Axis(labelColor="#64748b", titleColor="#64748b", gridColor="#1e2d3d", format="%d/%m")),
                    y=alt.Y("fiyat:Q", title="Fiyat (TL)", axis=alt.Axis(labelColor="#64748b", titleColor="#64748b", gridColor="#1e2d3d")),
                    tooltip=["tarih:T","fiyat:Q"]
                )
                points = alt.Chart(trend).mark_circle(size=60, color="#4cd7f6").encode(
                    x="tarih:T", y="fiyat:Q", tooltip=["tarih:T","fiyat:Q"])
                chart = (line + points).properties(height=320).configure(background="transparent").configure_view(strokeOpacity=0)
                st.altair_chart(chart, use_container_width=True)
                st.dataframe(trend[["tarih","fiyat"]].rename(columns={"tarih":"Tarih","fiyat":"Fiyat (TL)"}),
                    use_container_width=True, hide_index=True)
            else:
                st.info("Bu hız için trend verisi yok.")
