"""İlk liste sayfasından toplam sayfa sayısını bulur."""
import math
import re

from ..config import ITEMS_PER_PAGE, MAX_PAGES


async def get_total_pages(page) -> int:
    try:
        text = await page.inner_text("body")
        m = re.search(r"([\d\.]+)\s*ilan", text, re.IGNORECASE)
        if m:
            total = int(m.group(1).replace(".", ""))
            pages = max(1, math.ceil(total / ITEMS_PER_PAGE))
            print(f"  Toplam ilan: {total} -> {pages} sayfa")
            return min(pages, MAX_PAGES)
    except Exception:
        pass
    try:
        hrefs = await page.eval_on_selector_all(
            "a[href*='pagingOffset']", "els => els.map(e => e.getAttribute('href'))")
        best = 1
        for h in hrefs:
            m = re.search(r"pagingOffset=(\d+)", h or "")
            if m:
                best = max(best, int(m.group(1)) // ITEMS_PER_PAGE + 1)
        return min(best, MAX_PAGES)
    except Exception:
        return 1
