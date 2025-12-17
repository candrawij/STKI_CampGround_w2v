import pandas as pd
import os
import re

# ================= KONFIGURASI =================
ROOT_FOLDER = 'Data_Mentah'
OUTPUT_STAGING = os.path.join('Documents', 'corpus_staging.csv')

# 1. Daftar Kata Kunci "Alam Abadi"
# Jika ulasan (baru/lama) mengandung kata ini, ulasan DIJAMIN MASUK.
NATURE_KEYWORDS = [
    'dingin', 'sejuk', 'kabut', 'asri', 'alami', 'pemandangan', 'view',
    'gunung', 'bukit', 'sungai', 'hutan', 'pinus', 'tenda', 'camping',
    'kemah', 'bintang', 'sunrise', 'sunset', 'jalan', 'akses', 'tanjakan',
    'adem', 'tenang', 'damai', 'kabut'
]

# 2. Daftar Kata Khas Owner (Harus Dibuang)
OWNER_PHRASES = [
    'terimakasih', 'terima kasih', 'thank you', 'thanks', 
    'ditunggu kedatangannya', 'salam sehat', 'matur nuwun', 
    'semoga sehat', 'berkunjung kembali', 'owner', 'pengelola',
    'management', 'manajemen', 'kakak', 'kak'
]

def get_strict_rating(val):
    """Membersihkan format rating menjadi angka 1-5"""
    if pd.isna(val): return None
    val_str = str(val).lower().strip()
    match = re.search(r'(\d)(\s?/\s?5|\s?bintang|\s?stars)?', val_str)
    if match: return float(match.group(1))
    elif re.match(r'^[1-5](\.\d)?$', val_str): return float(val_str)
    return None

def is_quality_review(text):
    """ 
    Logika Filter Cerdas:
    1. Buang Balasan Owner.
    2. Selamatkan ulasan (meski pendek/lama) jika mengandung kata alam.
    3. Buang ulasan sampah/terlalu pendek tanpa konteks.
    """
    if not isinstance(text, str): return False
    text_lower = text.lower().strip()
    
    # --- ATURAN 1: Pastikan Bukan Balasan Owner ---
    # Jika mengandung kata owner, kita cek lebih ketat
    is_owner_suspect = False
    for phrase in OWNER_PHRASES:
        if phrase in text_lower:
            is_owner_suspect = True
            break
            
    if is_owner_suspect:
        # Jika teks mengandung kata owner DAN tidak ada kata "saya/aku", kemungkinan besar owner
        if not any(x in text_lower for x in ['saya', 'aku', 'gue', 'kami', 'kita', 'buat']):
            return False # REJECT (Ini Owner)

    # --- ATURAN 2: "Nature Protection" (Penyelamat Data Lama) ---
    # Cek apakah ulasan mengandung kata kunci alam?
    has_nature_context = any(word in text_lower for word in NATURE_KEYWORDS)
    
    if has_nature_context:
        return True # ACCEPT (Simpan! Ini data berharga untuk Word2Vec)

    # --- ATURAN 3: Filter Sampah Standar ---
    # Jika TIDAK ada konteks alam, kita seleksi ketat berdasarkan panjang
    
    # Hapus jika cuma simbol
    if not re.search('[a-zA-Z]', text_lower): return False
    
    # Hapus jika terlalu pendek (kurang dari 15 huruf) DAN tidak ada konteks alam
    # Contoh yang dibuang: "Mantap", "Ok gan", "Good place", "Jos gandos"
    # Kenapa dibuang? Karena AI tidak belajar apa-apa dari kata "Ok" untuk rekomendasi camping.
    if len(text_lower) < 15:
        return False 

    return True # ACCEPT (Ulasan panjang umum)

def clean_data_hybrid():
    print("🛡️ [CLEANING FINAL] Menggabungkan Data Baru + Data Lama Relevan...")
    
    all_data = []
    total_files = 0
    
    for root, dirs, files in os.walk(ROOT_FOLDER):
        for filename in files:
            if not filename.endswith(".csv"): continue
            
            total_files += 1
            file_path = os.path.join(root, filename)
            folder_name = os.path.basename(root)
            lokasi_fix = folder_name if folder_name != ROOT_FOLDER else "Jogja/Jateng"
            nama_tempat = filename.replace('.csv', '').replace('_', ' ').title()
            
            try:
                df = pd.read_csv(file_path)
                
                # Cari kolom teks
                col_text = next((c for c in ['wiI7pd', 'Teks_Mentah', 'review_text', 'teks'] if c in df.columns), None)
                col_rating = next((c for c in df.columns if 'rating' in c.lower() or 'Rating' in c), None)

                if not col_text: continue
                
                # Drop baris kosong
                df = df.dropna(subset=[col_text])

                count_kept = 0
                for _, row in df.iterrows():
                    teks = str(row[col_text])
                    
                    # === INI FILTERNYA ===
                    if is_quality_review(teks):
                        
                        # Ambil Rating
                        rating = 0
                        if col_rating:
                            r_val = get_strict_rating(row[col_rating])
                            if r_val: rating = r_val
                        
                        all_data.append({
                            'Nama_Tempat': nama_tempat,
                            'Lokasi': lokasi_fix,
                            'Rating': rating,
                            'Teks_Mentah': teks
                        })
                        count_kept += 1
                
                # Feedback per file (biar tau progress)
                # print(f"   -> {nama_tempat}: {count_kept} ulasan disimpan.")
                
            except Exception: pass

    # --- SIMPAN HASIL AKHIR ---
    if all_data:
        df_final = pd.DataFrame(all_data)
        
        # Hapus duplikat persis (Jika scraper mengambil data yang sama 2x)
        df_final.drop_duplicates(subset=['Teks_Mentah'], inplace=True)
        
        # Beri ID Dokumen
        df_final.reset_index(drop=True, inplace=True)
        df_final.insert(0, 'Doc_ID', range(1, len(df_final) + 1))
        
        os.makedirs('Documents', exist_ok=True)
        df_final.to_csv(OUTPUT_STAGING, index=False)
        
        print("\n" + "="*50)
        print(f"✅ CLEANING SELESAI!")
        print(f"📊 Total Ulasan Berkualitas: {len(df_final)}")
        print(f"📂 Disimpan di: {OUTPUT_STAGING}")
        print("="*50)
    else:
        print("❌ Tidak ada data yang lolos filter.")

if __name__ == "__main__":
    clean_data_hybrid()