import pandas as pd
import numpy as np
import os
import re
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

# DATABASE HANDLER
try:
    from Asisten.db_handler import db
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Asisten.db_handler import db

# PATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')

# BOBOT (Keyword dominan untuk akurasi teks)
WEIGHT_SEMANTIC = 0.3
WEIGHT_KEYWORD = 0.7

# STOPWORDS
STOPWORDS = ["tempat", "lokasi", "di", "ke", "yang", "dan", "ini", "itu", "ada", "buat", "sangat", "banget", "untuk", "yg", "juga", "dengan", "secara", "karena", "kalo", "sih", "nya", "dr", "dari", "wisata", "camping", "ground", "kemah"]

# NEGASI
NEGATION_WORDS = ["tidak", "gak", "kurang", "jangan", "bukan", "no", "ga", "minus", "sayang", "kecewa", "tapi", "belum", "agak", "cuma", "hanya"]

# ANTONIM
ANTONYM_MAP = {
    "bersih": ["kotor", "jorok", "bau", "sampah", "berantakan", "kumuh", "licin", "kurang"],
    "luas": ["sempit", "sesak", "kecil", "padat"],
    "dingin": ["panas", "gerah", "sumuk"],
    "sepi": ["ramai", "berisik", "padat", "gaduh", "pasar"],
    "tenang": ["berisik", "ramai", "gaduh", "terganggu"],
    "murah": ["mahal", "pricey", "nembak", "boros"],
    "bagus": ["jelek", "buruk", "kecewa", "zonk", "biasa", "kurang"],
    "ramah": ["jutek", "galak", "kasar", "cuek", "lambat"],
    "aman": ["rawan", "takut", "bahaya", "hilang"],
    "pemandanganindah": ["jelek", "buruk", "biasa", "ketutup", "halang", "kecewa", "zonk"]
}

# SINONIM
KEYWORD_SYNONYMS = {
    "angker": ["seram", "mistis", "hantu", "menakutkan", "gelap", "kuntilanak", "pocong", "wingit", "singup"],
    "kamar mandi": ["toilet", "wc", "klozet", "mck", "kamar kecil", "km/wc", "kamar"],
    "bagus": ["indah", "keren", "cakep", "jos", "mantap", "memukau", "estetik", "juara", "ok", "best", "good", "nice", "top"],
    "bersih": ["terawat", "kinclong", "rapi", "higienis", "wangi"],
    "sejuk": ["dingin", "adem", "segar", "asri", "kabut"],
    "listrik": ["colokan", "stop kontak", "charging", "cas", "kabel", "cok"],
    "sungai": ["kali", "river", "air", "aliran", "gemericik", "water"],
    "pemandangan": ["view", "panorama", "landscape", "scenery", "alam", "gunung", "bukit"],
    "pemandanganindah": ["pemandangan", "view", "panorama", "alam", "landscape", "gunung", "bukit"] 
}

