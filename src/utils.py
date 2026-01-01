import pandas as pd
import os
import joblib
import streamlit as st
from datetime import datetime

# ==============================================================================
# KONFIGURASI PATH
# ==============================================================================
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SRC_DIR)

# Path untuk Log CSV
LOG_FILE_PATH = os.path.join(BASE_DIR, 'Riwayat', 'riwayat_pencarian.csv')
# Kita kembalikan kolom 'tokens' agar sesuai dengan format lama
LOG_COLS = ['timestamp', 'query_mentah', 'tokens', 'intent_terdeteksi', 'region_terdeteksi']

# ==============================================================================
# FUNGSI PEMUAT ASET
# ==============================================================================
def load_metadata():
    """ Memuat Metadata (df_metadata.pkl) untuk UI. """
    assets_dir = os.path.join(BASE_DIR, 'Assets')
    metadata_path = os.path.join(assets_dir, 'df_metadata.pkl')
    
    try:
        if os.path.exists(metadata_path):
            return joblib.load(metadata_path)
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ ERROR saat memuat metadata: {e}")
        return pd.DataFrame()

def load_map_from_csv(filename):
    """ Memuat file CSV Kamus. """
    filepath = os.path.join(BASE_DIR, 'Kamus', filename)
    try:
        if not os.path.exists(filepath): return {}
        df = pd.read_csv(filepath, comment='#', dtype=str).fillna('')
        if df.empty: return {}
        
        # Ambil kolom 1 (Key) dan 2 (Value)
        key_col = df.columns[0]
        value_col = df.columns[1]
        df = df.dropna(subset=[key_col, value_col])
        return pd.Series(df[value_col].values, index=df[key_col]).to_dict()
    except:
        return {}

# ==============================================================================
# FUNGSI LOGGING (PERBAIKAN COMPATIBILITY)
# ==============================================================================

def log_pencarian_csv(query, tokens, intent, region):
    """
    Mencatat riwayat ke CSV.
    DIPERBAIKI: Menerima 4 argumen (query, tokens, intent, region) agar tidak crash.
    """
    try:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Ubah list tokens jadi string agar bisa disimpan di CSV
        if isinstance(tokens, list):
            tokens_str = " ".join(tokens)
        else:
            tokens_str = str(tokens)
        
        # Simpan data lengkap
        data_baru = pd.DataFrame(
            [[timestamp, query, tokens_str, str(intent), str(region)]], 
            columns=LOG_COLS
        )
        
        file_exists = os.path.exists(LOG_FILE_PATH)
        
        data_baru.to_csv(
            LOG_FILE_PATH, 
            mode='a', 
            header=not file_exists, 
            index=False
        )
    except Exception as e:
        print(f"⚠️ GAGAL mencatat riwayat ke CSV: {e}")

def baca_riwayat_csv(limit=50):
    """ Membaca log untuk Admin Dashboard """
    try:
        if not os.path.exists(LOG_FILE_PATH):
            return pd.DataFrame(columns=LOG_COLS)
        df = pd.read_csv(LOG_FILE_PATH)
        return df.iloc[::-1].head(limit)
    except:
        return pd.DataFrame(columns=LOG_COLS)

def log_pencarian_gsheets(query, tokens, intent, region):
    """ 
    Mencatat ke Google Sheets.
    DIPERBAIKI: Menerima 4 argumen juga.
    """
    try:
        conn = st.connection("gsheets", type="gsheets")
        
        if isinstance(tokens, list):
            tokens_str = " ".join(tokens)
        else:
            tokens_str = str(tokens)

        data_baru = pd.DataFrame({
            "timestamp": [datetime.now()],
            "queri_mentah": [query],
            "vsm_tokens_final": [tokens_str], # Sesuaikan nama kolom di GSheets Anda
            "intent_terdeteksi": [str(intent)],
            "region_terdeteksi": [str(region)]
        })
        conn.append_rows(worksheet="LogData", data=data_baru)
    except Exception as e:
        pass