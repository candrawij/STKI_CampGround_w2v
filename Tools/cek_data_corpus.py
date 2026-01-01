import pandas as pd
import os
import sys

# Tambahkan folder root ke path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Konfigurasi Path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_PATH = os.path.join(ROOT_DIR, "Documents", "corpus_master.csv")

def cek_jumlah_per_tempat():
    print("📊 --- AUDIT DATA CORPUS MASTER ---")
    
    if not os.path.exists(CORPUS_PATH):
        print(f"❌ File tidak ditemukan: {CORPUS_PATH}")
        print("   Jalankan pipeline 'Update Otak AI' dulu.")
        return

    try:
        # Baca CSV
        df = pd.read_csv(CORPUS_PATH)
        
        # Cek kolom nama tempat
        if 'Nama_Tempat' not in df.columns:
            print("❌ Kolom 'Nama_Tempat' tidak ada di CSV.")
            return

        # Hitung jumlah per tempat
        counts = df['Nama_Tempat'].value_counts().reset_index()
        counts.columns = ['Nama_Tempat', 'Jumlah_Data']
        
        print(f"📂 Total Seluruh Data: {len(df)} baris")
        print("-" * 60)
        print(f"{'NAMA TEMPAT':<30} | {'JUMLAH':<8} | {'STATUS WORD2VEC'}")
        print("-" * 60)
        
        total_kurang = 0
        
        for _, row in counts.iterrows():
            nama = row['Nama_Tempat']
            jumlah = row['Jumlah_Data']
            
            # Logika Status
            if jumlah < 50:
                status = "❌ KURANG (Risiko Bias)"
                total_kurang += 1
            elif 50 <= jumlah < 100:
                status = "⚠️ CUKUP (Bisa Dilatih)"
            else:
                status = "✅ BAGUS (Optimal)"
                
            print(f"{nama:<30} | {jumlah:<8} | {status}")
            
        print("-" * 60)
        
        if total_kurang > 0:
            print(f"\n💡 TIPS: Ada {total_kurang} tempat yang datanya < 50.")
            print("   Sebaiknya scrap ulang tempat tersebut agar hasil AI lebih akurat.")
        else:
            print("\n🎉 Mantap! Semua tempat memiliki data yang cukup untuk pelatihan AI.")

    except Exception as e:
        print(f"❌ Terjadi error: {e}")

if __name__ == "__main__":
    cek_jumlah_per_tempat()