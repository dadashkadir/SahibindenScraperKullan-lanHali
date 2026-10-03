"""Tek bir liste sayfasındaki ilanları okur."""
import asyncio
from .utils import ROW_SELECTOR, goto, wait_until_ready, random_sleep

_JS = """
elements => elements.map(el => {
    const txt = s => { const n = el.querySelector(s); return n ? n.innerText.trim() : ''; };
    const titleEl = el.querySelector('td.searchResultsTitleValue a.classifiedTitle')
                 || el.querySelector('td.searchResultsTitleValue a');
    const title = titleEl ? (titleEl.getAttribute('title') || titleEl.innerText.trim()) : '';
    const url = titleEl ? titleEl.href : '';
    const price = txt('td.searchResultsPriceValue .classified-price-container span')
               || txt('td.searchResultsPriceValue');
    const location = txt('td.searchResultsLocationValue');
    const attrs = Array.from(el.querySelectorAll('td.searchResultsAttributeValue')).map(a => a.innerText.trim());
    return {id: el.getAttribute('data-id'), title, url, price, location, attrs};
})
"""


def _split_attrs(attrs):
    """Sütun sırasına güvenmeden, içeriğe bakarak oda ve m² ayırır.
    '3+1' -> oda, saf sayı -> m². (Eski kod ilk sütunu oda sanıyordu.)"""
    room, m2 = "", ""
    for a in attrs:
        a = a.strip()
        if not a:
            continue
        if "+" in a and any(ch.isdigit() for ch in a) and len(a) <= 6:
            room = room or a
        elif a.replace(".", "").replace(",", "").isdigit():
            m2 = m2 or a
    return room, m2


async def scrape_page(page, url: str, page_num: int):
    print(f"\n  Sayfa {page_num} yükleniyor...")
    await goto(page, url)
    ok = await wait_until_ready(page, wait_seconds=180 if page_num == 1 else 60)
    if not ok:
        print("  UYARI: Sayfa hazır olmadı / ilan bulunamadı.")
        return []
    await random_sleep(1000, 2000)
    for _ in range(3):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.6)

    raw = await page.eval_on_selector_all(ROW_SELECTOR, _JS)
    listings = []
    for r in raw:
        room, m2 = _split_attrs(r.pop("attrs"))
        r["room"] = room
        r["gross_m2"] = m2      # listede tek m² sütunu var (net/brüt ayrımı yok)
        r["net_m2"] = ""
        listings.append(r)
    print(f"  {len(listings)} ilan okundu.")
    return listings
