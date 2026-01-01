import os
import sys
import getpass
import pandas as pd
from datetime import datetime, timedelta

try:
    from tabulate import tabulate
except ImportError:
    print("❌ Library 'tabulate' belum terinstall.")
    sys.exit()

try:
    from Asisten.db_handler import db
    from Asisten.smart_search import SmartSearchEngine
except ImportError:
    print("❌ Gagal import modul.")
    sys.exit()

CURRENT_USER = None
SEARCH_ENGINE = None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    clear_screen()
    print("=" * 70)
    print(f"🏕️  CARIKEMAH SYSTEM (TERMINAL VERSION) | {title}")
    print("=" * 70)
    if CURRENT_USER:
        role_str = "👑 ADMIN" if CURRENT_USER['role'] == 'admin' else "👤 USER"
        print(f"Login sebagai: {CURRENT_USER['username']} | {role_str}")
        print("-" * 70)

def input_clean(prompt):
    return input(f"👉 {prompt}: ").strip()

def pause():
    input("\n[Tekan Enter untuk lanjut...]")

def format_rp(nilai):
    return f"Rp {int(nilai):,}".replace(",", ".")

def get_ai_engine():
    global SEARCH_ENGINE
    if SEARCH_ENGINE is None:
        print("\n[⏳] Sedang membangunkan AI (Word2Vec)... Mohon tunggu...")
        try:
            SEARCH_ENGINE = SmartSearchEngine()
            if SEARCH_ENGINE.is_ready:
                print("[✅] AI Siap digunakan!")
            else:
                print("[⚠️] AI Engine dimuat tapi model/data tidak lengkap.")
        except Exception as e:
            print(f"[❌] Error AI: {e}")
            return None
    return SEARCH_ENGINE

# ================= AUTH =================
def menu_auth():
    global CURRENT_USER
    while True:
        print_header("HALAMAN DEPAN")
        print("1. 🔐 Login")
        print("2. 📝 Daftar Akun Baru")
        print("3. 🛠️  Tools: Promosi User jadi Admin")
        print("0. ❌ Keluar")
        
        p = input_clean("Pilih menu")
        
        if p == '1':
            u = input_clean("Username")
            p = getpass.getpass("👉 Password: ")
            user = db.verify_login(u, p)
            if user:
                CURRENT_USER = user
                if user['role'] == 'admin': menu_admin_dashboard()
                else: menu_user_dashboard()
            else:
                print("\n❌ Login Gagal.")
                pause()
        elif p == '2':
            u = input_clean("Username Baru")
            p1 = getpass.getpass("👉 Password: ")
            p2 = getpass.getpass("👉 Ulangi Password: ")
            if p1 != p2: print("❌ Password tidak cocok!")
            else:
                sukses, msg = db.register_user(u, p1)
                print(f"✅ {msg}" if sukses else f"❌ {msg}")
            pause()
        elif p == '3':
            # Tools Admin
            u_target = input_clean("Username Target")
            code = getpass.getpass("👉 Kode Dev: ")
            if code == "dev":
                import sqlite3
                conn = sqlite3.connect('camping.db')
                conn.execute("UPDATE users SET role = 'admin' WHERE username = ?", (u_target,))
                conn.commit()
                conn.close()
                print("✅ Sukses jadi Admin.")
            else: print("❌ Kode salah.")
            pause()
        elif p == '0':
            sys.exit()

def do_logout():
    global CURRENT_USER
    CURRENT_USER = None

# ================= USER FLOW =================
def menu_user_dashboard():
    while True:
        if not CURRENT_USER: break
        print_header("USER DASHBOARD")
        print("1. 🔍 Cari Tempat Kemah")
        print("2. 🎫 Tiket Saya")
        print("0. 🚪 Logout")
        
        p = input_clean("Pilih")
        if p == '1': flow_pencarian()
        elif p == '2': flow_tiket_saya()
        elif p == '0': 
            do_logout()
            break

