#!/usr/bin/env python3
"""
Donanimarsivi Sıcak Fırsatlar Forum Takip Botu
────────────────────────────────────────────────
Her dakika structItem-title div'lerini kontrol eder.
Takip listenizdeki ürünler başlıkta geçerse Telegram bildirimi gönderir.
"""

import re
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from notifier import telegram_gonder

# Windows terminal emoji sorunu için
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ══════════════════════════════════════════
#  AYARLAR
# ══════════════════════════════════════════

FORUM_URL       = "https://forum.donanimarsivi.com/forumlar/Sicakfirsatlar/"
GORULMUS_DOSYA  = Path(__file__).parent / "gorulmus_ilanlar.json"
KONTROL_ARALIGI = 60          # saniye
MAX_HATALI_ISTEK = 60         # Bu kadar ardışık hatadan sonra Telegram'a bildir (60dk = 1 saat)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# ══════════════════════════════════════════
#  TAKİP LİSTESİ  ← buradan düzenle
# ══════════════════════════════════════════

# Her satır bir arama deseni.  Büyük/küçük harf fark etmez.
# Başlıkta bu metin GEÇİYORSA bildirim gönderilir.

ANAKARTLAR: list[str] = [
    "Gigabyte B650",
    "ASUS TUF Gaming B650-Plus",
    "Gigabyte B650 AORUS Elite AX",
    "ASUS TUF Gaming B860",
    "Gigabyte B760M",
]

ISLEMCILER: list[str] = [
    "7800X3D",
    "9800X3D",
    "9700X",
    "9600X",
    "7700X",
    "Core Ultra 7 265K",
    "Core Ultra 5 250K",
    "Core Ultra 5 245K",
    # Kısa versiyonlar — yukarıdakiler tutmazsa bunlar yakalar
    "265K",
    "250K",
    "245K",
]

EKRAN_KARTLARI: list[str] = [
    "RX 9070 XT",
    "9070 XT",
]

# RAM: DDR5 + 16 GB ve üzeri → özel fonksiyon (aşağıda)
RAM_MIN_GB   = 16
RAM_TIP      = "ddr5"

# ══════════════════════════════════════════
#  GÖRÜLMÜŞ İLAN HAFIZASI
# ══════════════════════════════════════════

