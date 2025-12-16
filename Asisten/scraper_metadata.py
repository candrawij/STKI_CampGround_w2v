import csv
import time
import os
import re
from playwright.sync_api import sync_playwright

# ================= KONFIGURASI =================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_OUTPUT_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "Documents")

# LANGSUNG KE FILE MASTER (Bukan Draft lagi)
TARGET_CSV = os.path.join(BASE_OUTPUT_DIR, "input_info_statis.csv")

def scrape_metadata():
    print("--- 📸 GMAPS METADATA SCRAPER (AUTO APPEND) ---")
    print(f"📂 Target File: {TARGET_CSV}")
    print("ℹ️  Data akan langsung ditambahkan ke bagian bawah file CSV.")
    print("    Harga & Fasilitas tetap perlu dicek manual nanti.")
    print("-" * 40)
    
    urls = []
    print("Masukkan URL Gmaps (Tekan Enter kosong jika selesai):")
    while True:
        url = input(f"URL #{len(urls)+1}: ").strip()
        if not url: break
        urls.append(url)

    if not urls: return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Mode hening (cepat)
        page = browser.new_page()
        
        results = []
        
        for url in urls:
            try:
                print(f"⏳ Memproses: {url[:30]}...")
                page.goto(url, timeout=60000)
                time.sleep(2) # Tunggu loading

                # 1. AMBIL NAMA TEMPAT
                try:
                    nama_el = page.locator('h1.DUwDvf').first
                    nama = nama_el.inner_text()
                except:
                    nama = "Nama Tidak Ditemukan"

                # 2. AMBIL FOTO SAMPUL
                photo_url = ""
                try:
                    # Ambil tombol foto pertama
                    button_img = page.locator('button.aoRNLd img').first
                    src = button_img.get_attribute('src')
                    if src: photo_url = src
                except:
                    # Fallback jika tidak ada tombol foto
                    photo_url = ""

                # 3. AMBIL WAKTU BUKA (Default: "Cek Gmaps")
                waktu_buka = "Cek Gmaps"
                try:
                    # Mencoba mengambil status jam buka
                    # Selector ini mencari elemen status buka/tutup
                    status_el = page.locator('div[aria-label*="Open"], div[aria-label*="Closed"], div.t39EBf').first
                    if status_el.count() > 0:
                        aria_label = status_el.get_attribute('aria-label')
                        if aria_label:
                            # Bersihkan teks aneh
                            waktu_buka = aria_label.replace('\u202f', ' ').strip()
                except:
                    pass

                print(f"   ✅ Dapat: {nama}")
                print(f"      🕒 Jam: {waktu_buka}")
                
                results.append({
                    'Nama_Tempat': nama,
                    'Photo_URL': photo_url,
                    'Gmaps_Link': url,
                    'Waktu_Buka': waktu_buka
                })

            except Exception as e:
                print(f"   ❌ Gagal: {e}")

        browser.close()

        # APPEND KE FILE CSV UTAMA
        # Kita cek apakah file sudah ada isinya atau belum
        file_exists = os.path.exists(TARGET_CSV)
        
        with open(TARGET_CSV, 'a', newline='', encoding='utf-8') as f:
            # Pastikan nama kolom SAMA PERSIS dengan struktur input_info_statis.csv Anda
            fieldnames = ['Nama_Tempat', 'Photo_URL', 'Gmaps_Link', 'Waktu_Buka']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Jika file baru dibuat, tulis header dulu
            if not file_exists:
                writer.writeheader()
            
            # Tulis data
            writer.writerows(results)
            
        print(f"\n🎉 SUKSES! {len(results)} tempat baru ditambahkan ke {TARGET_CSV}")
        print("👉 Jangan lupa jalankan 'Asisten/konversi_data.py' nanti untuk mengupdate Metadata AI.")

if __name__ == "__main__":
    scrape_metadata()