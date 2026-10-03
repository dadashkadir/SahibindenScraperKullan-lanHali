"""Tüm sayfaları gezip ilanları toplar ve txt/json olarak kaydeder."""
import json
import re

from .config import OUTPUT_DIR, ITEMS_PER_PAGE, MAX_PAGES
from .scraper.list_page import scrape_page
from .scraper.paginator import get_total_pages
from .scraper.utils import random_sleep


def _page_url(base: str, page_num: int) -> str:
    if page_num == 1:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}pagingOffset={(page_num - 1) * ITEMS_PER_PAGE}"


def _norm_room(r: str) -> str:
    return re.sub(r"\s+", "", r or "")


async def run_scrape(page, target_url: str, prefix: str, rooms: str = ""):
    """İlanları döndürür ve <prefix>.txt / .json dosyalarını yazar."""
    print(f"\nHedef: {target_url}")
    first = await scrape_page(page, target_url, 1)
    if not first:
        return []
    total_pages = await get_total_pages(page)
    print(f"Toplam {total_pages} sayfa taranacak.")

    all_listings = list(first)
    seen = {i["id"] for i in all_listings}
    for n in range(2, min(total_pages, MAX_PAGES) + 1):
        await random_sleep(2000, 4000)
        got = None
        for attempt in range(3):
            try:
                got = await scrape_page(page, _page_url(target_url, n), n)
                break
            except Exception as e:
                print(f"  Hata (deneme {attempt + 1}/3): {e}")
                await random_sleep(3000, 5000)
        if not got:
            print(f"  Sayfa {n} boş/başarısız, tarama durduruldu.")
            break
        new = [i for i in got if i["id"] not in seen]
        if not new:
            break
        seen.update(i["id"] for i in new)
        all_listings.extend(new)

    if rooms:
        want = _norm_room(rooms)
        before = len(all_listings)
        all_listings = [i for i in all_listings if _norm_room(i["room"]) == want]
        print(f"\nOda filtresi ({rooms}): {before} -> {len(all_listings)} ilan")

    with open(OUTPUT_DIR / f"{prefix}.json", "w", encoding="utf-8") as f:
        json.dump(all_listings, f, ensure_ascii=False, indent=2)
    with open(OUTPUT_DIR / f"{prefix}.txt", "w", encoding="utf-8") as f:
        for i in all_listings:
            f.write(" | ".join([
                f"Başlık: {i['title']}", f"Oda: {i['room']}", f"m²: {i['gross_m2']}",
                f"Fiyat: {i['price']}", f"Konum: {i['location']}", f"Link: {i['url']}"]) + "\n")
    print(f"Kaydedildi: {OUTPUT_DIR / (prefix + '.json')}")
    return all_listings
