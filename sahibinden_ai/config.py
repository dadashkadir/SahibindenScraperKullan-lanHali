"""Ayarlar."""
import sys
import os
from pathlib import Path

CDP_PORT = 9222

# Exe'nin (veya geliştirme sırasında proje klasörünün) yanındaki klasörler
if getattr(sys, "frozen", False):
    # Yazılabilir bir konum: Kullanıcı AppData\Local\SahibindenAI
    base = Path(os.getenv("LOCALAPPDATA", Path(sys.executable).parent)) / "SahibindenAI"
else:
    base = Path(__file__).resolve().parent.parent

PROFILE_DIR = base / "chrome_profile"   # giriş/çerez bilgileri burada saklanır
OUTPUT_DIR = base / "cikti"             # txt / json / pdf çıktıları
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.sahibinden.com"
TRANSACTION = "satilik"
ITEMS_PER_PAGE = 20
MAX_PAGES = 50          # sahibinden en fazla 50 sayfa gösterir

# Emlak tipi -> sahibinden kategori yolu
ESTATE_TYPES = {
    "Daire":  "satilik-daire",
    "Villa":  "satilik-villa",
    "Arsa":   "satilik-arsa",
    "İşyeri": "satilik-isyeri",
}
ROOM_TYPES = {"Daire", "Villa"}   # oda sayısı sadece bunlarda sorulur

# ---------- Vasıta (Araç) Kategorileri ----------
# Satılık araç kategorileri (slug = path segment after domain)
VEHICLE_CATEGORIES_SATILIK = {
    "Otomobil": "otomobil",
    "Arazi / SUV / Pickup": "arazi-suv-pickup",
    "Elektrikli Araçlar": "elektrikli-araclar",
    "Motorsiklet": "motorsiklet",
    "Minivan / Panelvan": "minivan-panelvan",
    "Ticari Araçlar": "ticari-araclar",
    "Deniz Araçları": "deniz-araclari",
    "Hasarlı Araçlar": "hasarli-araclar",
    "Karavan": "karavan",
    "Klasik Araçlar": "klasik-araclar",
    "Hava Araçları": "hava-araclari",
    "ATV / UTV / Engelli Plakalı": "atv-utv-engelli-plakali",
}

# Kiralık araç kategorileri (tek kategori genelde)
VEHICLE_CATEGORIES_KIRALIK = {
    "Kiralık Araçlar": "kiralik-araclar",
}

# Vasıta filtre parametreleri (sahibinden query parametreleri)
VEHICLE_FILTER_MAP = {
    # Yıl aralığı (genelde a5)
    "year_min": "a5_min",
    "year_max": "a5_max",
    # Kilometre aralığı (genelde a4)
    "km_min": "a4_min",
    "km_max": "a4_max",
    # Fiyat
    "price_min": "price_min",
    "price_max": "price_max",
    # Yakıt, vites, kasa, renk vs. a812 çoklu seçim
    # Örnek değerler kategori bazlı değişir; kullanıcıdan çoklu seçim alıp a812=... tekrar ederiz.
    "fuel": "a812",          # yakıt tipi
    "gear": "a812",          # vites tipi
    "body": "a812",          # kasa tipi
    "color": "a812",         # renk
}