def gorulmusleri_yukle() -> set[str]:
    if GORULMUS_DOSYA.exists():
        try:
            return set(json.loads(GORULMUS_DOSYA.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def gorulmusleri_kaydet(gorulmusler: set[str]) -> None:
    # Sonsuz büyümesini önle: son 2000 kaydı tut
    liste = sorted(gorulmusler)[-2000:]
    GORULMUS_DOSYA.write_text(
        json.dumps(liste, ensure_ascii=False, indent=2), encoding="utf-8"
    )

# ══════════════════════════════════════════
#  EŞLEŞTİRME MANTIĞI
# ══════════════════════════════════════════

def ram_eslesme(baslik: str) -> bool:
    """DDR5 + belirtilen min GB'ın üzeri mi?"""
    b = baslik.lower()
    if RAM_TIP not in b:
        return False
    # Başlıktaki tüm "XGB" değerlerini bul
    sayilar = re.findall(r'(\d{1,4})\s*gb', b)
    if not sayilar:
        return False
    return max(int(s) for s in sayilar) >= RAM_MIN_GB


def eslesme_kontrol(baslik: str) -> tuple[bool, str, str]:
    """
    Returns:
        (eşleşti_mi, kategori_etiketi, eşleşen_desen)
    """
    b = baslik.lower()

    for desen in ANAKARTLAR:
        if desen.lower() in b:
            return True, "🖥️ ANAKART", desen

    for desen in ISLEMCILER:
        if desen.lower() in b:
            return True, "⚙️ İŞLEMCİ", desen

    for desen in EKRAN_KARTLARI:
        if desen.lower() in b:
            return True, "🎮 EKRAN KARTI", desen

    if ram_eslesme(baslik):
        return True, f"💾 DDR5 RAM ({RAM_MIN_GB}GB+)", "DDR5"

    return False, "", ""

# ══════════════════════════════════════════
#  FORUM SCRAPER
# ══════════════════════════════════════════

def forum_ilanlarini_cek() -> list[dict]:
    """
    Forum ana sayfasından structItem-title div'lerini çeker.
    Her eleman: {"baslik": str, "link": str}
    """
    try:
        r = requests.get(FORUM_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = "utf-8"
    except requests.exceptions.RequestException as e:
        print(f"  [HATA] Forum erişim hatası: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    ilanlar: list[dict] = []

    for div in soup.select("div.structItem-title"):
        # Donanimarsivi XenForo: thread linki /konu/ içerir.
        # labelLink class'ı prefix etiketi (örn. 🔥İndirim) — atla.
        a = div.find("a", href=re.compile(r'/konu/'), class_=lambda c: c != "labelLink")
        if not a:
            # labelLink olmayanı al (prefix etiketi değil)
            a = div.find("a", class_=lambda c: c != "labelLink")
        if not a:
            continue

        baslik = a.get_text(strip=True)
        href   = a.get("href", "")

        if href and not href.startswith("http"):
            href = "https://forum.donanimarsivi.com" + href

        if baslik and href:
            ilanlar.append({"baslik": baslik, "link": href})

    return ilanlar

# ══════════════════════════════════════════
#  TELEGRAM MESAJ ŞABLONU
# ══════════════════════════════════════════

def bildirim_mesaji(baslik: str, link: str, kategori: str, desen: str) -> str:
    zaman = datetime.now().strftime("%d.%m.%Y %H:%M")
    return (
        f"{kategori} <b>YENİ FIRSAT İLANI!</b>\n\n"
        f"📌 <b>{baslik}</b>\n\n"
        f"🔍 Eşleşen: <code>{desen}</code>\n"
        f"🕐 {zaman}\n\n"
        f"🔗 <a href='{link}'>İlanı Görüntüle →</a>\n\n"
        f"📍 <i>Donanimarsivi Sıcak Fırsatlar</i>"
    )


# ══════════════════════════════════════════
#  ANA DÖNGÜ
# ══════════════════════════════════════════

def main() -> None:
    print("=" * 55)
    print("  🔍 Donanimarsivi Forum Takip Botu")
    print("=" * 55)
    print(f"  📡 URL     : {FORUM_URL}")
    print(f"  ⏱️  Aralık  : Her {KONTROL_ARALIGI} saniye (1 dakika)")
    print(f"  🖥️  Anakart : {len(ANAKARTLAR)} model")
    print(f"  ⚙️  İşlemci : {len(set(ISLEMCILER))} desen")
    print(f"  💾  RAM     : DDR5 {RAM_MIN_GB}GB+")
    print("=" * 55 + "\n")

    gorulmusler  = gorulmusleri_yukle()
    hatali_istek = 0

    print(f"📂 Hafızada {len(gorulmusler)} önceki ilan var.\n")

    while True:
        zaman = datetime.now().strftime("%H:%M:%S")
        print(f"[{zaman}] 🔄 Kontrol başlıyor...")

        ilanlar = forum_ilanlarini_cek()

        # ── Erişim hatası takibi ─────────────────────────────
        if not ilanlar:
            hatali_istek += 1
            print(f"  ⚠️  İlan alınamadı (ardışık hata: {hatali_istek})")
            if hatali_istek >= MAX_HATALI_ISTEK:
                telegram_gonder(
                    f"⚠️ <b>Forum Takip Botu Uyarısı</b>\n\n"
                    f"Son {hatali_istek} kontrolde forum sayfasına erişilemedi.\n"
                    f"Bot çalışmaya devam ediyor..."
                )
                hatali_istek = 0
            time.sleep(KONTROL_ARALIGI)
            continue

        hatali_istek = 0
        print(f"  📋 {len(ilanlar)} başlık alındı")

        yeni_sayisi     = 0
        eslesme_sayisi  = 0

        for ilan in ilanlar:
            link   = ilan["link"]
            baslik = ilan["baslik"]

            # Daha önce görüldüyse atla
            if link in gorulmusler:
                continue

            gorulmusler.add(link)
            yeni_sayisi += 1

            # Eşleşme kontrolü
            eslesti, kategori, desen = eslesme_kontrol(baslik)

            if eslesti:
                print(f"  ✅ EŞLEŞTİ [{kategori}] → {baslik[:55]}")
                mesaj  = bildirim_mesaji(baslik, link, kategori, desen)
                basari = telegram_gonder(mesaj)
                durum  = "📨 Gönderildi" if basari else "❌ Telegram hatası"
                print(f"     {durum}")
                eslesme_sayisi += 1
            else:
                print(f"  ⬜ Yeni (eşleşmedi): {baslik[:55]}")

        # ── Durum özeti ──────────────────────────────────────
        if yeni_sayisi == 0:
            print("  ✅ Yeni ilan yok.")
        elif eslesme_sayisi > 0:
            print(f"  🎯 {eslesme_sayisi} eşleşme bildirimi gönderildi!")

        gorulmusleri_kaydet(gorulmusler)
        print(f"  ⏳ {KONTROL_ARALIGI} saniye bekleniyor...\n")
        time.sleep(KONTROL_ARALIGI)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot durduruldu (Ctrl+C).")
        sys.exit(0)
