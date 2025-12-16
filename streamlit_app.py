import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import csv
import ast
import re
import urllib.parse
from datetime import datetime

# ================= 1. KONFIGURASI HALAMAN =================
st.set_page_config(
    page_title="Cari Kemah AI",
    page_icon="🏕️",
    layout="wide"
)

# --- IMPORT MODUL (DENGAN PENANGANAN ERROR) ---
try:
    from src import mesin_pencari
    from src import utils
except ImportError as e:
    st.error(f"⚠️ Gagal memuat modul internal: {e}")
    st.stop()

# --- PATH FILE ---
DATA_PATH = os.path.join("Documents", "info_tempat.csv")
SCORECARD_PATH = os.path.join("Documents", "scorecards.json")
LOG_FOLDER = "Riwayat"
LOG_FILE = "riwayat_pencarian.csv"
LOG_PATH = os.path.join(LOG_FOLDER, LOG_FILE)

# ================= 2. FUNGSI BANTUAN (HELPER) =================
def load_css(file_name="style.css"):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def parse_metadata_column(val):
    """Mengubah string '[...]' menjadi objek Python list/dict"""
    try:
        if pd.isna(val) or val == "": return []
        if isinstance(val, (list, dict)): return val
        return ast.literal_eval(str(val))
    except: return []

def save_log(query, meta):
    """Menyimpan log ke CSV (Support Admin Dashboard)"""
    if not os.path.exists(LOG_FOLDER): os.makedirs(LOG_FOLDER)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["waktu", "query", "tokens", "intent", "region"])
    try:
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                query,
                " ".join(meta["tokens"]),
                meta["intent"],
                meta["region"]
            ])
    except: pass

load_css()

# ================= 3. INISIALISASI DATA & AI =================
@st.cache_resource
def init_engine():
    mesin_pencari.initialize_mesin()
    return True

@st.cache_data
def load_db():
    # 1. Scorecards
    scorecards = {}
    if os.path.exists(SCORECARD_PATH):
        try:
            with open(SCORECARD_PATH, "r", encoding="utf-8") as f:
                scorecards = json.load(f)
        except: pass

    # 2. Info Tempat (Single Source)
    df = pd.DataFrame()
    if os.path.exists(DATA_PATH):
        try:
            df = pd.read_csv(DATA_PATH).fillna("")
            if "Nama_Tempat" in df.columns:
                df["__key"] = df["Nama_Tempat"].astype(str).str.lower().str.strip()
            
            # Parsing Harga & Fasilitas
            col_hrg = next((c for c in df.columns if 'price' in c.lower() or 'harga' in c.lower()), None)
            col_fas = next((c for c in df.columns if 'facilit' in c.lower() or 'fasilitas' in c.lower()), None)

            if col_hrg: df['parsed_harga'] = df[col_hrg].apply(parse_metadata_column)
            else: df['parsed_harga'] = [[] for _ in range(len(df))]

            if col_fas: df['parsed_fasilitas'] = df[col_fas].apply(parse_metadata_column)
            else: df['parsed_fasilitas'] = [[] for _ in range(len(df))]
        except: pass
    
    return scorecards, df

init_engine()
scorecards, df_info = load_db()

# ================= 4. LOGIKA PENCARIAN =================
def run_search(query):
    if not query:
        # Rekomendasi Default (Top Scorecard)
        top = sorted(scorecards.keys(), key=lambda x: sum(v['score'] for v in scorecards[x]['aspects'].values())/5, reverse=True)[:5]
        return [{'name': n, 'relevansi': 0, 'snippet': ''} for n in top], None

    # AI Process
    tokens, intent, region = mesin_pencari.analyze_full_query(query)
    raw_results = mesin_pencari.search_by_keyword(tokens, intent, region)
    
    results = []
    for item in raw_results:
        results.append({
            'name': item['name'],
            'relevansi': item.get('top_vsm_score', 0),
            'snippet': item.get('snippet', '')
        })
    return results, {'tokens': tokens, 'intent': intent, 'region': region}

