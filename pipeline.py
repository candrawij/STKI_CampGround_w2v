import os
import sys
import subprocess
import time

# ================= KONFIGURASI =================
# Mendapatkan path interpreter python yang sedang aktif (.venv)
PYTHON_EXE = sys.executable 

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("="*50)
    print("   ⛺ CAMPGROUND AI - MISSION CONTROL ⛺")
    print("="*50)

def run_script(script_path, description):
    """Menjalankan script python lain dan menunggu sampai selesai"""
    print(f"\n[⏳] Sedang menjalankan: {description}...")
    print(f"    File: {script_path}")
    print("-" * 40)
    
    try:
        # Menjalankan script sebagai subprocess
        result = subprocess.run([PYTHON_EXE, script_path], check=True)
        if result.returncode == 0:
            print(f"✅ {description} SELESAI.")
            return True
        else:
            print(f"❌ {description} GAGAL.")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error saat menjalankan script: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ Dibatalkan oleh user.")
        return False

def menu_hunting():
    while True:
        print_header()
        print("🕵️‍♂️ MODE PEMBURU DATA (SCRAPING)")
        print("-" * 30)
        print("1. Scrape ULASAN (Review Gmaps)")
        print("2. Scrape INFO PROFIL (Metadata)")
        print("0. Kembali ke Menu Utama")
        
        pilihan = input("\nPilih menu (0-2): ").strip()
        
        if pilihan == '1':
            # Jalankan scraper_gmaps
            run_script(os.path.join('Asisten', 'scraper_gmaps.py'), "Scraping Ulasan")
            input("\nTekan Enter untuk lanjut...")
        elif pilihan == '2':
            # Jalankan scraper_metadata
            run_script(os.path.join('Asisten', 'scraper_metadata.py'), "Scraping Metadata")
            input("\nTekan Enter untuk lanjut...")
        elif pilihan == '0':
            break

def menu_update_ai():
    print_header()
    print("🧠 MODE UPDATE OTAK AI (PIPELINE OTOMATIS)")
    print("⚠️  Pastikan Anda sudah selesai scraping data baru.")
    print("-" * 30)
    confirm = input("Mulai proses update? (y/n): ").lower()
    
    if confirm != 'y': return

    start_time = time.time()
    
    # 1. CLEANING DATA
    if not run_script('clean_data.py', "1. Membersihkan Data Mentah"): return

    # 2. MERGING CORPUS
    if not run_script(os.path.join('Asisten', 'merge_corpus.py'), "2. Menggabungkan ke Master"): return

    # 3. KONVERSI METADATA (Info Harga/Foto)
    if not run_script(os.path.join('Asisten', 'konversi_data.py'), "3. Update Metadata Harga/Foto"): return

    # 4. GENERATE SCORECARD (Analisis Aspek)
    if not run_script(os.path.join('Asisten', 'scorecard_generator.py'), "4. Generate Scorecard & Insight"): return

    # 5. TRAINING AI (Word2Vec)
    if not run_script('train_w2v.py', "5. Melatih Model AI (Word2Vec)"): return

    total_time = time.time() - start_time
    print("\n" + "="*50)
    print(f"🎉 SEMUA PROSES SELESAI dalam {total_time:.2f} detik!")
    print("   AI sekarang sudah lebih pintar.")
    print("="*50)
    input("\nTekan Enter untuk kembali...")

def main_menu():
    while True:
        print_header()
        print("MENU UTAMA:")
        print("1. 🕵️‍♂️ Tambah Data Baru (Hunting)")
        print("2. 🧠 Update Otak AI (Pipeline Otomatis)")
        print("3. 🧪 Tes Kepintaran AI (Cek Asosiasi)")
        print("4. 🌐 Jalankan Website (Streamlit)")
        print("0. Keluar")
        
        pilihan = input("\nPilih menu (0-4): ").strip()
        
        if pilihan == '1':
            menu_hunting()
        elif pilihan == '2':
            menu_update_ai()
        elif pilihan == '3':
            run_script('cek_otak_ai.py', "Tes AI")
            input("\nTekan Enter untuk kembali...")
        elif pilihan == '4':
            print("\n[🌐] Menjalankan Server Web...")
            print("     (Tekan Ctrl+C di terminal ini untuk berhenti/kembali)")
            
            try:
                # Kita jalankan Streamlit
                subprocess.run([PYTHON_EXE, "-m", "streamlit", "run", "streamlit_app.py"])
            except KeyboardInterrupt:
                # Jika user tekan Ctrl+C, kode ini yang jalan (bukan error merah)
                print("\n\n✅ Web Server dimatikan. Kembali ke menu...")
                time.sleep(1) # Jeda sebentar biar user baca
        elif pilihan == '0':
            print("👋 Sampai jumpa!")
            break
        else:
            print("❌ Pilihan tidak valid.")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()