def flow_pencarian():
    engine = get_ai_engine()
    if not engine: 
        pause()
        return

    # Loop Utama Pencarian
    while True:
        print_header("PENCARIAN CERDAS (STKI)")
        query = input_clean("Apa yang Anda cari? (0 untuk batal)")
        
        if query == '0': break
        
        # 1. DAPATKAN HASIL
        df = engine.search(query, top_k=10)
        
        if df.empty:
            print("\n❌ Tidak ditemukan hasil.")
            pause()
            continue
            
        df = df.reset_index(drop=True)
        
        # Loop Tampilan Hasil
        while True:
            print_header(f"HASIL PENCARIAN: '{query}'")
            
            # Tampilkan Tabel
            display_df = df[['Nama Tempat', 'Lokasi', 'Skor Relevansi']].copy()
            # Kita tambah 1 biar user lihatnya mulai dari 1 (lebih manusiawi), tapi logic tetep 0-based
            display_df.index = display_df.index + 0 
            
            print(tabulate(display_df, headers="keys", tablefmt="simple", showindex=True))
            print(f"\n[Ditemukan {len(df)} tempat]")
            print("\n👉 Ketik No Index (0-9) untuk detail")
            print("👉 Ketik 'x' untuk cari kata kunci lain")
            
            pil = input_clean("Pilihan")
            
            if pil.lower() == 'x': 
                break 
            
            try:
                idx = int(pil)
                # Validasi index sesuai panjang data (bukan label)
                if 0 <= idx < len(df):
                    selected_row = df.iloc[idx]
                    sukses_booking = flow_detail_tempat(selected_row)
                    if sukses_booking: 
                        break 
                else:
                    print(f"❌ Nomor tidak valid. Masukkan angka 0 sampai {len(df)-1}.")
                    pause()
            except ValueError:
                pass

def flow_detail_tempat(row):
    nama = row['Nama Tempat']
    place_id = db.get_place_by_name(nama)
    detail = db.get_place_details(place_id)
    info = detail['info']
    
    print_header(f"DETAIL: {nama}")
    print(f"📍 Alamat : {info.get('lokasi', '-')}")
    print(f"⭐ Rating : {info.get('rating_gmaps', 0)} / 5.0")
    print("-" * 70)
    print("FASILITAS:")
    print(", ".join(detail['fasilitas']) if detail['fasilitas'] else "-")
    print("-" * 70)
    
    # Menampilkan Tabel Harga untuk Informasi
    print("💰 DAFTAR HARGA & OPSI:")
    price_list = detail['harga']
    if price_list:
        tabel_harga = pd.DataFrame(price_list)[['item', 'harga']]
        tabel_harga['harga'] = tabel_harga['harga'].apply(format_rp)
        print(tabulate(tabel_harga, headers=['Item', 'Biaya'], tablefmt="plain", showindex=False))
    else:
        print("Info harga tidak tersedia.")

    print("-" * 70)
    print("ULASAN RELEVAN:")
    print(f"\"{str(row['Isi Ulasan'])[:300]}...\"")
    print("-" * 70)
    
    print("\n1. 📝 Booking Tempat Ini")
    print("0. Kembali ke Hasil Pencarian")
    
    p = input_clean("Pilih")
    if p == '1':
        # [UPDATE] Kita lempar seluruh list harga ke fungsi booking
        return flow_booking_form(place_id, nama, price_list)
    else:
        return False

