from Asisten.db_handler import db

print("🛠️ Memulai update database...")
try:
    db.init_tables()
    print("✅ Tabel 'users' berhasil dibuat/dicek.")
    print("✅ Tabel 'bookings' berhasil dibuat/dicek.")
    print("🎉 Database siap untuk fitur Booking!")
except Exception as e:
    print(f"❌ Gagal update database: {e}")