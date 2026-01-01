import pandas as pd
import json
import os

print("--- 🚀 Memulai Skrip Asisten Konversi Data ---")

# --- 1. Setup Path ---
# Path ini sudah benar (menggunakan trik 'satu level ke atas')
try:
    ASISTEN_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(ASISTEN_DIR)
    DOCS_FOLDER = os.path.join(BASE_DIR, 'Documents')
except NameError:
    # Fallback jika dijalankan di lingkungan non-file (misal: notebook)
    BASE_DIR = os.path.abspath('.')
    DOCS_FOLDER = os.path.join(BASE_DIR, 'Documents')

# --- 2. Definisikan Nama File ---
# Tiga file input "MUDAH"
STATIS_INPUT_FILE = os.path.join(DOCS_FOLDER, 'input_info_statis.csv')
HARGA_INPUT_FILE = os.path.join(DOCS_FOLDER, 'input_harga.csv')
FASILITAS_INPUT_FILE = os.path.join(DOCS_FOLDER, 'input_fasilitas.csv')

# Satu file output "MESIN" (yang akan dibaca build_index.py)
FINAL_OUTPUT_FILE = os.path.join(DOCS_FOLDER, 'info_tempat.csv')

try:
    # --- 3. Baca Tiga File Input ---
    print(f"Membaca info statis dari: {STATIS_INPUT_FILE}")
    df_statis = pd.read_csv(STATIS_INPUT_FILE)
    df_statis['Nama_Tempat'] = df_statis['Nama_Tempat'].str.strip()
    
    print(f"Membaca info harga dari: {HARGA_INPUT_FILE}")
    df_harga = pd.read_csv(HARGA_INPUT_FILE)
    df_harga['Nama_Tempat'] = df_harga['Nama_Tempat'].str.strip()

    print(f"Membaca info fasilitas dari: {FASILITAS_INPUT_FILE}")
    df_fasilitas = pd.read_csv(FASILITAS_INPUT_FILE)
    df_fasilitas['Nama_Tempat'] = df_fasilitas['Nama_Tempat'].str.strip()

    # --- 4. Proses Data (Agregasi) ---

    # A. Proses Harga (menjadi JSON)
    print("Memproses data harga (mengubah ke JSON)...")
    df_harga['harga'] = df_harga['harga'].fillna(0)
    df_harga_json = df_harga.groupby('Nama_Tempat').apply(
        lambda x: x[['item', 'harga', 'kategori']].to_json(orient='records')
    ).reset_index()
    df_harga_json.columns = ['Nama_Tempat', 'Price_Items']

    # B. Proses Fasilitas (menjadi String terpisah "|")
    print("Memproses data fasilitas (mengubah ke String)...")
    df_fasilitas_str = df_fasilitas.groupby('Nama_Tempat')['Fasilitas'].apply(
        lambda x: ' | '.join(x.dropna().astype(str).str.strip())
    ).reset_index()
    df_fasilitas_str.columns = ['Nama_Tempat', 'Facilities'] 

    # --- 5. Gabungkan Semua Data ---
    print("Menggabungkan semua data menjadi satu...")
    
    # Mulai dengan data statis sebagai dasar
    df_final = df_statis
    
    # Gabungkan dengan data harga yang sudah jadi JSON
    df_final = df_final.merge(df_harga_json, on='Nama_Tempat', how='left')
    
    # Gabungkan dengan data fasilitas yang sudah jadi String
    df_final = df_final.merge(df_fasilitas_str, on='Nama_Tempat', how='left')

    # --- 6. Pembersihan Akhir ---
    # Isi data yang mungkin kosong setelah penggabungan
    df_final['Price_Items'] = df_final['Price_Items'].fillna("[]")
    df_final['Facilities'] = df_final['Facilities'].fillna("")
    df_final['Waktu_Buka'] = df_final['Waktu_Buka'].fillna("Info tidak tersedia")
    df_final['Photo_URL'] = df_final['Photo_URL'].fillna("")
    df_final['Gmaps_Link'] = df_final['Gmaps_Link'].fillna("")

    # --- 7. Simpan File Output ---
    print(f"Menyimpan file akhir yang siap dibaca mesin ke: {FINAL_OUTPUT_FILE}")
    df_final.to_csv(FINAL_OUTPUT_FILE, index=False)
    
    print("\n✅ SUKSES!")
    print(f"File '{FINAL_OUTPUT_FILE}' telah berhasil dibuat ulang.")
    print("---------------------------------------------------------")
    print("Alur Kerja Selesai. Sekarang jalankan 'python train_w2v.py'")
    print("---------------------------------------------------------")

except FileNotFoundError as e:
    print(f"❌ ERROR: File input tidak ditemukan: {e.filename}")
    print("Pastikan ketiga file 'input_harga.csv', 'input_fasilitas.csv', dan 'input_info_statis.csv' ada di folder 'Documents'.")
except Exception as e:
    print(f"❌ ERROR: Terjadi kesalahan: {e}")