def flow_booking_form(place_id, nama_tempat, price_list):
    print_header("FORM RESERVASI (MPTI)")
    print(f"Booking untuk: {nama_tempat}")
    
    # 1. PILIH JENIS TIKET/PAKET (SOLUSI BARU)
    selected_item_name = "Tiket Masuk Umum"
    selected_price = 15000 # Fallback jika list kosong
    
    if price_list:
        print("\n📋 PILIH JENIS PESANAN:")
        # Tampilkan list dengan nomor index
        for i, item in enumerate(price_list):
            print(f"[{i+1}] {item['item']} -> {format_rp(item['harga'])}")
        
        # User wajib pilih
        while True:
            pil_str = input_clean("Pilih Nomor Item yang mau dipesan")
            try:
                idx = int(pil_str) - 1
                if 0 <= idx < len(price_list):
                    selected_item = price_list[idx]
                    selected_item_name = selected_item['item']
                    selected_price = int(selected_item['harga'])
                    break
                else:
                    print("❌ Nomor tidak ada di daftar.")
            except ValueError:
                print("❌ Masukkan angka.")
    else:
        print("\n⚠️ Data harga kosong. Menggunakan estimasi default Rp 15.000.")

    print("-" * 50)
    print(f"✅ Item Terpilih: {selected_item_name}")
    print(f"💰 Harga Satuan: {format_rp(selected_price)}")
    print("-" * 50)

    # 2. VALIDASI TANGGAL
    tgl_fix = None
    while True:
        tgl_str = input_clean("Tanggal Check-in (YYYY-MM-DD)")
        try:
            input_date = datetime.strptime(tgl_str, "%Y-%m-%d").date()
            if input_date < datetime.now().date():
                print("❌ Tanggal sudah lewat!")
            else:
                tgl_fix = tgl_str
                break
        except: print("❌ Format salah. Contoh: 2024-12-31")

    # 3. JUMLAH UNIT (ORANG/PAKET)
    qty_fix = 0
    while True:
        try:
            # Ubah prompt agar relevan (bisa Orang, bisa Paket)
            label_qty = "Jumlah Paket" if "paket" in selected_item_name.lower() else "Jumlah Orang"
            n = int(input_clean(f"{label_qty}"))
            
            if n < 1: print("❌ Minimal 1.")
            else:
                qty_fix = n
                break
        except: pass

    # 4. KONFIRMASI
    total = selected_price * qty_fix
    print("\n--- RINGKASAN PESANAN ---")
    print(f"🛒 Item    : {selected_item_name}")
    print(f"📅 Tanggal : {tgl_fix}")
    print(f"🔢 Jumlah  : {qty_fix}")
    print(f"💵 Total   : {format_rp(total)}")
    
    y = input_clean("Simpan Pesanan? (y/n)")
    if y.lower() == 'y':
        # Simpan booking ke DB
        ok = db.add_booking(CURRENT_USER['id'], place_id, tgl_fix, qty_fix, total)
        if ok:
            print("\n✅ Booking BERHASIL! Status: PENDING.")
            print("Silakan cek menu 'Tiket Saya'.")
            pause()
            return True 
        else:
            print("\n❌ Gagal menyimpan.")
    else:
        print("\n🚫 Batal.")
    
    pause()
    return False

def flow_tiket_saya():
    print_header("TIKET SAYA")
    df = db.get_user_bookings(CURRENT_USER['id'])
    if df.empty:
        print("📭 Belum ada booking.")
    else:
        view = df[['id', 'nama', 'tanggal_checkin', 'status', 'total_harga']].copy()
        view['total_harga'] = view['total_harga'].apply(format_rp)
        print(tabulate(view, headers=["ID", "Tempat", "Tanggal", "Status", "Total"], tablefmt="fancy_grid", showindex=False))
    pause()

# ================= ADMIN =================
def menu_admin_dashboard():
    while True:
        if not CURRENT_USER or CURRENT_USER['role'] != 'admin': break
        print_header("ADMIN DASHBOARD")
        df = db.get_all_bookings_admin()
        
        if df.empty: print("📭 Kosong.")
        else:
            view = df[['id', 'username', 'nama', 'tanggal_checkin', 'status']].head(10)
            print(tabulate(view, headers=["ID", "User", "Tempat", "Tanggal", "Status"], tablefmt="grid", showindex=False))
            
        print("\n1. ✅ Proses (Approve/Reject)")
        print("0. 🚪 Logout Admin")
        p = input_clean("Pilih")
        
        if p == '1':
            tid = input_clean("ID Transaksi")
            if tid.isdigit():
                act = input_clean("1=Terima, 2=Tolak")
                stat = 'CONFIRMED' if act == '1' else 'CANCELLED' if act == '2' else None
                if stat:
                    db.update_booking_status(tid, stat)
                    print(f"✅ Status -> {stat}")
            pause()
        elif p == '0':
            do_logout()
            break

if __name__ == "__main__":
    try: menu_auth()
    except KeyboardInterrupt: print("\nSTOP.")