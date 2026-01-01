import pandas as pd
import numpy as np
import os
import urllib.parse
import joblib
import streamlit as st
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity
from . import preprocessing
from . import utils

# ======================================================================
# 1. VARIABEL GLOBAL (OTAK AI)
# ======================================================================
MODEL_W2V = None      # Otak Kecerdasan Buatan
DF_CORPUS = None      # Data Teks Ulasan
DOC_VECTORS = None    # Matriks Vektor Dokumen (Cache agar cepat)
DF_METADATA = None    # Data Harga/Foto

# Konfigurasi Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')
CORPUS_PATH = os.path.join(BASE_DIR, 'Documents', 'corpus_master.csv')

# Bobot Ranking
BOBOT_AI = 0.7        # 70% Kecocokan Makna
BOBOT_RATING = 0.3    # 30% Kualitas Tempat (Bintang)

# ======================================================================
# 2. FUNGSI INISIALISASI (Dipanggil saat aplikasi mulai)
# ======================================================================
def initialize_mesin():
    """Memuat Model AI, Corpus, dan Metadata."""
    global MODEL_W2V, DF_CORPUS, DOC_VECTORS, DF_METADATA
    
    print("--- 🚀 Memuat Mesin Deep Learning (Word2Vec)... ---")
    
    # 1. Load Metadata (Harga/Foto)
    DF_METADATA = utils.load_metadata()
    
    # 2. Load Model Word2Vec
    if os.path.exists(MODEL_PATH):
        MODEL_W2V = Word2Vec.load(MODEL_PATH)
        print("✅ Model AI Loaded.")
    else:
        print("❌ FATAL: Model AI tidak ditemukan. Jalankan 'train_w2v.py' dulu!")
        return

    # 3. Load Corpus & Pre-calculate Vectors
    if os.path.exists(CORPUS_PATH):
        DF_CORPUS = pd.read_csv(CORPUS_PATH)
        
        # Hitung vektor untuk semua dokumen SEKARANG (biar pencarian ngebut)
        print("⚙️ Menghitung vektor dokumen...")
        DF_CORPUS['Vector'] = DF_CORPUS['Teks_Mentah'].apply(_get_text_vector)
        
        # Simpan sebagai matrix numpy
        DOC_VECTORS = np.array(DF_CORPUS['Vector'].tolist())
        print(f"✅ Siap mencari di {len(DF_CORPUS)} ulasan.")
    else:
        print("❌ FATAL: Corpus master tidak ditemukan!")

# ======================================================================
# 3. FUNGSI PENDUKUNG (VECTORIZATION)
# ======================================================================
def _get_text_vector(text):
    """Mengubah teks menjadi vektor matematika (Rata-rata vektor kata)."""
    if MODEL_W2V is None: return np.zeros(100)
    
    # Gunakan preprocessing yang sama
    # Jika input berupa list token, pakai langsung. Jika string, split dulu.
    if isinstance(text, list):
        tokens = text
    else:
        tokens = preprocessing.full_preprocessing(str(text))
    
    if not tokens: return np.zeros(MODEL_W2V.vector_size)
    
    # Ambil vektor tiap kata
    vectors = [MODEL_W2V.wv[word] for word in tokens if word in MODEL_W2V.wv]
    
    if vectors:
        return np.mean(vectors, axis=0) # Rata-rata vektor
    else:
        return np.zeros(MODEL_W2V.vector_size)

# Wrapper agar kompatibel dengan kode lama yang memanggil 'analyze_full_query'
def analyze_full_query(query_text):
    """Sama seperti lama: deteksi intent & region."""
    query_after_intent, special_intent = preprocessing.detect_intent(query_text)
    final_vsm_text, region_filter = preprocessing.detect_region_and_filter_query(query_after_intent)
    vsm_tokens = preprocessing.full_preprocessing(final_vsm_text)
    return vsm_tokens, special_intent, region_filter

