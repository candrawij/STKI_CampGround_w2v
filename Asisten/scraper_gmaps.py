import csv
import time
import os
import re
from playwright.sync_api import sync_playwright

# ================= KONFIGURASI =================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_OUTPUT_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "Data_Mentah")
USER_DATA_DIR = os.path.join(CURRENT_DIR, "chrome_session")
DEFAULT_MAX = 2000 

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def validate_url(url):
    """Memperbaiki URL jika user salah ketik"""
    url = url.strip()
    if " " in url and "." not in url:
        return None, "Sepertinya Anda memasukkan NAMA tempat, bukan URL."
    
    if url.startswith("httpsmaps"): url = url.replace("httpsmaps", "https://maps")
    if url.startswith("httpmaps"): url = url.replace("httpmaps", "http://maps")
    
    if not url.startswith("http"):
        url = "https://" + url
        
    return url, None

def extract_rating_flexible(card):
    try:
        star_el = card.locator('span[aria-label*="stars"], span[aria-label*="bintang"]').first
        if star_el.count() > 0:
            return star_el.get_attribute('aria-label').split(' ')[0].strip()

        text_rating_el = card.locator('span:has-text("/5")').first
        if text_rating_el.count() > 0:
            text = text_rating_el.inner_text().strip()
            if '/' in text: return text.split('/')[0].strip()
        
        hotel_rating_el = card.locator('div.GDWaad').first
        if hotel_rating_el.count() > 0:
            return hotel_rating_el.inner_text().strip().split('/')[0]
    except: pass
    return "0"

def extract_time_flexible(card):
    possible_selectors = ['.rsqaWe', '.xRkPPb', '.du8b2b', 'span.bp9Aid', 'span.dehysf']
    for sel in possible_selectors:
        try:
            el = card.locator(sel).first
            if el.count() > 0:
                text = el.inner_text().strip()
                if any(k in text.lower() for k in ['lalu', 'ago', 'week', 'month', 'year', 'day', 'jam', 'menit']):
                    return text
        except: continue
    return ""

def scrape_reviews():
    print("--- 🕵️‍♂️ GMAPS SCRAPER (All-in-One) ---")
    
    # --- INPUT 1: NAMA TEMPAT ---
    nama_file = input("1. Nama Tempat: ").strip()
    if not nama_file: return
    
    # --- INPUT 2: FOLDER LOKASI ---
    folder_lokasi = input("2. Nama Folder Lokasi (misal: Sleman): ").strip() or "General"

    # --- INPUT 3: URL (Dengan Validasi) ---
    while True:
        raw_url = input("3. Masukkan URL Google Maps: ").strip()
        target_url, error = validate_url(raw_url)
        
        if error:
            print(f"❌ {error}")
            print("👉 Masukkan LINK Gmaps yang valid.")
        elif not target_url:
            return 
        else:
            break 

    # Persiapan Folder
    nama_file_clean = sanitize_filename(nama_file)
    full_dir = os.path.join(BASE_OUTPUT_DIR, folder_lokasi)
    os.makedirs(full_dir, exist_ok=True)
    output_csv = os.path.join(full_dir, f"{nama_file_clean}.csv")
    
    print("-" * 40)
    print(f"🚀 Target: {nama_file_clean}")
    print(f"📂 Folder: {folder_lokasi}")
    print(f"🔗 Link: {target_url}")
    print("-" * 40)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR, 
            headless=False, 
            viewport={"width": 1366, "height": 768}
        )
        page = browser.pages[0]
        
        try:
            print("⏳ Membuka halaman...")
            page.goto(target_url, timeout=60000)
            time.sleep(4)

            print("👆 Mengklik tab Ulasan...")
            try:
                page.locator('button[aria-label*="Reviews"], button[aria-label*="Ulasan"], div[role="tab"]:has-text("Reviews")').first.click()
                time.sleep(3)
            except:
                print("ℹ️  Sudah di tab ulasan.")

            print("📜 Mulai scrolling...")
            try: page.locator('div.jftiEf, div.m6QErb').first.click()
            except: page.mouse.click(500, 500)

            last_count = 0
            stuck_count = 0
            
            while True:
                page.keyboard.press("End")
                time.sleep(1.5)
                
                more_buttons = page.locator('button.w8nwRe.kyuRq')
                if more_buttons.count() > 0:
                    for i in range(more_buttons.count()):
                        try:
                            if more_buttons.nth(i).is_visible(): more_buttons.nth(i).click()
                        except: pass
                
                review_cards = page.locator('div.jftiEf')
                current_count = review_cards.count()
                print(f"   Terambil: {current_count} ulasan...", end="\r")

                if current_count >= DEFAULT_MAX:
                    print("\n✅ Target tercapai!")
                    break

                if current_count == last_count:
                    stuck_count += 1
                    page.mouse.wheel(0, 1000)
                    time.sleep(1)
                    if stuck_count > 10: 
                        print(f"\n⚠️ Mentok di {current_count} ulasan.")
                        break
                else:
                    stuck_count = 0
                last_count = current_count

            print("\n⛏️ Menyalin data ke CSV...")
            reviews = []
            all_cards = page.locator('div.jftiEf').all()
            
            for card in all_cards:
                try:
                    rating = extract_rating_flexible(card)
                    
                    text_el = card.locator('.wiI7pd').first
                    text = text_el.inner_text() if text_el.count() > 0 else ""
                    
                    time_str = extract_time_flexible(card)

                    if text:
                        text_clean = text.replace('\n', ' ').replace('\r', ' ')
                        reviews.append([rating, time_str, text_clean])
                except: continue

            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Rating', 'Waktu', 'Teks_Mentah']) 
                writer.writerows(reviews)
                
            print(f"\n✅ SELESAI! {len(reviews)} ulasan berhasil disimpan.")
            print(f"📂 Lokasi: {output_csv}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_reviews()