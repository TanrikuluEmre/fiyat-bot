import re
from playwright.sync_api import sync_playwright
from config import FILTRE_KELIME, MIN_KAPASITE_GB, VATAN_RAM_URL

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def fiyat_parse(fiyat_str: str) -> float:
    """'4.689' -> 4689.0  (Türk formatı: nokta = binlik ayıraç)"""
    temiz = fiyat_str.strip().replace(".", "").replace(",", ".")
    try:
        return float(temiz)
    except ValueError:
        return 0.0


def ddr_tipi_bul(isim: str) -> str:
    """İsimden DDR3/DDR4/DDR5 çıkar."""
    m = re.search(r'DDR(\d)', isim, re.IGNORECASE)
    return f"DDR{m.group(1)}" if m else "UNKNOWN"


def kapasite_bul(isim: str) -> int:
    """İsimden GB kapasitesini çıkar. Örn: '16GB (1x16GB)' -> 16"""
    # Önce toplam kapasiteyi bul: 32GB, 16GB, 8GB, vs.
    m = re.search(r'(\d+)GB\s*\(', isim, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*GB', isim, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def ram_fiyatlarini_cek() -> list[dict]:
    urunler = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="tr-TR",
            extra_http_headers={"Accept-Language": "tr-TR,tr;q=0.9"},
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Çerez kabul
        page.goto("https://www.vatanbilgisayar.com/", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(1500)
        try:
            page.click("text=Tümünü Kabul Et", timeout=3000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        page.goto(VATAN_RAM_URL, wait_until="networkidle", timeout=40000)
        page.wait_for_timeout(6000)

        data = page.evaluate("""() => {
            const cards = document.querySelectorAll(
                '.product-list.product-list--list-page'
            );
            const result = [];
            for (const card of cards) {
                const nameEl  = card.querySelector('h3');
                const priceEl = card.querySelector('.product-list__price');
                const linkEl  = card.querySelector('a.product-list-link');
                if (!nameEl || !priceEl) continue;
                result.push({
                    isim:      nameEl.innerText.trim(),
                    fiyat_str: priceEl.innerText.trim(),
                    link:      linkEl ? linkEl.href : ''
                });
            }
            return result;
        }""")

        browser.close()

    for item in data:
        isim      = item["isim"]
        fiyat     = fiyat_parse(item["fiyat_str"])
        ddr       = ddr_tipi_bul(isim)
        kapasite  = kapasite_bul(isim)

        if fiyat <= 0:
            continue
        if FILTRE_KELIME and FILTRE_KELIME.lower() not in isim.lower():
            continue
        if MIN_KAPASITE_GB > 0 and kapasite < MIN_KAPASITE_GB:
            continue

        fiyat_per_gb = round(fiyat / kapasite, 1) if kapasite > 0 else 0

        urunler.append({
            "isim":        isim,
            "fiyat":       fiyat,
            "ddr":         ddr,
            "kapasite_gb": kapasite,
            "fiyat_per_gb": fiyat_per_gb,
            "link":        item["link"],
        })

    urunler.sort(key=lambda x: x["fiyat"])
    return urunler