# ================= 5. ADMIN PANEL (FITUR LAMA DIKEMBALIKAN) =================
with st.sidebar:
    st.header("⚙️ Panel Admin")
    if st.checkbox("Buka Dashboard"):
        pw = st.text_input("Password", type="password")
        if pw == "1234":
            st.success("Mode Admin Aktif")
            st.metric("Total Database", f"{len(df_info)} Tempat")
            
            if os.path.exists(LOG_PATH):
                try:
                    df_log = pd.read_csv(LOG_PATH)
                    if not df_log.empty:
                        st.subheader("📊 Statistik Pencarian")
                        # Top Query
                        if 'query' in df_log.columns:
                            st.write("**Kata Kunci Populer:**")
                            top_q = df_log['query'].value_counts().head(5)
                            for q, c in top_q.items():
                                st.metric(f"'{q}'", f"{c} kali")
                        
                        # Top Region
                        if 'region' in df_log.columns:
                            st.write("**Wilayah Populer:**")
                            top_r = df_log['region'].value_counts().head(3)
                            st.bar_chart(top_r)

                        with st.expander("Lihat Data Mentah"):
                            st.dataframe(df_log.tail(50))
                    else: st.info("Belum ada data log.")
                except: st.warning("File log rusak.")
        elif pw: st.error("Password Salah")

# ================= 6. HEADER & SEARCH =================
st.title("🏕️ Cari Kemah AI")
st.markdown('<p class="sub-judul">Temukan Hidden Gems di Jogja & Jateng</p>', unsafe_allow_html=True)

# State
if 'last_res' not in st.session_state: st.session_state.last_res = []
if 'last_meta' not in st.session_state: st.session_state.last_meta = None

c_src, c_srt = st.columns([3, 1])
with c_src:
    with st.form("search_box"):
        q_in = st.text_input("Cari", placeholder="Misal: pinggir sungai, toilet bersih...", label_visibility="collapsed")
        go = st.form_submit_button("Cari")

with c_srt:
    sort_mode = st.selectbox("Urutkan", ["Relevansi AI", "Rapor Tertinggi"], label_visibility="collapsed")

if go:
    res, meta = run_search(q_in)
    st.session_state.last_res = res
    st.session_state.last_meta = meta
    if q_in: save_log(q_in, meta)

# Data to Render
final_results = st.session_state.last_res if st.session_state.last_res else run_search("")[0]

# Sorting
if sort_mode == "Rapor Tertinggi":
    final_results = sorted(final_results, key=lambda x: sum(v['score'] for v in scorecards.get(x['name'], {}).get('aspects', {}).values()) if x['name'] in scorecards else 0, reverse=True)

# ================= 7. RENDER HASIL (CARD VIEW) =================
st.write("")
if not final_results:
    st.warning("Tidak ditemukan hasil.")
