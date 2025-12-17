from gensim.models import Word2Vec
import sys
import os

# Tambahkan folder root ke path agar bisa import 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import mesin_pencari

# Path ke model
MODEL_PATH = os.path.join('Assets', 'word2vec.model')

def cek_kepintaran():
    if not os.path.exists(MODEL_PATH):
        print("❌ Model belum ada. Jalankan train_w2v.py dulu.")
        return

    print("🧠 Memuat Otak AI...")
    model = Word2Vec.load(MODEL_PATH)
    
    print(f"📊 Total Kosa Kata yang dipelajari: {len(model.wv.index_to_key)} kata.")
    
    # Daftar kata yang ingin dites
    kata_tes = [
        'sejuk', 'bersih', 'mahal', 'bagus', 'toilet', 'malam', 
        'akses', 'jalan', 'pandang', 'ramah', 'tenda', 'listrik','pantai'
    ]
    
    print("\n--- 🧪 TES ASOSIASI KATA ---")
    for kata in kata_tes:
        if kata in model.wv:
            print(f"\nKata: '{kata.upper()}' mirip dengan:")
            # Tampilkan 5 kata teratas
            try:
                mirip = model.wv.most_similar(kata, topn=5)
                for k, skor in mirip:
                    print(f"   - {k} (Kemiripan: {skor:.2f})")
            except:
                print("   (Gagal mencari kemiripan)")
        else:
            print(f"\n❌ Kata '{kata}' TIDAK DIKENALI (Belum ada di data latih).")

if __name__ == "__main__":
    cek_kepintaran()