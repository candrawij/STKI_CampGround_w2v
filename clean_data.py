import pandas as pd
import os
import re
from deep_translator import GoogleTranslator
from langdetect import detect

# ================= KONFIGURASI =================
ROOT_FOLDER = 'Data_Mentah'
OUTPUT_STAGING = os.path.join('Documents', 'corpus_staging.csv')

# Kata-kata khas Balasan Owner (Stopwords khusus Owner)
OWNER_PHRASES = [
    'terimakasih', 'terima kasih', 'thank you', 'thanks', 
    'ditunggu kedatangannya', 'salam sehat', 'matur nuwun', 
    'semoga sehat', 'berkunjung kembali', 'owner', 'pengelola'
]

def get_strict_rating(val):
    """Mencoba mengambil angka rating. Return Integer atau None."""
    if pd.isna(val): return None
    val_str = str(val).lower().strip()
    
    found_val = None
    
    # Format "5/5", "4/5", "5 bintang"
    match = re.search(r'(\d)(\s?/\s?5|\s?bintang|\s?stars)?', val_str)
    if match:
        found_val = float(match.group(1))

    # Format angka murni "5.0", "4", "5"
    elif re.match(r'^[1-5](\.\d)?$', val_str): 
        found_val = float(val_str)
        
    if found_val is not None and 1 <= found_val <= 5:
        return int(round(found_val))
            
    return None

def is_recent(time_str):
    """ Filter Waktu (Opsional: Ambil semua data untuk training) """
    # Saat training, kita biasanya ambil semua data.
    # Jika ingin membatasi, aktifkan logika ini.
    return True 

def is_owner_reply_or_spam(text):
    """ 
    Mendeteksi apakah teks ini adalah balasan owner atau spam emoji.
    """
    if not isinstance(text, str): return True
    text_lower = text.lower().strip()

    # 1. Terlalu Pendek (Hanya simbol/emoji/1 kata)
    # Contoh: "🙏 ...", "👍", "Ok", "Sip" -> Kurang bermakna buat AI
    if len(text_lower) < 4: 
        return True
    
    # 2. Hanya Tanda Baca/Simbol
    # Menghapus huruf & angka, jika sisanya kosong berarti cuma simbol
    if not re.search('[a-zA-Z]', text_lower):
        return True

    # 3. Deteksi Bahasa Owner
    # Jika teks mengandung "terima kasih berkunjung", kemungkinan besar itu owner
    # TAPI kita harus hati-hati, user juga bisa bilang "Terima kasih pelayanannya"
    # Jadi kita cek kombinasi panjangnya. Balasan owner biasanya sopan dan baku.
    
    hit_count = 0
    for phrase in OWNER_PHRASES:
        if phrase in text_lower:
            hit_count += 1
    
    # Jika mengandung kata owner DAN pendek (< 100 char), kemungkinan besar itu balasan
    # Contoh: "Terimakasih kak ulasannya" (Buang)
    # Contoh: "Terimakasih tempatnya bagus banget saya suka" (Simpan - ini user)
    if hit_count > 0 and len(text_lower) < 80:
        # Cek apakah ada kata ganti orang pertama (saya, aku, gue) -> User
        if not any(x in text_lower for x in ['saya', 'aku', 'gue', 'kami', 'kita']):
            return True

    return False

def translate_to_indo(text):
    """Mendeteksi bahasa, jika Inggris -> Translate ke Indo."""
    try:
        # Translate hanya jika teks cukup panjang (hemat waktu)
        if len(text) > 10 and len(text) < 500:
            lang = detect(text)
            if lang != 'id' and lang != 'ind':
                translated = GoogleTranslator(source='auto', target='id').translate(text)
                return translated
        return text
    except:
        return text

def clean_data_tolerant():
    print("🛡️ [CLEANING V2] FILTERING OWNER & SPAM...")
    
    all_data = []
    
    for root, dirs, files in os.walk(ROOT_FOLDER):
        for filename in files:
            if not filename.endswith(".csv"): continue
            
            file_path = os.path.join(root, filename)
            folder_name = os.path.basename(root)
            lokasi_fix = folder_name if folder_name != ROOT_FOLDER else "Jogja/Jateng"
            nama_tempat = filename.replace('.csv', '').replace('_', ' ').title()
            
            print(f"📂 [{lokasi_fix}] {filename}...", end=" ")
            
            try:
                df = pd.read_csv(file_path)
                
                # --- DETEKSI KOLOM ---
                col_text_candidates = ['wiI7pd', 'Teks_Mentah', 'review_text', 'teks'] 
                col_text = None
                for c in col_text_candidates:
                    if c in df.columns: col_text = c; break

                col_rating = None
                for c in df.columns:
                    if 'Rating' in c or 'rating' in c or '/5' in str(df[c].iloc[0]):
                        col_rating = c; break

                if not col_text:
                    print("⏩ LEWATI (No text column)")
                    continue
                
                # --- EKSTRAKSI ---
                count_ok = 0
                count_spam = 0
                
                for _, row in df.iterrows():
                    teks = row[col_text]
                    
                    # 1. Filter Spam / Owner
                    if is_owner_reply_or_spam(teks): 
                        count_spam += 1
                        continue
                    
                    # 2. Translate (Opsional, matikan jika lambat)
                    # teks = translate_to_indo(teks) 
                    
                    # 3. Ambil Rating
                    final_rating = 0
                    if col_rating:
                        val = get_strict_rating(row[col_rating])
                        if val is not None: final_rating = val
                    
                    # 4. Simpan
                    all_data.append({
                        'Nama_Tempat': nama_tempat,
                        'Lokasi': lokasi_fix,
                        'Rating': final_rating,
                        'Teks_Mentah': teks # Simpan teks asli/translated
                    })
                    count_ok += 1
                
                print(f"✅ OK: {count_ok} | 🗑️ Sampah/Owner: {count_spam}")
                
            except Exception as e:
                print(f"❌ ERROR: {e}")

    # --- SIMPAN ---
    if all_data:
        df_final = pd.DataFrame(all_data)
        df_final.drop_duplicates(subset=['Teks_Mentah'], inplace=True)
        df_final.reset_index(drop=True, inplace=True)
        df_final.insert(0, 'Doc_ID', range(1, len(df_final) + 1))
        
        os.makedirs('Documents', exist_ok=True)
        df_final.to_csv(OUTPUT_STAGING, index=False)
        
        print("\n" + "="*40)
        print(f"🎉 SELESAI! Data Bersih: {len(df_final)} baris.")
        print(f"📂 File: {OUTPUT_STAGING}")
    else:
        print("\n❌ Tidak ada data sama sekali.")

if __name__ == "__main__":
    clean_data_tolerant()