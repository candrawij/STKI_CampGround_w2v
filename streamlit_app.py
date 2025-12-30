import streamlit as st
import pandas as pd
import os
import json
import base64
import urllib.parse
import time
from datetime import datetime, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="CariKemah", 
    page_icon="⛺", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# --- 2. LOAD MODUL ---
try:
    from Asisten.smart_search import SmartSearchEngine
    from Asisten.db_handler import db 
except ImportError: st.stop()

# --- 3. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'search_results' not in st.session_state: st.session_state.search_results = pd.DataFrame()
if 'last_query' not in st.session_state: st.session_state.last_query = ""

# --- 4. ASSETS & STYLING ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

def set_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
        st.markdown(f'''
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.95)), url("data:image/jpg;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        ''', unsafe_allow_html=True)

if os.path.exists('tent-night-wide.jpg'):
    set_bg('tent-night-wide.jpg')

# CSS Tambahan untuk Tampilan Card & Fasilitas
st.markdown("""
<style>
    .fas-tag {
        background-color: #2c3e50;
        color: #ecf0f1;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        margin-right: 5px;
        display: inline-block;
        border: 1px solid #34495e;
    }
    .price-tag {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2ecc71;
    }
    .rating-star {
        color: #f1c40f;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def format_rp(angka): 
    return f"Rp {int(angka):,}".replace(",", ".")

# --- 5. ENGINE LOAD ---
@st.cache_resource
def init_engine(): return SmartSearchEngine()

engine = init_engine()

# --- 6. LOGIC PENCARIAN & MODAL DETAIL ---

def run_search():
    query = st.session_state.query_input
    if query:
        with st.spinner("Sedang mencari..."):
            if engine.is_ready:
                res = engine.search(query, top_k=60)
                if not res.empty:
                    # Reset index agar rapi (0, 1, 2...)
                    st.session_state.search_results = res.reset_index(drop=True)
                    st.session_state.last_query = query
            else: st.error("AI belum siap.")

# [UPDATE BESAR] MODAL DETAIL & BOOKING
@st.dialog("Detail & Reservasi", width="large")
def show_details(row, detail, sc_data):
    info = detail['info']
    
    # Header: Nama & Lokasi
    st.markdown(f"## {row['Nama Tempat']}")
    st.markdown(f"📍 {info.get('lokasi', '-')}")
    
    # Foto Utama (Placeholder jika kosong)
    foto_url = info.get('photo_url')
    if not foto_url: 
        safe_name = urllib.parse.quote(row['Nama Tempat'])
        foto_url = f"https://placehold.co/800x400/222/FFF?text={safe_name}"
    
    st.image(foto_url, use_container_width=True)

    # Tabs Info
    tab1, tab2, tab3 = st.tabs(["ℹ️ Info & Fasilitas", "💰 Harga", "📝 Booking"])
    
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("### Fasilitas")
            if detail['fasilitas']:
                html_tags = "".join([f"<span class='fas-tag'>{f}</span>" for f in detail['fasilitas']])
                st.markdown(html_tags, unsafe_allow_html=True)
            else:
                st.info("Data fasilitas belum tersedia.")
        
        with c2:
            st.markdown("### Rating")
            rate = info.get('rating_gmaps', 0)
            st.markdown(f"<span class='rating-star'>⭐ {rate} / 5.0</span>", unsafe_allow_html=True)
            st.caption("Sumber: Google Maps")
            
            # Tombol GMaps
            if 'gmaps_link' in info and info['gmaps_link']:
                st.link_button("🗺️ Buka Peta", info['gmaps_link'], use_container_width=True)

        st.divider()
        st.markdown("### Ulasan Relevan (Kata AI)")
        st.info(f"\"{str(row['Isi Ulasan'])[:300]}...\"")

    with tab2:
        if detail['harga']:
            # Tampilkan Tabel Harga Rapi
            df_h = pd.DataFrame(detail['harga'])[['item', 'harga']]
            df_h['harga_fmt'] = df_h['harga'].apply(format_rp)
            st.dataframe(df_h[['item', 'harga_fmt']], column_config={"item": "Jenis", "harga_fmt": "Biaya"}, hide_index=True, use_container_width=True)
        else:
            st.warning("Informasi harga belum tersedia.")

    # [UPDATE] FORM BOOKING LOGIS (SEPERTI TERMINAL)
    with tab3:
        if st.session_state.user is None:
            st.warning("🔒 Silakan Login terlebih dahulu untuk memesan.")
        else:
            st.markdown("### Form Pemesanan")
            
            # 1. PILIH PAKET (Dropdown)
            price_list = detail['harga']
            if price_list:
                # Buat list opsi: "Nama Paket - Rp XXX"
                options = [f"{p['item']} | {format_rp(p['harga'])}" for p in price_list]
                selected_opt = st.selectbox("Pilih Jenis Tiket/Paket:", options)
                
                # Cari harga asli dari pilihan
                idx = options.index(selected_opt)
                selected_item_name = price_list[idx]['item']
                selected_price = int(price_list[idx]['harga'])
            else:
                st.warning("Data harga kosong. Menggunakan default.")
                selected_item_name = "Tiket Masuk (Estimasi)"
                selected_price = 15000
                st.write(f"**Harga:** {format_rp(selected_price)}")

            # 2. INPUT DATA
            c_date, c_qty = st.columns(2)
            with c_date:
                # Validasi: min_value=datetime.today() agar tidak bisa pilih kemarin
                tgl = st.date_input("Tanggal Check-in", min_value=datetime.today())
            with c_qty:
                qty = st.number_input("Jumlah (Orang/Unit)", min_value=1, value=1)

            # 3. KALKULASI & SUBMIT
            total = selected_price * qty
            st.divider()
            
            st.markdown(f"""
            <div style="background-color: #2d3436; padding: 15px; border-radius: 10px; border: 1px solid #636e72;">
                <h4>Ringkasan Pesanan</h4>
                <p>📦 <b>Item:</b> {selected_item_name}<br>
                📅 <b>Tanggal:</b> {tgl}<br>
                👥 <b>Jumlah:</b> {qty}</p>
                <h3 style="color: #00cec9;">Total: {format_rp(total)}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            if st.button("✅ Ajukan Booking Sekarang", type="primary", use_container_width=True):
                # Simpan ke DB (Status otomatis PENDING dari db_handler)
                user_id = st.session_state.user['id']
                tempat_id = detail['info'].get('id')
                if not tempat_id: tempat_id = db.get_place_by_name(row['Nama Tempat'])
                
                ok = db.add_booking(user_id, tempat_id, str(tgl), qty, total)
                
                if ok:
                    st.success("🎉 Berhasil! Status Pesanan: PENDING.")
                    st.caption("Admin akan memverifikasi pesanan Anda.")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Gagal menyimpan pesanan.")

# --- 7. SIDEBAR (NAVIGASI) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/299/299901.png", width=50)
    st.markdown("### CariKemah")
    
    if st.session_state.user is None:
        st.info("Login untuk Booking")
        tab_log, tab_reg = st.tabs(["Masuk", "Daftar"])
        with tab_log:
            with st.form("f_login"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Login", use_container_width=True):
                    res = db.verify_login(u, p)
                    if res:
                        st.session_state.user = res
                        st.rerun()
                    else: st.error("Salah!")
        with tab_reg:
            with st.form("f_reg"):
                u = st.text_input("User Baru")
                p = st.text_input("Pass", type="password")
                if st.form_submit_button("Daftar"):
                    ok, msg = db.register_user(u, p)
                    if ok: st.success(msg)
                    else: st.error(msg)
    else:
        u = st.session_state.user
        role_label = "👑 ADMIN" if u['role'] == 'admin' else "👤 USER"
        st.success(f"Halo, {u['username']}\n\n{role_label}")
        
        if u['role'] == 'admin':
            menu = st.radio("Menu:", ["Dashboard Admin", "Logout"])
        else:
            menu = st.radio("Menu:", ["Pencarian", "Tiket Saya", "Logout"])
        
        if menu == "Logout":
            st.session_state.user = None
            st.rerun()

# --- 8. HALAMAN UTAMA ---

# A. HALAMAN ADMIN
if st.session_state.user and st.session_state.user['role'] == 'admin' and menu == "Dashboard Admin":
    st.title("📊 Admin Dashboard")
    df_adm = db.get_all_bookings_admin()
    if df_adm.empty: st.info("Tidak ada data.")
    else:
        # KPI
        c1, c2 = st.columns(2)
        rev = df_adm[df_adm['status']=='CONFIRMED']['total_harga'].sum()
        pen = len(df_adm[df_adm['status']=='PENDING'])
        c1.metric("Revenue (Confirmed)", format_rp(rev))
        c2.metric("Need Approval", pen)
        
        st.write("---")
        for i, row in df_adm.iterrows():
            with st.container(border=True):
                c_a, c_b, c_c = st.columns([3, 1, 1])
                c_a.markdown(f"**#{row['id']} {row['nama']}**")
                c_a.caption(f"User: {row['username']} | {row['tanggal_checkin']} | {format_rp(row['total_harga'])}")
                
                color = "orange" if row['status']=='PENDING' else "green" if row['status']=='CONFIRMED' else "red"
                c_b.markdown(f":{color}[{row['status']}]")
                
                if row['status'] == 'PENDING':
                    if c_c.button("✅ Acc", key=f"y{i}"):
                        db.update_booking_status(row['id'], 'CONFIRMED')
                        st.rerun()
                    if c_c.button("❌ Reject", key=f"n{i}"):
                        db.update_booking_status(row['id'], 'CANCELLED')
                        st.rerun()

# B. HALAMAN USER - TIKET
elif st.session_state.user and menu == "Tiket Saya":
    st.title("🎫 Tiket Saya")
    df = db.get_user_bookings(st.session_state.user['id'])
    if df.empty: st.info("Belum ada riwayat.")
    else:
        for i, row in df.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['nama']}**")
                st.write(f"📅 {row['tanggal_checkin']} | 💰 {format_rp(row['total_harga'])}")
                st.caption(f"Status: {row['status']}")

# C. HALAMAN PENCARIAN (DEFAULT)
else:
    st.markdown("""<div style="text-align: center; padding: 40px 0;">
        <h1>🏕️ CariKemah AI</h1>
        <p>Cari tempat camping di Jogja & Jateng dengan bahasa manusia.</p>
    </div>""", unsafe_allow_html=True)
    
    query = st.text_input("Pencarian", placeholder="Coba: 'Pemandangan bagus' atau 'Karimun Jawa'...", label_visibility="collapsed", on_change=run_search, key="query_input")
    
    df = st.session_state.search_results
    if not df.empty:
        st.write(f"Ditemukan {len(df)} tempat:")
        for i, (_, row) in enumerate(df.iterrows()):
            p_id = db.get_place_by_name(row['Nama Tempat'])
            detail = db.get_place_details(p_id)
            info = detail['info']
            
            # TAMPILAN CARD DENGAN GAMBAR
            with st.container(border=True):
                c_img, c_info = st.columns([1, 3])
                
                with c_img:
                    # Gambar Thumbnail
                    foto = info.get('photo_url')
                    if not foto: 
                        foto = f"https://placehold.co/400x300/333/FFF?text={urllib.parse.quote(row['Nama Tempat'][:10])}"
                    st.image(foto, use_container_width=True)
                
                with c_info:
                    st.subheader(row['Nama Tempat'])
                    st.caption(f"📍 {info.get('lokasi', row['Lokasi'])}")
                    # Fasilitas (Preview 3 biji)
                    fas_prev = detail['fasilitas'][:3]
                    if fas_prev:
                        st.markdown(" ".join([f"`{f}`" for f in fas_prev]) + " ...")
                    
                    st.write(f"\"{str(row['Isi Ulasan'])[:120]}...\"")
                    
                    if st.button(f"Lihat Detail & Booking", key=f"view_{i}", use_container_width=True):
                        show_details(row, detail, {})