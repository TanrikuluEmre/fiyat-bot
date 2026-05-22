# ========================
# AYARLAR
# ========================
import os
from pathlib import Path

# .env dosyasını yükle (local çalışma için)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# Kontrol aralığı (dakika)
KONTROL_ARALIGI_DAKIKA = 10

# Ortalama fiyatın yüzde kaç altına düşünce bildirim gönderilsin
# 50 = ortalama fiyatın %50 altına düşerse bildir
ESIK_YUZDE = 50

# Sadece bu kelimeyi içeren ürünleri izle (boş = hepsi)
# Örnekler: "16GB", "DDR5", "Kingston"
FILTRE_KELIME = ""

# Minimum kapasite filtresi (GB) - 0 = filtre yok
MIN_KAPASITE_GB = 0

# URL ve dosyalar
VATAN_RAM_URL = "https://www.vatanbilgisayar.com/bilgisayar-ram-bellek/?siralama=fiyat-artan"
PRICES_FILE   = "prices.json"
AVERAGES_FILE = "averages.json"

# ========================
# GPU TAKİP AYARLARI
# ========================

# RX 9070 XT fiyat eşiği (TL) - bu fiyatın altına düşerse bildirim gelir
GPU_ESIK_FIYAT = 30000

# GPU fiyat geçmişi dosyası
GPU_PRICES_FILE = "gpu_prices.json"
