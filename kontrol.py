"""
GitHub Actions icin tek seferlik fiyat kontrol scripti.
main.py'den farkli olarak schedule loop yok, sadece bir kez calisir.
"""
import json
import os
from datetime import datetime

from config import GPU_ESIK_FIYAT, GPU_PRICES_FILE, PRICES_FILE, ESIK_YUZDE
from scraper import ram_fiyatlarini_cek
from gpu_scraper import gpu_fiyatlarini_cek
from analyzer import ortalama_hesapla, ortalama_kaydet, ortalama_yukle, esik_alti_urunler
from notifier import telegram_gonder, esik_alti_mesaji, gpu_esik_alti_mesaji


def json_yukle(dosya: str) -> dict:
    if os.path.exists(dosya):
        with open(dosya, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def json_kaydet(dosya: str, data: dict):
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ram_kontrol():
    print("  [RAM] Kontrol ediliyor...")
    try:
        urunler = ram_fiyatlarini_cek()
    except Exception as e:
        print(f"  [RAM][HATA] {e}")
        return

    if not urunler:
        print("  [RAM] Urun cekilemedi.")
        return

    print(f"  [RAM] {len(urunler)} urun bulundu.")
    averages = ortalama_hesapla(urunler)
    ortalama_kaydet(averages)

    for ddr, v in sorted(averages.items()):
        print(f"    {ddr}: ort={v['ort_fiyat_per_gb']:,.0f} | esik={v['esik_fiyat_per_gb']:,.0f} TL/GB")

    alti = esik_alti_urunler(urunler, averages)
    if alti:
        print(f"  [RAM] *** {len(alti)} firsat urun! ***")
        for u in alti:
            telegram_gonder(esik_alti_mesaji(u))
            print(f"    Bildirim: {u['isim'][:45]} - {u['fiyat']:,.0f} TL")
    else:
        print(f"  [RAM] Esik alti urun yok.")

    json_kaydet(PRICES_FILE, {u["isim"]: u["fiyat"] for u in urunler})


def gpu_kontrol():
    print("  [GPU] RX 9070 XT kontrol ediliyor...")
    try:
        urunler = gpu_fiyatlarini_cek()
    except Exception as e:
        print(f"  [GPU][HATA] {e}")
        return

    if not urunler:
        print("  [GPU] Urun cekilemedi.")
        return

    en_ucuz = urunler[0]
    print(f"  [GPU] {len(urunler)} urun | En ucuz: {en_ucuz['kaynak']} - {en_ucuz['fiyat']:,.0f} TL")

    eski_fiyatlar = json_yukle(GPU_PRICES_FILE)
    bildirim_gonderildi = False

    for u in urunler:
        anahtar = f"{u['kaynak']}_{u['isim'][:50]}"
        eski = eski_fiyatlar.get(anahtar)

        if u["fiyat"] < GPU_ESIK_FIYAT:
            if eski is None or u["fiyat"] < eski:
                mesaj = gpu_esik_alti_mesaji(u, GPU_ESIK_FIYAT, eski)
                basari = telegram_gonder(mesaj)
                durum = "OK" if basari else "HATA"
                print(f"  [GPU][Bildirim {durum}] {u['kaynak']} - {u['fiyat']:,.0f} TL")
                bildirim_gonderildi = True

    if not bildirim_gonderildi:
        print(f"  [GPU] Esik alti ({GPU_ESIK_FIYAT:,.0f} TL) urun yok. "
              f"En ucuz: {en_ucuz['fiyat']:,.0f} TL ({en_ucuz['kaynak']})")

    yeni = {f"{u['kaynak']}_{u['isim'][:50]}": u["fiyat"] for u in urunler}
    json_kaydet(GPU_PRICES_FILE, yeni)


if __name__ == "__main__":
    zaman = datetime.now().strftime("%d.%m.%Y %H:%M")
    print(f"\n[{zaman}] Kontrol basliyor...")
    ram_kontrol()
    gpu_kontrol()
    print(f"[{zaman}] Tamamlandi.")
