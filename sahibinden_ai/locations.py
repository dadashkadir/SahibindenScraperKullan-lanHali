"""Plaka kodları, slug üretimi ve sahibinden sayfasından ilçe/mahalle keşfi."""
import re

PLAKA = {
    1: "Adana", 2: "Adıyaman", 3: "Afyonkarahisar", 4: "Ağrı", 5: "Amasya", 6: "Ankara",
    7: "Antalya", 8: "Artvin", 9: "Aydın", 10: "Balıkesir", 11: "Bilecik", 12: "Bingöl",
    13: "Bitlis", 14: "Bolu", 15: "Burdur", 16: "Bursa", 17: "Çanakkale", 18: "Çankırı",
    19: "Çorum", 20: "Denizli", 21: "Diyarbakır", 22: "Edirne", 23: "Elazığ", 24: "Erzincan",
    25: "Erzurum", 26: "Eskişehir", 27: "Gaziantep", 28: "Giresun", 29: "Gümüşhane",
    30: "Hakkari", 31: "Hatay", 32: "Isparta", 33: "Mersin", 34: "İstanbul", 35: "İzmir",
    36: "Kars", 37: "Kastamonu", 38: "Kayseri", 39: "Kırklareli", 40: "Kırşehir",
    41: "Kocaeli", 42: "Konya", 43: "Kütahya", 44: "Malatya", 45: "Manisa",
    46: "Kahramanmaraş", 47: "Mardin", 48: "Muğla", 49: "Muş", 50: "Nevşehir", 51: "Niğde",
    52: "Ordu", 53: "Rize", 54: "Sakarya", 55: "Samsun", 56: "Siirt", 57: "Sinop",
    58: "Sivas", 59: "Tekirdağ", 60: "Tokat", 61: "Trabzon", 62: "Tunceli", 63: "Şanlıurfa",
    64: "Uşak", 65: "Van", 66: "Yozgat", 67: "Zonguldak", 68: "Aksaray", 69: "Bayburt",
    70: "Karaman", 71: "Kırıkkale", 72: "Batman", 73: "Şırnak", 74: "Bartın", 75: "Ardahan",
    76: "Iğdır", 77: "Yalova", 78: "Karabük", 79: "Kilis", 80: "Osmaniye", 81: "Düzce",
}

_TR_MAP = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "Ç": "c", "Ğ": "g", "İ": "i", "I": "i", "Ö": "o", "Ş": "s", "Ü": "u",
})


def slugify(text: str) -> str:
    """Türkçe karakterleri çevirir. ÖNEMLİ: harita lower()'dan ÖNCE uygulanmalı,
    yoksa 'İ'.lower() birleşik nokta üretir ve 'İstanbul' -> 'i-stanbul' olur."""
    text = text.translate(_TR_MAP).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def il_from_plaka(code: int) -> str:
    return PLAKA[code]


_JS_LINKS = """
(prefix) => {
    const out = {};
    document.querySelectorAll('a[href]').forEach(a => {
        let u;
        try { u = new URL(a.href, location.origin); } catch (e) { return; }
        const path = u.pathname.replace(/\\/+$/, '');
        const parts = path.split('/').filter(Boolean);
        if (parts.length !== 2) return;
        if (!parts[1].startsWith(prefix)) return;
        let text = (a.innerText || a.textContent || '').replace(/\\s+/g, ' ').trim();
        text = text.replace(/\\(\\s*[\\d\\.\\,]+\\s*\\)\\s*$/, '').trim();   // sondaki "(1.234)" sayacı
        if (!text) return;
        if (!out[path]) out[path] = text;
    });
    return Object.entries(out).map(([path, name]) => ({path, name}));
}
"""


async def discover_links(page, path_prefix: str):
    """Açık sayfadaki, /kategori/<path_prefix>... biçimindeki adres bağlantılarını toplar.
    Dönen: [{'path': '/satilik-daire/manisa-yunusemre', 'name': 'Yunusemre'}, ...]"""
    items = await page.evaluate(_JS_LINKS, path_prefix)
    items = [i for i in items if i["path"].split("/")[-1] != path_prefix.rstrip("-")]
    # Bir öğenin slug'ı başka bir öğenin slug'ı + "-" ile başlıyorsa alt seviyedir (mahalle) -> ele
    slugs = [i["path"].split("/")[-1] for i in items]
    items = [i for i, sl in zip(items, slugs)
             if not any(sl != o and sl.startswith(o + "-") for o in slugs)]
    items.sort(key=lambda i: i["name"].lower().translate(_TR_MAP))
    return items


_JS_SUBMODELS = """
(prefix) => {
    const out = {};
    document.querySelectorAll('a[href]').forEach(a => {
        let u;
        try { u = new URL(a.href, location.origin); } catch (e) { return; }
        const path = u.pathname.replace(/^\\/+|\\/+$/g, '');
        const parts = path.split('/').filter(Boolean);
        // Alt model sayfaları tek segmentli oluyor: /ford-focus-1.5-tdci-titanium
        if (parts.length !== 1) return;
        if (!parts[0].startsWith(prefix)) return;
        let text = (a.innerText || a.textContent || '').replace(/\\s+/g, ' ').trim();
        text = text.replace(/\\(\\s*[\\d\\.,]+\\s*\\)\\s*$/, '').trim(); // sondaki sayaç
        if (!text) return;
        if (!out[path]) out[path] = text;
    });
    return Object.entries(out).map(([path, name]) => ({path, name}));
}
"""

async def discover_submodels(page, path_prefix: str):
    """Model sayfasında listelenen alt model (motor/donanim) linklerini toplar.
    Dönen: [{'path': '/ford-focus-1.5-tdci-titanium', 'name': '1.5 TDCi Titanium'}, ...]"""
    items = await page.evaluate(_JS_SUBMODELS, path_prefix)
    # prefix'in kendisini (model ana sayfası) listeden çıkar
    items = [i for i in items if i["path"] != path_prefix.rstrip("-")]
    items.sort(key=lambda i: i["name"].lower().translate(_TR_MAP))
    return items


_JS_CHILDREN = """
(prefix, depth) => {
    const out = {};
    document.querySelectorAll('a[href]').forEach(a => {
        let u;
        try { u = new URL(a.href, location.origin); } catch (e) { return; }
        const path = u.pathname.replace(/^\\/+|\\/+$/g, '');
        const parts = path.split('/').filter(Boolean);
        if (parts.length !== depth) return;
        const joined = parts.join('/');
        if (!joined.startsWith(prefix)) return;
        let text = (a.innerText || a.textContent || '').replace(/\\s+/g, ' ').trim();
        text = text.replace(/\\(\\s*[\\d\\.,]+\\s*\\)\\s*$/, '').trim(); // sondaki sayaç
        if (!text) return;
        if (!out[path]) out[path] = text;
    });
    return Object.entries(out).map(([path, name]) => ({path, name}));
}
"""

async def discover_children(page, path_prefix: str, depth: int):
    """
    Belirli bir derinlikte (segment sayısı) ve verilen prefix ile başlayan
    alt kategori/linkleri döner.
    Örnek:
        depth=3  -> /kategori/marka/model
        depth=4  -> /kategori/marka/model/motor
        depth=5  -> /kategori/marka/model/motor/kasa
    """
    items = await page.evaluate(_JS_CHILDREN, path_prefix, depth)
    # kendisini (prefix'e tam eşleşen) listeden çıkar
    items = [i for i in items if i["path"] != path_prefix.rstrip("/")]
    items.sort(key=lambda i: i["name"].lower().translate(_TR_MAP))
    return items
