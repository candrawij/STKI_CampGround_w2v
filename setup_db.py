import sqlite3
import os

# Nama File Database
DB_NAME = "camping.db"

def create_tables():
    print(f"⚙️ Membuat Database sesuai ERD Final: {DB_NAME}...")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabel TEMPAT
    # Sumber: info_tempat.csv & input_info_statis.csv
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tempat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL UNIQUE,
        lokasi TEXT,
        rating_gmaps REAL,
        gmaps_link TEXT,
        photo_url TEXT,
        waktu_buka TEXT,  -- Kolom baru request user
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 2. Tabel ULASAN
    # Sumber: corpus_master.csv & Data_Mentah
    # Note: user_name dihapus sesuai CSV yang ada
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ulasan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tempat_id INTEGER NOT NULL,
        rating_user INTEGER,
        teks_mentah TEXT,
        teks_bersih TEXT,
        waktu_ulasan DATE,
        tanggal_scrap DATE,
        FOREIGN KEY (tempat_id) REFERENCES tempat (id) ON DELETE CASCADE
    )
    ''')
    
    # 3. Tabel HARGA
    # Sumber: input_harga.csv
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS harga (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tempat_id INTEGER NOT NULL,
        item TEXT,
        harga INTEGER,
        kategori TEXT,
        FOREIGN KEY (tempat_id) REFERENCES tempat (id) ON DELETE CASCADE
    )
    ''')
    
    # 4. Tabel FASILITAS
    # Sumber: input_fasilitas.csv
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fasilitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tempat_id INTEGER NOT NULL,
        nama_fasilitas TEXT,
        FOREIGN KEY (tempat_id) REFERENCES tempat (id) ON DELETE CASCADE
    )
    ''')

    # 5. Tabel RIWAYAT
    # Sumber: riwayat_pencarian.csv
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS riwayat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        waktu TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        query_user TEXT,
        jumlah_hasil INTEGER,
        durasi_detik REAL
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Struktur Database Berhasil Dibuat!")
    print("   📋 Tabel Terbentuk: TEMPAT, ULASAN, HARGA, FASILITAS")

if __name__ == "__main__":
    create_tables()