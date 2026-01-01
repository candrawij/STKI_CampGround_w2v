# src/aspect_definitions.py

# Definisi kata kunci untuk setiap aspek (ASPECT MAPPING)
# Kita bisa memperkaya ini nanti menggunakan Word2Vec agar lebih pintar

ASPECTS = {
    "toilet": {
        "keywords": [
            "toilet", "wc", "kamar mandi", "air", "kran", "closet", 
            "kakus", "mandi", "kencing", "buang air", "km", "jamban",
            "pesing", "gayung", "ember", "kebersihan air"
        ],
        "icon": "🚽",
        "label": "Fasilitas Toilet"
    },
    "akses": {
        "keywords": [
            "jalan", "akses", "jalur", "aspal", "cor", "tanjakan", 
            "mobil", "motor", "parkir", "roda 4", "sempit", "makadam",
            "batu", "licin", "curam", "city car", "matic", "truk",
            "jalan masuk", "lokasi", "rute"
        ],
        "icon": "🛣️",
        "label": "Akses & Parkir"
    },
    "view": {
        "keywords": [
            "pandang", "pemandangan", "view", "gunung", "bukit", "matahari", 
            "sunrise", "sunset", "kabut", "alam", "foto", "spot",
            "city light", "lampu kota", "bintang", "langit", "merapi",
            "sawah", "sungai", "lembah", "indah", "cantik"
        ],
        "icon": "🍃",
        "label": "Pemandangan Alam"
    },
    "kenyamanan": {
        "keywords": [
            "tenang", "berisik", "ramai", "sepi", "nyaman", "tidur", 
            "tenda", "lapak", "tanah", "datar", "miring", "lahan",
            "ground", "campground", "camping ground", "angin", "badai",
            "rindang", "panas", "adem", "suasana"
        ],
        "icon": "⛺",
        "label": "Area Camping"
    },
    "pelayanan": {
        "keywords": [
            "ramah", "penjaga", "petugas", "pengelola", "bapak", 
            "ibu", "mas", "pelayanan", "staff", "owner", "akang",
            "tanggung jawab", "sigap", "bantu", "jaga", "respon"
        ],
        "icon": "🤝",
        "label": "Pelayanan Staff"
    },
    "fasilitas": {
        "keywords": [
            "listrik", "colokan", "mushola", "warung", "makan", 
            "sewa", "alat", "wifi", "sinyal", "internet", "jajan",
            "kopi", "mie", "kayu bakar", "terminal", "kabel",
            "sink", "cuci piring", "sampah"
        ],
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
        "sejuk", "dingin", "terjangkau", "murah", "aman", "lengkap", "memadai",
        "jos", "juara", "top", "terbaik", "rapi", "wangi", "kencang", "stabil",
        "tersedia", "gratis", "bantu", "sigap", "halus", "mulus"
    ],
    "negatif": [
        "kotor", "bau", "rusak", "susah", "jelek", "mahal", "curam", "sempit", 
        "macet", "licin", "berlubang", "gelap", "seram", "kecewa", "kapok", 
        "berisik", "ramai", "bising", "jorok", "antri", "kurang", "tidak ada",
        "parah", "jauh", "ribet", "mahal", "pungli", "kasar", "judes", "lambat",
        "mati", "hilang", "bocor", "becek", "lumpur"
    ]
}

# Definisi Kategori Pengunjung (Untuk Badge "Cocok Untuk")
VISITOR_TYPES = {
    # 1. Berdasarkan Level Skill
    "keluarga": [
        "anak", "keluarga", "bocah", "balita", "orang tua", "family", 
        "kids", "ramah anak", "playground", "toilet bersih", "aman"
    ],
    "pemula": [
        "baru", "pertama", "nyoba", "pemula", "mudah", "sewa tenda",
        "gak ribet", "anti ribet", "praktis", "full service"
    ],
    "petualang": [ # a.k.a Veteran / Hardcore
        "trekking", "jalan kaki", "jauh", "masuk hutan", "ekstrem",
        "mendaki", "hiking", "track", "trail", "survival", "semak",
        "liar", "bushcraft", "sepi banget", "hutan belantara"
    ],

    # 2. Berdasarkan Gaya Camping (Tren Baru)
    "campervan": [ # Motocamp / Car Camping
        "mobil", "motor", "samping tenda", "parkir luas", "campervan",
        "motocamp", "bisa masuk mobil", "kendaraan", "rooftop tent"
    ],
    "healing": [ # Pencari Ketenangan
        "tenang", "syahdu", "sunyi", "bengong", "damai", "healing",
        "santai", "relax", "kabut", "dingin", "suara sungai", "gemericik"
    ],
    "glamping": [ # Kategori Mewah
        "glamping", "villa", "kabin", "cabin", "kasur", "bed", "private",
        "kamar mandi dalam", "water heater", "air panas", "mewah"
    ]
}