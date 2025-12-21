import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

# PANGGIL PELAYAN DATABASE
try:
    from Asisten.db_handler import db
except ImportError:
    # Fallback kalau dijalankan manual dari folder Asisten
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Asisten.db_handler import db

# ================= KONFIGURASI PATH =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')

# Bobot Skor
WEIGHT_SEMANTIC = 0.7
WEIGHT_RECENCY = 0.3

# Kamus Sinonim Lokasi (Hard Filter)
REGION_MAP = {
    "jogja": ["yogyakarta", "jogja", "sleman", "bantul", "kulon progo", "gunung kidul", "kaliurang"],
    "yogya": ["yogyakarta", "jogja", "sleman", "bantul", "kulon progo", "gunung kidul"],
    "sleman": ["sleman", "kaliurang"],
    "semarang": ["semarang", "ungaran", "bandungan"],
    "magelang": ["magelang"],
    "wonosobo": ["wonosobo", "dieng"],
    "dieng": ["dieng", "wonosobo", "banjarnegara"],
    "kendal": ["kendal"],
    "batang": ["batang"]
}

class SmartSearchEngine:
    def __init__(self):
        self.model = None
        self.df = None
        self.doc_vectors = None
        self.is_ready = False
        self.load_resources()

    def load_resources(self):
        print(f"⚙️ [AI] Memuat Smart Search Engine dari Database...")
        
        # 1. LOAD DATA DARI DATABASE (Bukan CSV lagi!)
        try:
            conn = db.get_connection()
            # Kita gabungkan tabel Ulasan dengan Tempat
            # Agar AI tahu: "Ulasan ini milik tempat mana & lokasinya dimana"
            query = """
                SELECT 
                    u.teks_bersih, 
                    u.teks_mentah, 
                    u.waktu_ulasan as Waktu,
                    t.nama as Nama_Tempat, 
                    t.lokasi as Lokasi, 
                    t.rating_gmaps as Rating
                FROM ulasan u
                JOIN tempat t ON u.tempat_id = t.id
                WHERE u.teks_bersih IS NOT NULL AND u.teks_bersih != ''
            """
            self.df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Konversi Waktu & Bersihkan Data
            self.df['Waktu'] = pd.to_datetime(self.df['Waktu'], errors='coerce')
            self.df['Teks_Mentah'] = self.df['Teks_Mentah'].fillna("").astype(str)
            self.df['teks_bersih'] = self.df['teks_bersih'].fillna("").astype(str)
            self.df['Lokasi_Lower'] = self.df['Lokasi'].astype(str).str.lower()
            
            print(f"   📊 Data terload: {len(self.df)} ulasan.")

        except Exception as e:
            print(f"   ❌ Gagal load database: {e}")
            return

        # 2. LOAD MODEL WORD2VEC
        if os.path.exists(MODEL_PATH):
            try:
                self.model = Word2Vec.load(MODEL_PATH)
                print("   🧠 Model AI berhasil dimuat.")
            except: 
                print("   ⚠️ Model rusak/tidak cocok.")
                return
        else: 
            print("   ⚠️ File model word2vec.model tidak ditemukan.")
            return

        # 3. VEKTORISASI DOKUMEN (Pre-calculate)
        # Mengubah ribuan ulasan menjadi angka vektor saat startup
        if not self.df.empty and self.model:
            self.doc_vectors = np.array([self.get_vector(text) for text in self.df['teks_bersih']])
            self.is_ready = True
            print("✅ Search Engine SIAP (Database Powered).")
        else:
            print("❌ Search Engine GAGAL inisialisasi.")

    def get_vector(self, text):
        if not self.model: return np.zeros(100)
        # Tokenisasi sederhana
        words = str(text).split()
        # Ambil vektor kata yang dikenal model
        word_vecs = [self.model.wv[w] for w in words if w in self.model.wv]
        if len(word_vecs) == 0: return np.zeros(self.model.vector_size)
        return np.mean(word_vecs, axis=0)

    def calculate_recency_score(self, date_series):
        today = datetime.now()
        days_diff = (today - date_series).dt.days
        days_diff = days_diff.fillna(1825) # Default 5 tahun jika null
        days_diff = np.maximum(days_diff, 0)
        decay_rate = 0.001 
        return np.exp(-decay_rate * days_diff)

    def detect_region_filter(self, query):
        q_lower = query.lower()
        detected_regions = []
        for key, synonyms in REGION_MAP.items():
            if key in q_lower: 
                detected_regions.extend(synonyms)
        return detected_regions

    def search(self, query, top_k=50):
        if not self.is_ready: return pd.DataFrame()

        # 1. Hitung Skor Semantik (Kecocokan Kata)
        query_vec = self.get_vector(query).reshape(1, -1)
        semantic_scores = cosine_similarity(query_vec, self.doc_vectors)[0]
        # Normalisasi skor -1..1 menjadi 0..1
        semantic_scores = (semantic_scores + 1) / 2 
        
        # 2. Hitung Skor Waktu (Recency)
        recency_scores = self.calculate_recency_score(self.df['Waktu'])
        
        # 3. Skor Akhir Gabungan
        final_scores = (semantic_scores * WEIGHT_SEMANTIC) + (recency_scores * WEIGHT_RECENCY)

        # 4. FILTER LOKASI (HARD FILTER)
        target_regions = self.detect_region_filter(query)
        if target_regions:
            print(f"📍 Filter Wilayah Aktif: {target_regions}")
            mask = self.df['Lokasi_Lower'].apply(lambda x: any(r in x for r in target_regions))
            # Nol-kan skor yang lokasinya salah
            final_scores = final_scores * np.where(mask, 1.0, 0.0)

        # 5. Urutkan & Ambil Top K
        top_indices = final_scores.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if final_scores[idx] <= 0: continue # Skip sampah
            
            row = self.df.iloc[idx]
            tgl = row.get('Waktu', pd.NaT)
            tgl_str = tgl.strftime('%d %b %Y') if pd.notna(tgl) else "N/A"
            
            results.append({
                "Nama Tempat": row['Nama_Tempat'],
                "Lokasi": row['Lokasi'],
                "Rating": row['Rating'],
                "Tanggal Ulasan": tgl_str,
                "Isi Ulasan": row['Teks_Mentah'],
                "Skor Relevansi": round(final_scores[idx] * 100, 1)
            })
            
        return pd.DataFrame(results)

# Testing manual kalau dijalankan langsung
if __name__ == "__main__":
    engine = SmartSearchEngine()
    if engine.is_ready:
        print("\n--- Tes Pencarian: 'sejuk dingin' ---")
        res = engine.search("tempat kemah sejuk dingin", top_k=5)
        print(res[['Nama Tempat', 'Skor Relevansi']])