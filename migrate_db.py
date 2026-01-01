import pandas as pd
import sqlite3
import os
import ast
import csv

# ================= KONFIGURASI =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'Documents')
RIWAYAT_DIR = os.path.join(BASE_DIR, 'Riwayat') # Folder log pencarian
DB_PATH = os.path.join(BASE_DIR, 'camping.db')

# File Sumber
FILE_INFO_TEMPAT = os.path.join(DOCS_DIR, 'info_tempat.csv')
FILE_CORPUS_MASTER = os.path.join(DOCS_DIR, 'corpus_master.csv')
FILE_INPUT_HARGA = os.path.join(DOCS_DIR, 'input_harga.csv')
FILE_INPUT_FASILITAS = os.path.join(DOCS_DIR, 'input_fasilitas.csv')
FILE_RIWAYAT = os.path.join(RIWAYAT_DIR, 'riwayat_pencarian.csv') # Sumber Riwayat

# Cache Memori
NAME_TO_ID_MAP = {}

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def standardize_name(name):
    return str(name).strip().title()

def upsert_place(cursor, nama, lokasi="-", rating=0.0, gmaps="", photo="", buka=""):
    nama_clean = standardize_name(nama)
    
    # [FIX] Mapping Kaliurip manual jika belum di-clean
    if "Kaliurip Mount" in nama_clean: nama_clean = "Gunung Cilik Kaliurip"
    if "Gunung Cilik Kaliurip Wonosobo" in nama_clean: nama_clean = "Gunung Cilik Kaliurip"

    cursor.execute("SELECT id, lokasi, rating_gmaps FROM tempat WHERE nama = ?", (nama_clean,))
    res = cursor.fetchone()
    
    if res:
        place_id, db_lokasi, db_rating = res
        # Update Pintar
        update_query, update_vals = [], []
        
        if (db_lokasi == "-" or db_lokasi == "") and (lokasi != "-" and lokasi != ""):
            update_query.append("lokasi = ?"); update_vals.append(lokasi)
        if (db_rating == 0.0) and (rating > 0.0):
            update_query.append("rating_gmaps = ?"); update_vals.append(rating)
        if gmaps: 
            update_query.append("gmaps_link = ?"); update_vals.append(gmaps)
        if photo: 
            update_query.append("photo_url = ?"); update_vals.append(photo)
        if buka:
            update_query.append("waktu_buka = ?"); update_vals.append(buka)

        if update_query:
            sql = f"UPDATE tempat SET {', '.join(update_query)} WHERE id = ?"
            update_vals.append(place_id)
            cursor.execute(sql, tuple(update_vals))
            
        NAME_TO_ID_MAP[nama_clean] = place_id
        return place_id
    else:
        try:
            cursor.execute('''
                INSERT INTO tempat (nama, lokasi, rating_gmaps, gmaps_link, photo_url, waktu_buka)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nama_clean, lokasi, rating, gmaps, photo, buka))
            place_id = cursor.lastrowid
            NAME_TO_ID_MAP[nama_clean] = place_id
            return place_id
        except sqlite3.IntegrityError: return None

def migrate_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF")

    print("\n🚀 TAHAP 1: Migrasi Data TEMPAT (Master)...")
    
    if os.path.exists(FILE_INFO_TEMPAT):
        df = pd.read_csv(FILE_INFO_TEMPAT).fillna("")
        print(f"   📄 info_tempat.csv: {len(df)} baris")
        for _, row in df.iterrows():
            upsert_place(cursor, row.get('Nama_Tempat'), 
                         gmaps=row.get('Gmaps_Link', ''), 
                         photo=row.get('Photo_URL', ''), 
                         buka=row.get('Waktu_Buka', ''))
            
            # Harga Default (Akan ditimpa jika ada input_harga.csv)
            # Logika: Insert dulu, nanti dihapus kalau ada yang lebih bagus
            p_id = NAME_TO_ID_MAP.get(standardize_name(row.get('Nama_Tempat')))
            if p_id and row.get('Price_Items'):
                try:
                    items = ast.literal_eval(row['Price_Items'])
                    if isinstance(items, list):
                        # Cek apakah sudah ada harga? Kalau belum baru insert
                        cek = cursor.execute("SELECT COUNT(*) FROM harga WHERE tempat_id=?", (p_id,)).fetchone()[0]
                        if cek == 0:
                            for it in items:
                                cursor.execute("INSERT INTO harga (tempat_id, item, harga, kategori) VALUES (?, ?, ?, ?)",
                                               (p_id, it.get('item',''), it.get('harga',0), 'Umum'))
                except: pass

    # 2. BACA CORPUS MASTER (Perbaikan Rating User 0)
    print("\n🚀 TAHAP 2: Migrasi ULASAN (Fix Rating User)...")
    if os.path.exists(FILE_CORPUS_MASTER):
        df = pd.read_csv(FILE_CORPUS_MASTER).fillna("")
        print(f"   📄 corpus_master.csv: {len(df)} baris")
        
        count = 0
        for _, row in df.iterrows():
            p_id = upsert_place(cursor, row.get('Nama_Tempat'), 
                                lokasi=row.get('Lokasi', '-'), 
                                rating=row.get('Rating', 0.0)) # Rating Tempat
            
            if p_id:
                raw = row.get('Teks_Mentah', '')
                clean = str(raw).lower()
                
                # [FIX] Ambil Rating User dari CSV, jika kosong kasih 0
                user_rating = row.get('Rating', 0) 
                # Kadang CSV ratingnya float 5.0, kita ambil int 5
                try: user_rating = int(float(user_rating))
                except: user_rating = 0

                # [FIX] Ambil Tanggal Scrap
                tgl_scrap = row.get('Tanggal_Scrap', None)
                
                cursor.execute('''
                    INSERT INTO ulasan (tempat_id, rating_user, teks_mentah, teks_bersih, waktu_ulasan, tanggal_scrap)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (p_id, user_rating, raw, clean, row.get('Waktu'), tgl_scrap))
                count += 1
                if count % 2000 == 0: print(f"      ⏳ {count}...")

    # 3. HARGA & FASILITAS TAMBAHAN (Prioritas Tinggi)
    if os.path.exists(FILE_INPUT_HARGA):
        print("\n🚀 TAHAP 3: Data Harga Manual (Override)...")
        df_hrg = pd.read_csv(FILE_INPUT_HARGA).fillna("")
        processed_ids = set()
        
        for _, row in df_hrg.iterrows():
            p_id = upsert_place(cursor, row.get('Nama_Tempat'))
            if p_id:
                # [FIX] Hapus harga lama (versi 'Umum') agar tidak ganda
                if p_id not in processed_ids:
                    cursor.execute("DELETE FROM harga WHERE tempat_id = ?", (p_id,))
                    processed_ids.add(p_id)
                
                cursor.execute("INSERT INTO harga (tempat_id, item, harga, kategori) VALUES (?, ?, ?, ?)",
                               (p_id, row.get('item'), row.get('harga', 0), row.get('kategori', '')))

    if os.path.exists(FILE_INPUT_FASILITAS):
        df_fas = pd.read_csv(FILE_INPUT_FASILITAS).fillna("")
        for _, row in df_fas.iterrows():
            p_id = upsert_place(cursor, row.get('Nama_Tempat'))
            if p_id:
                cursor.execute("INSERT INTO fasilitas (tempat_id, nama_fasilitas) VALUES (?, ?)",
                               (p_id, row.get('Fasilitas')))
                               
    # 4. MIGRASI RIWAYAT
    print("\n🚀 TAHAP 4: Migrasi Riwayat Pencarian...")
    if os.path.exists(FILE_RIWAYAT):
        try:
            # Baca CSV manual karena kadang error tokenizing kalau pakai pandas
            with open(FILE_RIWAYAT, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                header = next(reader, None) # Skip header
                count_riwayat = 0
                for row in reader:
                    if len(row) >= 2:
                        waktu = row[0]
                        query = row[1]
                        hasil = row[2] if len(row) > 2 else 0
                        cursor.execute("INSERT INTO riwayat (waktu, query_user, jumlah_hasil) VALUES (?, ?, ?)",
                                       (waktu, query, hasil))
                        count_riwayat += 1
            print(f"   📜 Berhasil memindahkan {count_riwayat} log pencarian.")
        except Exception as e:
            print(f"   ⚠️ Gagal baca riwayat: {e}")
    else:
        print("   ⚠️ File riwayat_pencarian.csv tidak ditemukan. Tabel riwayat kosong.")

    conn.commit()
    conn.close()
    print("\n✅ SEMUA MIGRASI SELESAI.")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except: pass
    
    import setup_db
    setup_db.create_tables()
    migrate_data()