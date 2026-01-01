import re
import os
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from . import utils 

# ======================================================================
# 1. STOPWORDS & NEGASI (FITUR LAMA DIKEMBALIKAN)
# ======================================================================
# Kita coba pakai NLTK dulu (karena logikanya bagus untuk negasi).
# Jika gagal, baru pakai file text atau set manual.

try:
    from nltk.corpus import stopwords
    # Pastikan user sudah download: nltk.download('stopwords')
    STOPWORDS = set(stopwords.words('indonesian'))
    
    # --- PENTING: Jangan buang kata negasi ---
    # Agar "tidak bersih" tidak menjadi "bersih"
    NEGATION_WORDS = {'tidak', 'kurang', 'jangan', 'bukan', 'tanpa', 'enggak', 'gak', 'nggak', 'ndak', 'tak', 'kecuali'}
    
    for word in NEGATION_WORDS:
        if word in STOPWORDS:
            STOPWORDS.remove(word)
            
    print("✅ Stopwords NLTK (dengan Negasi aman) dimuat.")

except Exception as e:
    print(f"⚠️ NLTK tidak ditemukan/error ({e}). Menggunakan Fallback.")
    # Fallback: Stopwords dasar + baca file jika ada
    STOPWORDS = {'yang', 'dan', 'di', 'ke', 'dari', 'ini', 'itu', 'untuk', 'pada', 'adalah'}
    
    # Coba baca file stopwords_id.txt jika ada
    SRC_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(SRC_DIR)
    stopwords_path = os.path.join(BASE_DIR, 'Kamus', 'stopwords_id.txt')
    if os.path.exists(stopwords_path):
        with open(stopwords_path, 'r') as f:
            file_stopwords = set(f.read().splitlines())
            # Hapus negasi dari file juga
            NEGATION_WORDS = {'tidak', 'kurang', 'jangan', 'bukan', 'tanpa', 'enggak', 'gak', 'nggak'}
            STOPWORDS = file_stopwords - NEGATION_WORDS

# ======================================================================
# 2. INISIALISASI STEMMER & KAMUS
# ======================================================================
try:
    factory = StemmerFactory()
    stemmer = factory.create_stemmer()
except:
    # Dummy jika Sastrawi error (jarang terjadi)
    class Dummy: 
        def stem(self, t): return t
    stemmer = Dummy()

# Muat Kamus Mapping
print("--- Memuat Kamus Mapping ---")
PHRASE_MAP = utils.load_map_from_csv('config_phrase_map.csv')
REGION_MAP = utils.load_map_from_csv('config_region_map.csv')
INTENT_MAP = utils.load_map_from_csv('config_special_intent.csv')

# --- OPTIMALISASI: Pre-compile Regex untuk Phrase Map ---
# Ini teknik kode baru agar penggantian kata JAUH lebih cepat daripada loop biasa
# Kita urutkan dari frase terpanjang agar tidak salah ganti
sorted_phrases = sorted(PHRASE_MAP.keys(), key=len, reverse=True)
if sorted_phrases:
    regex_pattern = re.compile(r'\b(' + '|'.join(map(re.escape, sorted_phrases)) + r')\b')
else:
    regex_pattern = None

def replace_phrase(match):
    return PHRASE_MAP[match.group(0)]

# ======================================================================
# 3. FUNGSI PREPROCESSING UTAMA
# ======================================================================

def full_preprocessing(text):
    """
    Pipeline Lengkap: 
    Regex Clean -> Phrase Map (Gaul/Typo) -> Tokenize -> Stopword -> Stemming
    """
    if not isinstance(text, str): return []
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Hapus karakter selain huruf & angka (Regex Dasar)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # 3. Phrase Mapping (Gunakan Regex Cepat)
    # Mengubah "ga enak" -> "tidak enak", "jogja" -> "diy"
    if regex_pattern:
        text = regex_pattern.sub(replace_phrase, text)
    
    # 4. Tokenisasi
    tokens = text.split()
    
    # 5. Stopword Removal & Stemming
    final_tokens = []
    for t in tokens:
        if t not in STOPWORDS and len(t) > 1:
            # Stemming kita AKTIFKAN KEMBALI agar data latih lebih padat
            # "makanan" -> "makan", "berkemah" -> "kemah"
            stemmed_word = stemmer.stem(t)
            
            # Cek lagi panjang kata setelah distem (kadang jadi kpendekan)
            if len(stemmed_word) > 1:
                final_tokens.append(stemmed_word)
            
    return final_tokens

# ======================================================================
# 4. FUNGSI DETEKSI INTENT & REGION
# ======================================================================

def detect_intent(query):
    query = query.lower()
    detected_intent = None
    
    # Urutkan key terpanjang dulu
    sorted_intents = sorted(INTENT_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    
    for phrase, code in sorted_intents:
        if phrase in query:
            detected_intent = code
            query = query.replace(phrase, "")
            break
    return query, detected_intent

def detect_region_and_filter_query(query):
    query_lower = query.lower()
    detected_region = None
    
    # Urutkan key terpanjang dulu
    sorted_regions = sorted(REGION_MAP.items(), key=lambda x: len(x[0]), reverse=True)
    
    for term, region_code in sorted_regions:
        if term in query_lower:
            detected_region = region_code
            # Opsional: hapus nama kota dari query agar bersih
            # query_lower = query_lower.replace(term, "") 
            break
    return query_lower, detected_region