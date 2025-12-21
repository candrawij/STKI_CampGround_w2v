import sqlite3
import pandas as pd
import os
from datetime import datetime

# ================= KONFIGURASI =================
# Mencari lokasi file database secara otomatis
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR) # Naik satu level ke root
DB_PATH = os.path.join(BASE_DIR, 'camping.db')

class DBHandler:
    def __init__(self):
        self.db_path = DB_PATH

    def get_connection(self):
        """Membuat koneksi ke database SQLite"""
        conn = sqlite3.connect(self.db_path)
        # Agar hasil query bisa diakses pakai nama kolom (dict-like)
        conn.row_factory = sqlite3.Row 
        return conn

    # --- FITUR 1: UNTUK TAMPILAN APP (Streamlit) ---
    
    def get_all_places(self):
        """Mengambil semua daftar tempat kemah"""
        conn = self.get_connection()
        query = "SELECT id, nama, lokasi, rating_gmaps, photo_url, gmaps_link FROM tempat"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_place_details(self, place_id):
        """Mengambil detail lengkap satu tempat (Harga & Fasilitas)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Info Utama
        cursor.execute("SELECT * FROM tempat WHERE id = ?", (place_id,))
        place = cursor.fetchone()
        
        if not place:
            conn.close()
            return None

        # 2. Ambil Harga
        cursor.execute("SELECT item, harga, kategori FROM harga WHERE tempat_id = ?", (place_id,))
        prices = [dict(row) for row in cursor.fetchall()]

        # 3. Ambil Fasilitas
        cursor.execute("SELECT nama_fasilitas FROM fasilitas WHERE tempat_id = ?", (place_id,))
        facilities = [row['nama_fasilitas'] for row in cursor.fetchall()]
        
        conn.close()
        
        # Gabungkan jadi satu dictionary rapi
        return {
            "info": dict(place),
            "harga": prices,
            "fasilitas": facilities
        }
        
    def get_place_by_name(self, nama_tempat):
        """Mencari ID tempat berdasarkan nama (Case Insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tempat WHERE nama LIKE ? LIMIT 1", (f"%{nama_tempat}%",))
        res = cursor.fetchone()
        conn.close()
        return res['id'] if res else None

    # --- FITUR 2: UNTUK OTAK AI (Training) ---

    def get_corpus_for_ai(self):
        """Mengambil teks bersih untuk training Word2Vec"""
        conn = self.get_connection()
        # Ambil ulasan yang teks_bersih-nya tidak kosong
        query = "SELECT teks_bersih FROM ulasan WHERE teks_bersih IS NOT NULL AND teks_bersih != ''"
        df = pd.read_sql_query(query, conn)
        conn.close()
        # Return list of strings
        return df['teks_bersih'].tolist()
    
    def get_reviews_by_place(self, place_id):
        """Mengambil ulasan mentah untuk ditampilkan di UI"""
        conn = self.get_connection()
        query = """
            SELECT user_name, rating_user, teks_mentah, waktu_ulasan 
            FROM ulasan 
            WHERE tempat_id = ? 
            ORDER BY waktu_ulasan DESC 
            LIMIT 10
        """
        # Gunakan params agar aman dari SQL Injection
        df = pd.read_sql_query(query, conn, params=(place_id,))
        conn.close()
        return df

    # --- FITUR 3: PENCATATAN RIWAYAT ---

    def log_search(self, query_user, jumlah_hasil):
        """Menyimpan riwayat pencarian user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO riwayat (query_user, jumlah_hasil) 
                VALUES (?, ?)
            ''', (query_user, jumlah_hasil))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ Gagal simpan log: {e}")

    def get_search_history(self, limit=50):
        """Untuk Admin Panel: Melihat log pencarian"""
        conn = self.get_connection()
        query = "SELECT waktu, query_user, jumlah_hasil FROM riwayat ORDER BY waktu DESC LIMIT ?"
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df

# Helper instan biar file lain tinggal import 'db'
db = DBHandler()