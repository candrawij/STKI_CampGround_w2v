# src/aspect_definitions.py

# Definisi kata kunci untuk setiap aspek (ASPECT MAPPING)
# Kita bisa memperkaya ini nanti menggunakan Word2Vec agar lebih pintar

ASPECTS = {
    "toilet": {
        "keywords": ["toilet", "wc", "kamar mandi", "air", "kran", "closet", "kakus", "mandi"],
        "icon": "🚽",
        "label": "Kebersihan Toilet"
    },
    "akses": {
        "keywords": ["jalan", "akses", "jalur", "aspal", "cor", "tanjakan", "mobil", "motor", "parkir", "roda 4", "sempit"],
        "icon": "🛣️",
        "label": "Akses & Parkir"
    },
    "view": {
        "keywords": ["pemandangan", "view", "gunung", "bukit", "matahari", "sunrise", "sunset", "kabut", "alam", "foto"],
        "icon": "im",
        "label": "Pemandangan Alam"
    },
    "kenyamanan": {
        "keywords": ["tenang", "berisik", "ramai", "sepi", "nyaman", "tidur", "tenda", "lapak", "tanah"],
        "icon": "⛺",
        "label": "Kenyamanan Camp"
    },
    "pelayanan": {
        "keywords": ["ramah", "penjaga", "petugas", "pengelola", "bapak", "ibu", "mas", "pelayanan", "staff"],
        "icon": "🤝",
        "label": "Pelayanan Staff"
    },
    "fasilitas": {
        "keywords": ["listrik", "colokan", "mushola", "warung", "makan", "sewa", "alat"],
        "icon": "⚡",
        "label": "Fasilitas Umum"
    }
}

# Kata kunci Sentimen (Sederhana dulu, nanti bisa pakai Model AI)
# Ini untuk mendeteksi apakah aspek di atas dibicarakan secara positif/negatif

SENTIMENT_KEYWORDS = {
    "positif": [
        "bersih", "bagus", "enak", "nyaman", "ramah", "luas", "mudah", "lancar", 
        "indah", "keren", "mantap", "puas", "rekomended", "ok", "oke", "suka",
        "sejuk", "dingin", "terjangkau", "murah", "aman", "lengkap", "memadai"
    ],
    "negatif": [
        "kotor", "bau", "rusak", "susah", "jelek", "mahal", "curam", "sempit", 
        "macet", "licin", "berlubang", "gelap", "seram", "kecewa", "kapok", 
        "berisik", "ramai", "bising", "jorok", "antri", "kurang", "tidak ada"
    ]
}

# Definisi Kategori Pengunjung (Untuk Badge "Cocok Untuk")
VISITOR_TYPES = {
    "keluarga": ["anak", "keluarga", "bocah", "balita", "orang tua", "family"],
    "pemula": ["baru", "pertama", "nyoba", "pemula", "mudah", "sewa tenda"],
    "petualang": ["trekking", "jalan kaki", "jauh", "masuk hutan", "ekstrem"]
}