class SmartSearchEngine:
    def __init__(self):
        self.model = None
        self.df = None
        self.doc_vectors = None
        self.is_ready = False
        self.phrase_dict = {}     
        self.reverse_phrase = {} 
        self.region_dict = {}
        self.intent_dict = {}
        self.load_configs()
        self.load_resources()

    def _find_file(self, filename):
        possible_paths = [
            os.path.join(BASE_DIR, filename),
            os.path.join(BASE_DIR, 'Kamus', filename),
            os.path.join(BASE_DIR, 'Asisten', filename),
            os.path.join(BASE_DIR, 'Asisten', 'Kamus', filename)
        ]
        for path in possible_paths:
            if os.path.exists(path): return path
        return None

    def load_configs(self):
        try:
            path_ph = self._find_file('config_phrase_map.csv')
            if path_ph:
                df_ph = pd.read_csv(path_ph)
                df_ph['len'] = df_ph['Phrase'].str.len()
                sorted_ph = df_ph.sort_values('len', ascending=False)
                self.phrase_dict = dict(zip(sorted_ph['Phrase'], sorted_ph['Token']))
                for _, row in sorted_ph.iterrows():
                    token = row['Token']
                    phrase = row['Phrase']
                    if token not in self.reverse_phrase: self.reverse_phrase[token] = []
                    self.reverse_phrase[token].append(phrase)

            path_rg = self._find_file('config_region_map.csv')
            if path_rg:
                df_rg = pd.read_csv(path_rg)
                for _, row in df_rg.iterrows():
                    code = str(row['region_code']).lower()
                    term = str(row['location_term']).lower()
                    if code not in self.region_dict: self.region_dict[code] = []
                    self.region_dict[code].append(term)

            path_in = self._find_file('config_special_intent.csv')
            if path_in:
                df_in = pd.read_csv(path_in)
                self.intent_dict = dict(zip(df_in['intent_phrase'], df_in['intent_code']))
        except Exception as e: print(f"⚠️ Config Error: {e}")

    def load_resources(self):
        try:
            conn = db.get_connection()
            query = """SELECT u.teks_bersih, u.teks_mentah, u.waktu_ulasan, t.nama, t.lokasi, t.rating_gmaps 
                       FROM ulasan u JOIN tempat t ON u.tempat_id = t.id 
                       WHERE u.teks_bersih IS NOT NULL AND u.teks_bersih != ''"""
            self.df = pd.read_sql_query(query, conn)
            conn.close()
            
            self.df['teks_mentah'] = self.df['teks_mentah'].fillna("").astype(str)
            self.df['teks_bersih'] = self.df['teks_bersih'].fillna("").astype(str)
            self.df['lokasi_lower'] = self.df['lokasi'].astype(str).str.lower()
            self.df['nama_lower'] = self.df['nama'].astype(str).str.lower() # [BARU] Kolom nama lowercase
            self.df['rating_gmaps'] = pd.to_numeric(self.df['rating_gmaps'], errors='coerce').fillna(0.0)
        except: return

        if os.path.exists(MODEL_PATH):
            try: self.model = Word2Vec.load(MODEL_PATH)
            except: pass
        
        if not self.df.empty and self.model:
            self.doc_vectors = np.array([self.get_vector(t) for t in self.df['teks_bersih']])
            self.is_ready = True

    def get_vector(self, text):
        if not self.model: return np.zeros(100)
        words = str(text).split()
        word_vecs = [self.model.wv[w] for w in words if w in self.model.wv]
        if not word_vecs: return np.zeros(self.model.vector_size)
        return np.mean(word_vecs, axis=0)

    def preprocess_query(self, query):
        q = query.lower().strip()
        if q in self.intent_dict: return q, self.intent_dict[q]
        for phrase, token in self.phrase_dict.items():
            if phrase in q: q = q.replace(phrase, token)
        return q, None

    def detect_region_filter(self, query):
        q_lower = query.lower()
        detected = []
        for region_code, terms in self.region_dict.items():
            for term in terms:
                if term in q_lower:
                    detected.extend(terms)
                    break
        return list(set(detected))

    def calculate_smart_score(self, query_tokens, text):
        # (Logika ini tetap sama seperti sebelumnya untuk analisis ulasan)
        text_lower = text.lower()
        words = re.findall(r'\w+', text_lower)
        matches = 0
        negation_penalty_count = 0
        
        important_tokens = [t for t in query_tokens if t not in STOPWORDS]
        if not important_tokens: important_tokens = query_tokens
        if len(important_tokens) == 0: return 0.0

        for token in important_tokens:
            token_found = False
            check_list = [token] + KEYWORD_SYNONYMS.get(token, [])
            if token in self.reverse_phrase: check_list.extend(self.reverse_phrase[token])

            for keyword in check_list:
                if keyword in text_lower:
                    token_found = True
                    try:
                        first_word = keyword.split()[0]
                        indices = [i for i, x in enumerate(words) if x.startswith(first_word)]
                        for idx in indices:
                            start = max(0, idx - 3)
                            prev_words = words[start:idx]
                            for pw in prev_words:
                                if pw in NEGATION_WORDS:
                                    negation_penalty_count += 1
                                    break
                    except: pass
                    break 
            if token_found: matches += 1
        
        base_score = matches / len(important_tokens)
        final_score = base_score * (0.3 ** negation_penalty_count)
        return final_score

    def apply_antonym_penalty(self, query_tokens, text, current_score):
        # (Logika ini tetap sama)
        text_lower = text.lower()
        penalty = 1.0
        check_tokens = [t for t in query_tokens if t not in STOPWORDS]
        for token in check_tokens:
            keys_to_check = [token]
            if token in self.reverse_phrase: keys_to_check.extend(self.reverse_phrase[token])
            for k in keys_to_check:
                match_key = k if k in ANTONYM_MAP else next((key for key in ANTONYM_MAP if key == token), None)
                if match_key:
                    for bad in ANTONYM_MAP[match_key]:
                        if bad in text_lower:
                            penalty *= 0.1
                            break
        return current_score * penalty

    def search(self, query, top_k=50):
        if not self.is_ready: return pd.DataFrame()

        clean_query, intent = self.preprocess_query(query)
        
        # Intent Handler
        if intent == "ALL":
            return self.df.drop_duplicates(subset=['nama']).assign(**{"Skor Relevansi": 100.0}).head(100)
        elif intent == "RATING_TOP":
            return self.df.sort_values('rating_gmaps', ascending=False).drop_duplicates(subset=['nama']).assign(**{"Skor Relevansi": 100.0}).head(20)
        elif intent == "RATING_BOTTOM":
            bad_places = self.df[self.df['rating_gmaps'] > 0.1].sort_values('rating_gmaps', ascending=True)
            return bad_places.drop_duplicates(subset=['nama']).assign(**{"Skor Relevansi": 100.0}).head(20)

        # 1. Hitung Skor Ulasan (Review) - Semantic + Keyword
        query_vec = self.get_vector(clean_query).reshape(1, -1)
        semantic_scores = cosine_similarity(query_vec, self.doc_vectors)[0]
        
        query_tokens = clean_query.split()
        keyword_scores = np.array([self.calculate_smart_score(query_tokens, t) for t in self.df['teks_mentah']])
        
        final_scores = (semantic_scores * WEIGHT_SEMANTIC) + (keyword_scores * WEIGHT_KEYWORD)
        
        # Zero Tolerance Review
        has_important_tokens = any(t not in STOPWORDS for t in query_tokens)
        if has_important_tokens:
            final_scores = final_scores * np.where(keyword_scores > 0, 1.0, 0.0)

        # 2. [BARU] Hitung Skor Kecocokan Nama Tempat & Lokasi (Name Match)
        # Jika user mencari nama tempat spesifik (misal: "karimun jawa"), skor harus tinggi
        # meskipun di ulasannya tidak ada kata tersebut.
        name_scores = np.zeros(len(self.df))
        query_lower = query.lower() # Gunakan query asli user, bukan yang sudah di-clean berlebihan
        
        # Cek apakah query ada di Nama Tempat atau Lokasi
        mask_name = self.df['nama_lower'].str.contains(query_lower, na=False, regex=False)
        mask_loc = self.df['lokasi_lower'].str.contains(query_lower, na=False, regex=False)
        
        # Berikan skor 99% (0.99) jika nama/lokasi cocok
        name_scores = np.where(mask_name | mask_loc, 0.99, 0.0)
        
        # GABUNGKAN SKOR: Ambil nilai maksimal antara Skor Ulasan vs Skor Nama
        # Jadi kalau ulasannya jelek tapi namanya cocok, tetap muncul.
        final_scores = np.maximum(final_scores, name_scores)

        # 3. Filter Wilayah
        target_regions = self.detect_region_filter(query)
        if target_regions:
            mask = self.df['lokasi_lower'].apply(lambda x: any(r in x for r in target_regions))
            final_scores = final_scores * np.where(mask, 1.0, 0.0)

        # 4. Result Construction
        results = []
        top_indices = final_scores.argsort()[::-1][:top_k*5]

        for idx in top_indices:
            raw_score = final_scores[idx]
            if raw_score <= 0.01: continue 
            
            text = self.df.iloc[idx]['teks_mentah']
            
            # Terapkan penalti antonim HANYA jika skornya berasal dari ulasan (bukan dari nama tempat)
            # Jika skor > 0.9 (berarti match nama), jangan dipenalti
            final_score_processed = raw_score
            if raw_score < 0.9: 
                final_score_processed = self.apply_antonym_penalty(query_tokens, text, raw_score)
            
            if final_score_processed > 0.15:
                row = self.df.iloc[idx]
                results.append({
                    "Nama Tempat": row['nama'],
                    "Lokasi": row['lokasi'],
                    "Isi Ulasan": row['teks_mentah'],
                    "Skor Relevansi": round(min(final_score_processed * 100, 99.9), 1)
                })

        df_results = pd.DataFrame(results)
        if not df_results.empty:
            df_results = df_results.sort_values('Skor Relevansi', ascending=False)
            df_results = df_results.drop_duplicates(subset=['Nama Tempat'], keep='first')
            
        return df_results.head(top_k)