"""
GPU fiyat scraper: Amazon.com.tr + Vatanbilgisayar.com + itopya.com
Ürün: RX 9070 XT
"""
import re
from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

ITOPYA_URL  = "https://www.itopya.com/ekran-karti_k11?grafikislemcisi=radeon-rx-9070-xt-q7704"
AMAZON_URL  = "https://www.amazon.com.tr/s?k=radeon+rx+9070+xt&s=price-asc-rank"
VATAN_URL   = "https://www.vatanbilgisayar.com/arama/rx%209070%20xt/?siralama=fiyat-artan"


def fiyat_parse(fiyat_str: str) -> float:
    """'41.337,57 TL' -> 41337.57"""
    temiz = re.sub(r"[^\d,]", "", fiyat_str).replace(",", ".")
    try:
        return float(temiz)
    except ValueError:
        return 0.0


def _itopya_cek(page) -> list[dict]:
    page.goto(ITOPYA_URL, wait_until="networkidle", timeout=35000)
    page.wait_for_timeout(4000)

    data = page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('.product-block').forEach(card => {
            const nameEl  = card.querySelector('a.title');
            const priceEl = card.querySelector('span.product-price strong');
            if (!nameEl || !priceEl) return;

            const name = nameEl.innerText.trim();
            if (!name.includes('9070') || !name.toUpperCase().includes('XT')) return;

            // Fiyat: "41.337,57 TL" -> abbr'yi strip et
            const fiyatStr = priceEl.innerText.trim().replace('TL','').trim();

            const href = nameEl.getAttribute('href') || '';
            const link = href.startsWith('http') ? href
                         : 'https://www.itopya.com' + href;

            items.push({
                isim:      name,
                fiyat_str: fiyatStr,
                link:      link,
                kaynak:    'itopya'
            });
        });
        return items;
    }""")
    return data


def _amazon_cek(page) -> list[dict]:
    page.goto(AMAZON_URL, wait_until="networkidle", timeout=35000)
    page.wait_for_timeout(4000)

    for btn in ["Kabul Et", "Accept All", "Tümünü Kabul Et"]:
        try:
            page.click(f"text={btn}", timeout=2000)
            page.wait_for_timeout(500)
            break
        except Exception:
            pass

    data = page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('[data-component-type="s-search-result"]').forEach(card => {
            const nameEl  = card.querySelector('h2 span');
            const priceEl = card.querySelector('.a-price .a-offscreen');
            const linkEl  = card.querySelector('h2 a');
            if (!nameEl || !priceEl) return;
            const name = nameEl.innerText.trim();
            if (!name.includes('9070') || !name.toUpperCase().includes('XT')) return;
            // Hazir PC paketlerini cikar
            if (name.includes('Ryzen') || name.includes('Intel') ||
                name.includes('UNLOST') || name.includes('AMD R')) return;
            items.push({
                isim:      name,
                fiyat_str: priceEl.innerText.trim(),
                link:      linkEl ? 'https://www.amazon.com.tr' + linkEl.getAttribute('href') : '',
                kaynak:    'Amazon'
            });
        });
        return items;
    }""")
    return data


def _vatan_cek(page) -> list[dict]:
    page.goto("https://www.vatanbilgisayar.com/", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(1500)
    try:
        page.click("text=Tümünü Kabul Et", timeout=3000)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    page.goto(VATAN_URL, wait_until="networkidle", timeout=35000)
    page.wait_for_timeout(5000)

    data = page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('.product-list.product-list--list-page').forEach(card => {
            const nameEl  = card.querySelector('h3');
            const priceEl = card.querySelector('.product-list__price');
            const linkEl  = card.querySelector('a.product-list-link');
            if (!nameEl || !priceEl) return;
            const name = nameEl.innerText.trim();
            if (!name.includes('9070') || !name.toUpperCase().includes('XT')) return;
            // Hazir PC paketlerini cikar
            if (name.includes('SSD') || name.includes('RAM') ||
                name.includes('Ryzen') || name.includes('Intel') ||
                name.includes('RYZEN') || name.includes('INTEL')) return;
            items.push({
                isim:      name,
                fiyat_str: priceEl.innerText.trim(),
                link:      linkEl ? linkEl.href : '',
                kaynak:    'Vatanbilgisayar'
            });
        });
        return items;
    }""")
    return data


def gpu_fiyatlarini_cek() -> list[dict]:
    """itopya + Amazon + Vatanbilgisayar'dan RX 9070 XT fiyatlarını çek."""
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

        for isim, fn in [("itopya", _itopya_cek),
                         ("Amazon", _amazon_cek),
                         ("Vatanbilgisayar", _vatan_cek)]:
            try:
                data = fn(page)
                print(f"  {isim}: {len(data)} ürün")
                for item in data:
                    fiyat = fiyat_parse(item["fiyat_str"])
                    if fiyat > 0:
                        urunler.append({
                            "isim":   item["isim"],
                            "fiyat":  fiyat,
                            "kaynak": item["kaynak"],
                            "link":   item["link"],
                        })
            except Exception as e:
                print(f"  {isim} HATA: {e}")

        browser.close()

    urunler.sort(key=lambda x: x["fiyat"])
    return urunler
