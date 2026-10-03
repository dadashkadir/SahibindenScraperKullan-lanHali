"""Ortak yardımcılar."""
import asyncio
import random

ROW_SELECTOR = "tr.searchResultsItem[data-id]"


async def random_sleep(min_ms=800, max_ms=2000):
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def goto(page, url, timeout=60000):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    except Exception as e:
        print(f"  Sayfa zaman aşımı, tekrar deneniyor: {e}")
        await page.goto(url, wait_until="load", timeout=timeout)


async def wait_until_ready(page, wait_seconds=180, need_rows=True):
    """Cloudflare / giriş ekranı varsa kullanıcı geçene kadar bekler.
    need_rows=True: ilan satırı görünene kadar; False: sadece Cloudflare geçene kadar.
    True dönerse sayfa hazırdır."""
    warned = False
    for i in range(wait_seconds):
        try:
            title = await page.title()
        except Exception:
            title = ""
        blocked = any(k in title for k in ("Just a moment", "Bir dakika", "Checking", "Giriş"))
        rows = await page.query_selector_all(ROW_SELECTOR) if need_rows else []
        if need_rows and rows:
            return True
        if not need_rows and title and not blocked:
            return True
        # ilan yok sayfası (0 sonuç) da geçerli sayılır
        if need_rows and not blocked and title:
            body = ""
            try:
                body = (await page.inner_text("body"))[:5000].lower()
            except Exception:
                pass
            if "ilan bulunamadı" in body or "sonuç bulunamadı" in body or "aradığınız kriterlere uygun ilan" in body:
                return True
        if i >= 5 and not warned:
            print("\n  >>> Açılan tarayıcı penceresinde 'Ben robot değilim' kutusunu işaretleyin")
            print("  >>> veya sahibinden.com'a giriş yapın. Sayfa hazır olunca program otomatik devam eder.")
            warned = True
        await asyncio.sleep(1)
    return False
