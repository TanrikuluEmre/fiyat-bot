import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def telegram_gonder(mesaj: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mesaj,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[HATA] Telegram: {e}")
        return False


def baslangiç_mesaji(averages: dict) -> str:
    satirlar = ["🤖 <b>RAM Fiyat Botu Başladı!</b>\n"]
    for ddr, v in sorted(averages.items()):
        satirlar.append(
            f"📊 <b>{ddr}</b>\n"
            f"   Ort. fiyat/GB: {v['ort_fiyat_per_gb']:,.0f} TL\n"
            f"   Bildirim eşiği (%50 altı): <b>{v['esik_fiyat_per_gb']:,.0f} TL/GB</b>\n"
            f"   ({v['urun_sayisi']} ürün analiz edildi)"
        )
    satirlar.append("\n⏰ Her 10 dakikada kontrol ediyorum.")
    return "\n".join(satirlar)


def esik_alti_mesaji(u: dict) -> str:
    link = u["link"]
    return (
        f"🚨 <b>FIRTINA FİYAT!</b>\n\n"
        f"📦 <b>{u['isim']}</b>\n\n"
        f"💾 {u['ddr']} | {u['kapasite_gb']}GB\n"
        f"💥 Fiyat: <b>{u['fiyat']:,.0f} TL</b> ({u['fiyat_per_gb']:,.0f} TL/GB)\n"
        f"📊 {u['ddr']} ortalaması: {u['ortalama']:,.0f} TL/GB\n"
        f"📉 Ortalamadan <b>%{u['indirim_yuzdesi']:.0f} ucuz!</b>\n\n"
        f"🔗 <a href='{link}'>Ürün Sayfasına Git</a>\n"
        f"🛒 <a href='{link}'>Sepete Ekle (ürün sayfasından)</a>"
    )


def gpu_esik_alti_mesaji(u: dict, esik: int, eski_fiyat: float = None) -> str:
    degisim = ""
    if eski_fiyat and eski_fiyat != u["fiyat"]:
        fark = eski_fiyat - u["fiyat"]
        degisim = f"\n📉 Düşüş: <b>{fark:,.0f} TL</b> ({(fark/eski_fiyat*100):.1f}%)"
    return (
        f"🎮 <b>RX 9070 XT FİYAT ALARMI!</b>\n\n"
        f"📦 <b>{u['isim'][:70]}</b>\n\n"
        f"🏪 Kaynak: <b>{u['kaynak']}</b>\n"
        f"💥 Fiyat: <b>{u['fiyat']:,.0f} TL</b>{degisim}\n"
        f"🎯 Eşik: {esik:,.0f} TL\n\n"
        f"🔗 <a href='{u['link']}'>Ürün Sayfasına Git</a>"
    )


def ozet_mesaji(urunler: list[dict], averages: dict) -> str:
    satirlar = ["📊 <b>Günlük RAM Fiyat Özeti</b>\n"]
    for ddr in ["DDR4", "DDR5"]:
        if ddr not in averages:
            continue
        v = averages[ddr]
        grup = [u for u in urunler if u["ddr"] == ddr][:3]
        satirlar.append(
            f"<b>{ddr}</b> (ort: {v['ort_fiyat_per_gb']:,.0f} TL/GB | "
            f"eşik: {v['esik_fiyat_per_gb']:,.0f} TL/GB)"
        )
        for u in grup:
            satirlar.append(
                f"  • {u['isim'][:45]}...\n"
                f"    {u['fiyat']:,.0f} TL — {u['fiyat_per_gb']:,.0f} TL/GB"
            )
    return "\n".join(satirlar)