else:
    # Debug AI Info
    if st.session_state.last_meta:
        m = st.session_state.last_meta
        with st.expander("🧠 Debug AI"):
            st.write(f"Intent: {m['intent']} | Region: {m['region']} | Tokens: {m['tokens']}")

    for item in final_results:
        nama = item.get('name', '')
        key = nama.lower().strip()
        sc = scorecards.get(nama)
        
        # Info Metadata
        row = df_info[df_info["__key"] == key]
        alamat, foto, maps = "Alamat n/a", "", "#"
        parsed_hrg, parsed_fas = [], []
        
        if not row.empty:
            r = row.iloc[0]
            alamat = r.get("Alamat") or r.get("Lokasi") or alamat
            foto = r.get("Photo_URL") or ""
            maps = r.get("Gmaps_Link") or "#"
            parsed_hrg = r.get("parsed_harga", [])
            parsed_fas = r.get("parsed_fasilitas", [])

        # --- CONTAINER KARTU ---
        with st.container():
            c1, c2, c3 = st.columns([1.5, 2.5, 2])
            
            # FOTO
            with c1:
                if str(foto).startswith("http"): st.image(foto, use_container_width=True)
                else: st.image(f"https://placehold.co/400x300/2E8B57/FFFFFF?text={urllib.parse.quote(nama)}", use_container_width=True)
                st.link_button("📍 Buka Maps", maps, use_container_width=True)

            # INFO UTAMA
            with c2:
                st.subheader(nama)
                # Badges
                if sc and sc.get('badges'):
                    b_html = ""
                    cols = {"keluarga": "#2196F3", "pemula": "#4CAF50", "petualang": "#FF9800"}
                    for b in sc['badges']:
                        c = cols.get(b, "#888")
                        b_html += f'<span class="badge" style="background-color:{c}">{b.title()}</span>'
                    st.markdown(b_html, unsafe_allow_html=True)
                
                st.caption(f"📍 {alamat}")
                
                # Insight
                if item.get('snippet'): st.info(f"💡 \"{item['snippet']}\"")
                elif sc and sc.get('insight'): st.markdown(f"<div class='insight-box'>💡 {sc['insight']}</div>", unsafe_allow_html=True)

                # POPUP HARGA (LOGIKA LAMA - 4 KATEGORI)
                if st.button("💰 Cek Biaya & Fasilitas", key=f"btn_{key}"):
                    @st.dialog(f"Detail: {nama}")
                    def popup():
                        if not parsed_hrg:
                            st.warning("Info harga belum tersedia.")
                        else:
                            # Logika 4 Kategori (Wajib, Pokok, Mewah, Layanan)
                            wajib, pokok, mewah, layanan = [], [], [], []
                            est_dasar = 0
                            
                            for p in parsed_hrg:
                                if not isinstance(p, dict): continue
                                itm = p.get('Item') or p.get('item', '')
                                kat = str(p.get('Kategori') or '').lower()
                                try: hrg = int(str(p.get('Harga') or 0).replace('.',''))
                                except: hrg = 0
                                
                                txt = f"- {itm}: **Rp {hrg:,}**"
                                obj = {'h': hrg, 't': txt, 'i': itm}
                                
                                if 'wajib' in kat or 'tiket' in itm.lower() or 'parkir' in itm.lower(): wajib.append(obj)
                                elif 'sewa' in kat or 'tenda' in itm.lower(): pokok.append(obj)
                                elif 'layanan' in kat: layanan.append(obj)
                                else: mewah.append(obj)
                            
                            # Hitung Estimasi (Tiket Min + Parkir Min)
                            min_tik = min([x['h'] for x in wajib if 'tiket' in x['i'].lower()], default=0)
                            min_par = min([x['h'] for x in wajib if 'parkir' in x['i'].lower()], default=0)
                            est_dasar = min_tik + min_par

                            if wajib: 
                                st.markdown("##### 🎟️ Wajib")
                                for x in wajib: st.write(x['t'])
                            if pokok:
                                st.markdown("##### ⛺ Sewa Pokok")
                                for x in pokok: st.write(x['t'])
                            if mewah:
                                st.markdown("##### 🔥 Tambahan")
                                for x in mewah: st.write(x['t'])
                            if layanan:
                                st.markdown("##### 💁 Layanan")
                                for x in layanan: st.write(x['t'])
                                
                            st.divider()
                            if est_dasar > 0: st.success(f"**Estimasi Dasar (Tiket+Parkir): Rp {est_dasar:,}**")

                        # Fasilitas
                        st.write("")
                        st.markdown("##### ✅ Fasilitas")
                        if parsed_fas:
                            if isinstance(parsed_fas, list):
                                for f in parsed_fas:
                                    val = list(f.values())[0] if isinstance(f, dict) else f
                                    st.write(f"• {val}")
                            else: st.write(parsed_fas)
                        else: st.caption("Info fasilitas kosong.")
                    
                    popup()

            # SCORECARD
            with c3:
                if sc:
                    st.markdown("##### 📊 Rapor Kualitas")
                    for asp in sc.get('aspects', {}).values():
                        if asp.get('mentions', 0) > 0:
                            ca, cb = st.columns([1, 1])
                            ca.write(f"{asp['icon']} {asp['label']}")
                            cb.caption(f"⭐ {asp['score']}")
                            st.progress(asp['score']/5)
                else: st.caption("Belum ada rapor.")
        
        st.divider()