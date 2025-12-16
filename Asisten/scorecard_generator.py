import pandas as pd
import json
import os
import sys

# Agar bisa mengimport dari folder src (naik satu level dari Asisten)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.aspect_definitions import ASPECTS, SENTIMENT_KEYWORDS, VISITOR_TYPES

# ================= KONFIGURASI =================
INPUT_FILE = os.path.join('Documents', 'corpus_master.csv')
OUTPUT_FILE = os.path.join('Documents', 'scorecards.json')

def calculate_score(pos, neg):
    """
    Menghitung skor 1-5 berdasarkan rasio sentimen positif vs negatif.
    Rumus: 1 + (4 * (Positif / Total))
    """
    total = pos + neg
    if total == 0:
        return 0 # Belum ada data sentimen
    
    ratio = pos / total
    score = 1.0 + (4.0 * ratio)
    return round(score, 1)

def generate_scorecards():
    print("📊 [SCORECARD] Memulai Analisis Aspek & Sentimen...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File tidak ditemukan: {INPUT_FILE}")
        return

    # Load Data
    df = pd.read_csv(INPUT_FILE)
    # Pastikan semua teks string dan lowercase
    df['Teks_Mentah'] = df['Teks_Mentah'].astype(str).str.lower()
    
    scorecards = {}

    # Grouping berdasarkan Nama Tempat
    grouped = df.groupby('Nama_Tempat')

    count_processed = 0

    for tempat, group in grouped:
        # Struktur Data per Tempat
        stats = {
            'aspects': {},
            'badges': [],
            'insight': "",
            'total_reviews': len(group)
        }

        # 1. Inisialisasi Counter Aspek
        # Agar aspek yang tidak ada review tetap muncul (nanti skor 0/N/A)
        for key, info in ASPECTS.items():
            stats['aspects'][key] = {
                'label': info['label'],
                'icon': info['icon'],
                'pos': 0,
                'neg': 0,
                'mentions': 0,
                'score': 0
            }
        
        # Counter untuk Badges
        badge_counts = {k: 0 for k in VISITOR_TYPES.keys()}

        # 2. Iterasi Setiap Review di Tempat Tersebut
        for text in group['Teks_Mentah']:
            
            # --- ANALISIS ASPEK & SENTIMEN ---
            for aspect_key, aspect_data in ASPECTS.items():
                # Cek apakah review mengandung kata kunci aspek ini (misal: "toilet")
                if any(k in text for k in aspect_data['keywords']):
                    stats['aspects'][aspect_key]['mentions'] += 1
                    
                    # Cek Sentimen di kalimat yang sama
                    is_pos = any(p in text for p in SENTIMENT_KEYWORDS['positif'])
                    is_neg = any(n in text for n in SENTIMENT_KEYWORDS['negatif'])
                    
                    # Logika Sederhana: 
                    # Jika ada kata positif, tambah poin. Jika ada negatif, kurangi.
                    # (Bisa diimprove pakai AI nanti)
                    if is_pos and not is_neg:
                        stats['aspects'][aspect_key]['pos'] += 1
                    elif is_neg and not is_pos:
                        stats['aspects'][aspect_key]['neg'] += 1
                    elif is_pos and is_neg:
                        # Netral / Bingung (ada bagus ada jelek), kita anggap 0.5 masing2 atau abaikan
                        pass 

            # --- ANALISIS BADGES (COCOK UNTUK) ---
            for badge_key, keywords in VISITOR_TYPES.items():
                if any(k in text for k in keywords):
                    badge_counts[badge_key] += 1

        # 3. FINALISASI SKOR PER TEMPAT
        highest_score = -1
        lowest_score = 6
        best_aspect = ""
        worst_aspect = ""

        for key, data in stats['aspects'].items():
            # Hitung Skor Akhir (1-5)
            final_score = calculate_score(data['pos'], data['neg'])
            stats['aspects'][key]['score'] = final_score
            
            # Cari aspek terbaik & terburuk untuk Insight (Min 2 mention biar valid)
            if data['mentions'] > 2:
                if final_score > highest_score:
                    highest_score = final_score
                    best_aspect = data['label'].lower()
                if final_score < lowest_score and final_score > 0: # > 0 artinya ada nilai
                    lowest_score = final_score
                    worst_aspect = data['label'].lower()

        # 4. TENTUKAN BADGES
        # Jika > 10% review menyebut kata kunci badge, maka tempat ini berhak dapat badge
        threshold = max(2, len(group) * 0.1) 
        for badge, count in badge_counts.items():
            if count >= threshold:
                stats['badges'].append(badge)

        # 5. GENERATE INSIGHT OTOMATIS (KALIMAT EMAS)
        insight_text = "Belum cukup data untuk menyimpulkan."
        if best_aspect and worst_aspect and best_aspect != worst_aspect:
            insight_text = f"Pengunjung sangat menyukai {best_aspect}, namun perlu memperhatikan {worst_aspect}."
        elif best_aspect:
            insight_text = f"Kekuatan utama tempat ini adalah {best_aspect} yang sangat memuaskan."
        elif worst_aspect:
            insight_text = f"Banyak keluhan mengenai {worst_aspect}, harap persiapkan diri."
        
        stats['insight'] = insight_text
        
        # Simpan ke dictionary utama
        scorecards[tempat] = stats
        count_processed += 1

    # SIMPAN KE JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(scorecards, f, indent=4, ensure_ascii=False)

    print(f"✅ SELESAI! Scorecard untuk {count_processed} tempat telah dibuat.")
    print(f"📂 Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_scorecards()