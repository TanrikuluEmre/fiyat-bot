import json
import os
import time
import schedule
from datetime import datetime

from config import (
    KONTROL_ARALIGI_DAKIKA, PRICES_FILE, ESIK_YUZDE,
    GPU_ESIK_FIYAT, GPU_PRICES_FILE
)
from scraper import ram_fiyatlarini_cek
from gpu_scraper import gpu_fiyatlarini_cek
from analyzer import ortalama_hesapla, ortalama_kaydet, ortalama_yukle, esik_alti_urunler
from notifier import (
    telegram_gonder, baslangiç_mesaji,
    esik_alti_mesaji, gpu_esik_alti_mesaji
)


# ── Yardımcı fonksiyonlar ──────────────────────────────────────────────────

def json_yukle(dosya: str) -> dict:
    if os.path.exists(dosya):
        with open(dosya, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def json_kaydet(dosya: str, data: dict):
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── RAM Kontrolü ───────────────────────────────────────────────────────────

def ram_kontrol():
    print("  [RAM] Kontrol ediliyor...")
    try:
        urunler = ram_fiyatlarini_cek()
    except Exception as e:
        print(f"  [RAM][HATA] {e}")
        return

    if not urunler:
        print("  [RAM] Ürün çekilemedi.")
        return

    print(f"  [RAM] {len(urunler)} ürün bulundu.")
    averages = ortalama_hesapla(urunler)
    ortalama_kaydet(averages)

    for ddr, v in sorted(averages.items()):
        print(f"    {ddr}: ort={v['ort_fiyat_per_gb']:,.0f} | "
              f"eşik={v['esik_fiyat_per_gb']:,.0f} TL/GB")

    alti = esik_alti_urunler(urunler, averages)
    if alti:
        print(f"  [RAM] *** {len(alti)} firsat ürün! ***")
        for u in alti:
            telegram_gonder(esik_alti_mesaji(u))
            print(f"    Bildirim: {u['isim'][:45]} — {u['fiyat']:,.0f} TL")
    else:
        print(f"  [RAM] Eşik altı ürün yok.")

    json_kaydet(PRICES_FILE, {u["isim"]: u["fiyat"] for u in urunler})


# ── GPU Kontrolü ───────────────────────────────────────────────────────────

def gpu_kontrol():
    print("  [GPU] RX 9070 XT kontrol ediliyor...")
    try:
        urunler = gpu_fiyatlarini_cek()
    except Exception as e:
        print(f"  [GPU][HATA] {e}")
        return

    if not urunler:
        print("  [GPU] Ürün çekilemedi.")
        return

    en_ucuz = urunler[0]
    print(f"  [GPU] {len(urunler)} ürün | En ucuz: "
          f"{en_ucuz['kaynak']} — {en_ucuz['fiyat']:,.0f} TL")

    eski_fiyatlar = json_yukle(GPU_PRICES_FILE)

    bildirim_gonderildi = False
    for u in urunler:
        anahtar = f"{u['kaynak']}_{u['isim'][:50]}"
        eski = eski_fiyatlar.get(anahtar)

        # Esik altina dustuyse VE (ilk kez veya fiyat daha da dustuyse) bildir
        if u["fiyat"] < GPU_ESIK_FIYAT:
            if eski is None or u["fiyat"] < eski:
                mesaj = gpu_esik_alti_mesaji(u, GPU_ESIK_FIYAT, eski)
                basari = telegram_gonder(mesaj)
                durum = "OK" if basari else "HATA"
                print(f"  [GPU][Bildirim {durum}] {u['kaynak']} — "
                      f"{u['fiyat']:,.0f} TL")
                bildirim_gonderildi = True

    if not bildirim_gonderildi:
        print(f"  [GPU] Eşik altı ({GPU_ESIK_FIYAT:,.0f} TL) ürün yok. "
              f"En ucuz: {en_ucuz['fiyat']:,.0f} TL ({en_ucuz['kaynak']})")

    # Fiyatları kaydet
    yeni = {f"{u['kaynak']}_{u['isim'][:50]}": u["fiyat"] for u in urunler}
    json_kaydet(GPU_PRICES_FILE, yeni)


# ── Ana döngü ──────────────────────────────────────────────────────────────

def kontrol_et():
    zaman = datetime.now().strftime("%d.%m.%Y %H:%M")
    print(f"\n[{zaman}] ── Kontrol başlıyor ──")
    ram_kontrol()
    gpu_kontrol()
    print(f"[{zaman}] ── Kontrol tamamlandı ──")


def main():
    print("=" * 55)
    print("  Fiyat Bot v2 — RAM + GPU")
    print(f"  RAM eşiği : Ort. fiyatın %{ESIK_YUZDE} altı")
    print(f"  GPU eşiği : RX 9070 XT < {GPU_ESIK_FIYAT:,.0f} TL")
    print(f"  Kontrol   : Her {KONTROL_ARALIGI_DAKIKA} dakikada bir")
    print("=" * 55)

    # İlk çalıştırma
    kontrol_et()

    # Başlangıç mesajı
    averages = ortalama_yukle()
    if averages:
        telegram_gonder(baslangiç_mesaji(averages))

    # Periyodik zamanlama
    schedule.every(KONTROL_ARALIGI_DAKIKA).minutes.do(kontrol_et)

    print(f"\nBot çalışıyor... (Ctrl+C ile durdur)\n")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