# ======================================================================
# 4. FUNGSI PENCARIAN UTAMA
# ======================================================================
def search_by_keyword(query_tokens, special_intent, region_filter):
    """
    Fungsi Utama. Menerima token, mengembalikan rekomendasi format UI.
    """
    # --- JALUR 1: REKOMENDASI UMUM (INTENT 'ALL') ---
    if special_intent == 'ALL':
        return _get_all_places(region_filter)

    # --- JALUR 2: PENCARIAN DEEP LEARNING (VECTOR SEARCH) ---
    if MODEL_W2V is None or DF_CORPUS is None:
        return []

    # 1. Ubah Query jadi Vektor
    # Gabungkan tokens kembali jadi string karena kita butuh konteks (opsional)
    query_vector = _get_text_vector(query_tokens)
    
    if np.all(query_vector == 0): return [] # Kata tidak dikenali AI

    # 2. Hitung Kemiripan (Cosine Similarity)
    # Bandingkan 1 vektor query vs Ribuan vektor dokumen
    similarities = cosine_similarity([query_vector], DOC_VECTORS)[0]
    
    # 3. Ranking & Formatting
    candidates = []
    
    for idx, score_sim in enumerate(similarities):
        # Threshold: Hanya ambil yang agak mirip (> 0.1)
        if score_sim > 0.1:
            row = DF_CORPUS.iloc[idx]
            
            # Filter Region (Kabupaten)
            if region_filter and region_filter not in str(row['Lokasi']).lower():
                continue

            # Skor Gabungan (AI + Rating)
            # Normalisasi Rating 0-5 menjadi 0-1
            rating_norm = float(row['Rating']) / 5.0
            final_score = (score_sim * BOBOT_AI) + (rating_norm * BOBOT_RATING)
            
            candidates.append({
                'name': row['Nama_Tempat'],
                'location': row['Lokasi'],
                'avg_rating': float(row['Rating']),
                'top_vsm_score': float(final_score), # Kita pakai nama 'vsm_score' biar frontend gak error
                'ai_score': float(score_sim),        # Info tambahan debug
                'snippet': str(row['Teks_Mentah'])[:100] + "..."
            })
    
    # 4. Urutkan Ranking
    candidates = sorted(candidates, key=lambda x: x['top_vsm_score'], reverse=True)
    
    # 5. Grouping (Ambil Metadata Lengkap)
    final_results = _enrich_with_metadata(candidates)
    
    # Sorting Tambahan jika User minta
    if special_intent == 'RATING_TOP':
        final_results.sort(key=lambda x: x['avg_rating'], reverse=True)
    elif special_intent == 'RATING_BOTTOM':
        final_results.sort(key=lambda x: x['avg_rating'], reverse=False)
        
    # Logging
    try:
        query_str = " ".join(query_tokens)
        utils.log_pencarian_csv(query_str, intent="search", region=region_filter or "all")
    except: pass

    return final_results

# ======================================================================
# 5. HELPER: FORMATTING OUTPUT
# ======================================================================
def _enrich_with_metadata(candidates):
    """Menggabungkan hasil pencarian dengan Foto, Harga, Fasilitas."""
    unique_results = []
    seen_places = set()
    
    for item in candidates:
        name = item['name']
        if name in seen_places: continue
        
        # Ambil Metadata
        meta_row = None
        if not DF_METADATA.empty and name in DF_METADATA.index:
            meta_row = DF_METADATA.loc[name]
        
        # Siapkan Data Tampilan
        photo_url = ""
        gmaps_link = ""
        facilities = ""
        price_items = []
        waktu_buka = "Info tidak tersedia"
        
        if meta_row is not None:
            photo_url = meta_row.get('Photo_URL', '')
            gmaps_link = meta_row.get('Gmaps_Link', '')
            facilities = meta_row.get('Facilities', '')
            price_items = meta_row.get('Price_Items', [])
            waktu_buka = meta_row.get('Waktu_Buka', 'Info tidak tersedia')
            
            # Cek jika price masih string (kadang terjadi)
            if isinstance(price_items, str): price_items = []
        
        # Fallback Image
        if not photo_url or pd.isna(photo_url):
            safe_name = urllib.parse.quote(name)
            photo_url = f"https://placehold.co/400x200/2E8B57/FFFFFF?text={safe_name}&font=poppins"
            
        item.update({
            'photo_url': photo_url,
            'gmaps_link': gmaps_link,
            'facilities': facilities,
            'price_items': price_items,
            'waktu_buka': waktu_buka
        })
        
        unique_results.append(item)
        seen_places.add(name)
        
        if len(unique_results) >= 20: break # Batasi 20 hasil
        
    return unique_results

def _get_all_places(region_filter):
    """Mengembalikan semua tempat (Logika 'Lihat Semua')."""
    if DF_METADATA.empty: return []
    
    df_show = DF_METADATA.reset_index().drop_duplicates(subset='Nama_Tempat')
    
    if region_filter:
        df_show = df_show[df_show['Lokasi'].str.lower().str.contains(region_filter, na=False)]
        
    # Format agar sama dengan output search
    results = []
    for _, row in df_show.iterrows():
        results.append({
            'name': row['Nama_Tempat'],
            'location': row['Lokasi'],
            'avg_rating': row['Avg_Rating'],
            'top_vsm_score': 0.0,
        })
        
    return _enrich_with_metadata(results)