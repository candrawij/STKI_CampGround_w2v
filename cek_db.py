import sqlite3
import pandas as pd

# Buka Koneksi
conn = sqlite3.connect('camping.db')
cursor = conn.cursor()

print("--- STRUKTUR TABEL FASILITAS ---")
try:
    # Cek nama kolom di tabel fasilitas
    info = cursor.execute("PRAGMA table_info(fasilitas)").fetchall()
    if info:
        columns = [col[1] for col in info]
        print(f"Nama Kolom yang ada: {columns}")
    else:
        print("Tabel 'fasilitas' KOSONG atau TIDAK DITEMUKAN!")
except Exception as e:
    print(f"Error: {e}")

print("\n--- CONTOH ISI DATA ---")
try:
    df = pd.read_sql_query("SELECT * FROM fasilitas LIMIT 3", conn)
    print(df)
except:
    print("Gagal baca data.")

conn.close()