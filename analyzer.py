"""Dinamik fiyat eşiği hesaplama.

Her DDR tipi (DDR4, DDR5) için ayrı ayrı:
  - Ortalama fiyat/GB hesapla
  - Eşik = ortalama * (1 - ESIK_YUZDE/100)
  - Bir ürünün fiyat/GB değeri eşiğin altına düşerse bildir
"""
import json
import os
from collections import defaultdict
from config import ESIK_YUZDE, AVERAGES_FILE


def ortalama_hesapla(urunler: list[dict]) -> dict:
    """
    Her DDR tipi için ortalama fiyat/GB hesaplar.
    Dönüş: {"DDR4": {"ort_fiyat_per_gb": 250.0, "urun_sayisi": 12}, ...}
    """
    gruplar = defaultdict(list)

    for u in urunler:
        if u["fiyat_per_gb"] > 0 and u["ddr"] != "UNKNOWN":
            gruplar[u["ddr"]].append(u["fiyat_per_gb"])

    sonuc = {}
    for ddr, degerler in gruplar.items():
        if not degerler:
            continue
        # Aykırı değerleri temizle: %10-%90 arası kullan
        degerler_s = sorted(degerler)
        kes_alt = max(0, int(len(degerler_s) * 0.10))
        kes_ust = max(1, int(len(degerler_s) * 0.90))
        temiz = degerler_s[kes_alt:kes_ust] if kes_ust > kes_alt else degerler_s
        ort = sum(temiz) / len(temiz)
        sonuc[ddr] = {
            "ort_fiyat_per_gb": round(ort, 1),
            "urun_sayisi": len(degerler),
            "esik_fiyat_per_gb": round(ort * (1 - ESIK_YUZDE / 100), 1),
        }

    return sonuc


def ortalama_kaydet(averages: dict):
    with open(AVERAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(averages, f, ensure_ascii=False, indent=2)


def ortalama_yukle() -> dict:
    if os.path.exists(AVERAGES_FILE):
        with open(AVERAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def esik_alti_urunler(urunler: list[dict], averages: dict) -> list[dict]:
    """
    Fiyat/GB değeri kendi DDR tipinin eşiğinin altında olan ürünleri döner.
    """
    alti = []
    for u in urunler:
        ddr = u["ddr"]
        if ddr not in averages or u["fiyat_per_gb"] <= 0:
            continue
        esik = averages[ddr]["esik_fiyat_per_gb"]
        ort  = averages[ddr]["ort_fiyat_per_gb"]
        if u["fiyat_per_gb"] <= esik:
            alti.append({
                **u,
                "esik":    esik,
                "ortalama": ort,
                "indirim_yuzdesi": round((1 - u["fiyat_per_gb"] / ort) * 100, 1),
            })
    return alti
