"""Kullanıcıdan parametre alma: plaka -> ilçe -> mahalle -> işlem tipi -> emlak tipi -> oda -> metrekare -> bina yaşı -> özellikler."""
from dataclasses import dataclass, field
from typing import Optional

from .config import BASE_URL, ESTATE_TYPES, ROOM_TYPES, VEHICLE_CATEGORIES_SATILIK, VEHICLE_CATEGORIES_KIRALIK, VEHICLE_FILTER_MAP
from .locations import PLAKA, slugify, discover_links, discover_submodels, discover_children
from .scraper.utils import goto, wait_until_ready

# DISCOVERY_CATEGORY artık işlem tipine (satilik/kiralik) göre dinamik oluşturuluyor.


@dataclass
class Params:
    plaka: int
    il: str
    ilce: str = ""
    mahalle: str = ""
    transaction: str = "satilik"
    market_type: str = "emlak"          # "emlak" veya "vasita"
    estate: str = "Daire"               # emlak tipi
    vehicle_category: str = ""          # vasita slug (örn. "otomobil")
    vehicle_brand: str = ""             # marka (örn. "Audi")
    vehicle_model: str = ""             # model (örn. "A4")
    vehicle_submodel: str = ""          # alt model / donanım (örn. "1.5 TDCi Titanium")
    vehicle_engine: str = ""            # motor (örn. "1.5 TDCi")
    vehicle_body_type: str = ""         # kasa tipi (örn. "Sedan", "Hatchback")
    vehicle_transmission: str = ""      # vites: "otomatik" / "manuel" / ""
    vehicle_damage: bool = False        # hasarlı mı?
    rooms: str = ""
    min_m2: int = 0
    max_m2: int = 0
    building_age: int = -1
    site_icinde: bool = False
    acik_mutfak: bool = False
    dogalgaz: bool = False
    # Vasıta filtreleri
    vehicle_year_min: int = 0
    vehicle_year_max: int = 0
    vehicle_km_min: int = 0
    vehicle_km_max: int = 0
    vehicle_price_min: int = 0
    vehicle_price_max: int = 0
    vehicle_fuel: list = field(default_factory=list)   # a812 değerleri
    vehicle_gear: list = field(default_factory=list)
    vehicle_body: list = field(default_factory=list)
    vehicle_color: list = field(default_factory=list)
    vehicle_transmission_list: list = field(default_factory=list)  # vites listesi (eski alan)
    vehicle_degisen: bool = False                         # değişen parça var mı?
    vehicle_agir_hasar: bool = False                      # ağır hasar var mı?
    location_path: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def title(self):
        parts = [self.il, self.ilce or "Tüm ilçeler", self.mahalle or "Tüm mahalleler"]
        return " / ".join(parts)


def ask_plaka() -> int:
    while True:
        s = input("\nİl plaka kodu (örn. 45 = Manisa): ").strip()
        if s.isdigit() and int(s) in PLAKA:
            code = int(s)
            print(f"  -> {PLAKA[code]}")
            return code
        print("  Geçersiz plaka kodu (1-81 arası girin).")


def pick_from_list(title: str, items: list, allow_all_label: str):
    print(f"\n{title}")
    print(f"   0) {allow_all_label}")
    for i, it in enumerate(items, 1):
        print(f"  {i:>2}) {it['name']}")
    while True:
        s = input("Numara seçin: ").strip()
        if s.isdigit() and 0 <= int(s) <= len(items):
            n = int(s)
            return None if n == 0 else items[n - 1]
        print("  Geçersiz numara.")


def ask_manual(label: str) -> str:
    return input(f"{label} adını yazın (boş = hepsi): ").strip()


def pick_transaction() -> str:
    print("\nİşlem tipi:")
    opts = ["Satılık", "Kiralık"]
    for i, o in enumerate(opts, 1):
        print(f"  {i}) {o}")
    while True:
        s = input("Numara seçin: ").strip()
        if s.isdigit() and 1 <= int(s) <= len(opts):
            return "satilik" if int(s) == 1 else "kiralik"
        print("  Geçersiz numara.")


def pick_market_type() -> str:
    print("\nPazar tipi:")
    opts = ["Emlak", "Vasıta"]
    for i, o in enumerate(opts, 1):
        print(f"  {i}) {o}")
    while True:
        s = input("Numara seçin: ").strip()
        if s.isdigit() and 1 <= int(s) <= len(opts):
            return "emlak" if int(s) == 1 else "vasita"
        print("  Geçersiz numara.")


def pick_vehicle_category(transaction: str) -> str:
    if transaction == "kiralik":
        cat_map = VEHICLE_CATEGORIES_KIRALIK
    else:
        cat_map = VEHICLE_CATEGORIES_SATILIK
    names = list(cat_map.keys())
    print("\nVasıta kategorisi:")
    for i, n in enumerate(names, 1):
        print(f"  {i}) {n}")
    while True:
        s = input("Numara seçin: ").strip()
        if s.isdigit() and 1 <= int(s) <= len(names):
            return cat_map[names[int(s) - 1]]
        print("  Geçersiz numara.")


def ask_int(label: str, default: int = 0) -> int:
    s = input(f"{label} (varsayılan {default}): ").strip()
    return int(s) if s.isdigit() else default


def ask_bool(label: str) -> bool:
    while True:
        s = input(f"{label} (e/h): ").strip().lower()
        if s in ("e", "evet", "y", "yes"):
            return True
        if s in ("h", "hayir", "n", "no"):
            return False
        print("  'e' ya da 'h' giriniz.")


def pick_estate() -> str:
    names = list(ESTATE_TYPES)
    print("\nEmlak tipi:")
    for i, n in enumerate(names, 1):
        print(f"  {i}) {n}")
    while True:
        s = input("Numara seçin: ").strip()
        if s.isdigit() and 1 <= int(s) <= len(names):
            return names[int(s) - 1]
        print("  Geçersiz numara.")


def ask_rooms() -> str:
    while True:
        s = input("\nOda sayısı (örn. 2+1, 3+1 — boş bırakırsanız hepsi): ").strip().replace(" ", "")
        if not s or ("+" in s and all(p.isdigit() for p in s.split("+") if p) and len(s.split("+")) == 2):
            return s
        print("  Biçim örn. 3+1 olmalı.")


def ask_int(label: str, default: int = 0) -> int:
    while True:
        s = input(f"{label} (boş = {default}): ").strip()
        if not s:
            return default
        if s.isdigit():
            return int(s)
        print("  Sayı giriniz.")


def ask_bool(label: str) -> bool:
    while True:
        s = input(f"{label} (e/h): ").strip().lower()
        if s in ("e", "evet", "y", "yes"):
            return True
        if s in ("h", "hayir", "n", "no"):
            return False
        print("  'e' ya da 'h' giriniz.")


async def collect_params(page) -> Params:
    """Etkileşimli akış. Adres listelerini sahibinden.com'dan okur."""
    # ---- pazar tipi (emlak / vasita) ----
    market_type = pick_market_type()

    if market_type == "vasita":
        # Vasıta için işlem tipi varsayılan satılık, il/ilçe/mahalle sormuyoruz
        transaction = "satilik"
    else:
        # ---- işlem tipi (sadece emlak için) ----
        transaction = pick_transaction()

    if market_type == "vasita":
        # Vasıta için il/ilçe/mahalle sormuyoruz
        code = 0  # dummy plaka
        il = "Türkiye"
        il_slug = "turkiye"
        p = Params(plaka=code, il=il, location_path="")
        p.market_type = market_type
        p.transaction = transaction

        # ---- vasita kategori ----
        VASITA_CATEGORIES = [
            "Otomobil",
            "Arazi, SUV & Pickup",
            "Elektrikli Araçlar",
            "Motosiklet",
            "Minivan & Panelvan",
            "Ticari Araçlar",
            "Kiralık Araçlar",
            "Deniz Araçları",
            "Hasarlı Araçlar",
            "Karavan",
            "Klasik Araçlar",
            "Hava Araçları",
            "ATV",
            "UTV",
            "Engelli Plakalı Araçlar",
        ]
        print("\nVasıta kategorisi seçin:")
        sec = pick_from_list("Kategori:", [{"name": c, "path": slugify(c)} for c in VASITA_CATEGORIES], "Hepsi")
        p.vehicle_category = sec["name"] if sec else ""

        # ---- marka (sahibinden'den çek) ----
        cat_slug = slugify(p.vehicle_category)
        print(f"\n{cat_slug} markaları sahibinden.com'dan okunuyor...")
        await goto(page, f"{BASE_URL}/{cat_slug}")
        await wait_until_ready(page, wait_seconds=180)
        brands = await discover_links(page, cat_slug + "/")
        if brands:
            sec_brand = pick_from_list(f"{p.vehicle_category} markaları:", brands, "Elle gir")
            if sec_brand:
                p.vehicle_brand = sec_brand["name"]
            else:
                p.vehicle_brand = ask_manual("Marka").strip()
        else:
            print("  Marka listesi okunamadı. Elle girin.")
            p.vehicle_brand = ask_manual("Marka").strip()

        # ---- model (sahibinden'den çek) ----
        if p.vehicle_brand:
            brand_slug = slugify(p.vehicle_brand)
            print(f"\n{p.vehicle_brand} modelleri sahibinden.com'dan okunuyor...")
            await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}")
            await wait_until_ready(page, wait_seconds=180)
            models = await discover_links(page, f"{cat_slug}/{brand_slug}/")
            if models:
                sec_model = pick_from_list(f"{p.vehicle_brand} modelleri:", models, "Elle gir")
                if sec_model:
                    p.vehicle_model = sec_model["name"]
                    model_path = sec_model["path"]          # e.g. "/otomobil/ford-focus"
                    model_slug = model_path.split("/")[-1]  # "ford-focus"
                    # ---- motor (engine) seçenekleri ----
                    engine_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/"
                    print(f"\n{p.vehicle_model} motor seçenekleri okunuyor...")
                    await goto(page, f"{BASE_URL}{model_path}")
                    await wait_until_ready(page, wait_seconds=180)
                    engines = await discover_children(page, engine_prefix, depth=4, container_sel=".jspPane ul")
                    engine_slug = ""
                    if engines:
                        sec_engine = pick_from_list(f"{p.vehicle_model} motorları:", engines, "Hepsi / Elle gir")
                        if sec_engine:
                            p.vehicle_engine = sec_engine["name"]
                            engine_path = sec_engine["path"]          # e.g. "/otomobil/ford/focus/1.5-tdci"
                            engine_slug = engine_path.split("/")[-1]  # "1.5-tdci"
                        else:
                            p.vehicle_engine = ask_manual("Motor").strip()
                            engine_slug = slugify(p.vehicle_engine) if p.vehicle_engine else ""
                    else:
                        print("  Motor listesi okunamadı. Elle girin.")
                        p.vehicle_engine = ask_manual("Motor").strip()
                        engine_slug = slugify(p.vehicle_engine) if p.vehicle_engine else ""

                    # ---- kasa tipi (body type) seçenekleri ----
                    body_slug = ""
                    if engine_slug:
                        body_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/"
                        print(f"\n{p.vehicle_model} {p.vehicle_engine} kasa tipleri okunuyor...")
                        await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}")
                        await wait_until_ready(page, wait_seconds=180)
                        bodies = await discover_children(page, body_prefix, depth=5, container_sel=".jspPane ul")
                        if bodies:
                            sec_body = pick_from_list(f"{p.vehicle_model} {p.vehicle_engine} kasa tipleri:", bodies, "Hepsi / Elle gir")
                            if sec_body:
                                p.vehicle_body_type = sec_body["name"]
                                body_path = sec_body["path"]
                                body_slug = body_path.split("/")[-1]
                            else:
                                p.vehicle_body_type = ask_manual("Kasa tipi").strip()
                                body_slug = slugify(p.vehicle_body_type) if p.vehicle_body_type else ""
                        else:
                            print("  Kasa tipi listesi okunamadı. Elle girin.")
                            p.vehicle_body_type = ask_manual("Kasa tipi").strip()
                            body_slug = slugify(p.vehicle_body_type) if p.vehicle_body_type else ""

                    # ---- alt model / donanım (trim) ----
                    # Alt model sayfası genellikle motor/kasa sonrası gelir; varsa çek
                    trim_slug = ""
                    if body_slug:
                        trim_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/{body_slug}/"
                        print(f"\n{p.vehicle_model} {p.vehicle_engine} {p.vehicle_body_type} donanım (trim) seçenekleri okunuyor...")
                        await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/{body_slug}")
                        await wait_until_ready(page, wait_seconds=180)
                        trims = await discover_children(page, trim_prefix, depth=6, container_sel=".jspPane ul")
                        if trims:
                            sec_trim = pick_from_list(f"{p.vehicle_model} {p.vehicle_engine} {p.vehicle_body_type} donanımlar:", trims, "Hepsi / Elle gir")
                            if sec_trim:
                                p.vehicle_submodel = sec_trim["name"]
                                trim_path = sec_trim["path"]
                                trim_slug = trim_path.split("/")[-1]
                            else:
                                p.vehicle_submodel = ask_manual("Donanım (trim)").strip()
                                trim_slug = slugify(p.vehicle_submodel) if p.vehicle_submodel else ""
                        else:
                            print("  Donanım listesi okunamadı. Elle girin.")
                            p.vehicle_submodel = ask_manual("Donanım (trim)").strip()
                            trim_slug = slugify(p.vehicle_submodel) if p.vehicle_submodel else ""

                    # ---- vites (transmission) ----
                    trans_options = [("Otomatik", "otomatik"), ("Manuel", "manuel")]
                    print("\nVites türü seçin:")
                    trans_sec = pick_from_list("Vites:", [{"name": n, "path": v} for n, v in trans_options], "Hepsi")
                    if trans_sec:
                        p.vehicle_transmission = trans_sec["path"]
                    else:
                        p.vehicle_transmission = ""
                else:
                    p.vehicle_model = ask_manual("Model").strip()
                    # proceed to motor/kasa/trim even for manual model
                    model_slug = slugify(p.vehicle_model)
                    # ---- motor (engine) seçenekleri ----
                    engine_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/"
                    print(f"\n{p.vehicle_model} motor seçenekleri okunuyor...")
                    await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}")
                    await wait_until_ready(page, wait_seconds=180)
                    engines = await discover_children(page, engine_prefix, depth=4, container_sel=".jspPane ul")
                    engine_slug = ""
                    if engines:
                        sec_engine = pick_from_list(f"{p.vehicle_model} motorları:", engines, "Hepsi / Elle gir")
                        if sec_engine:
                            p.vehicle_engine = sec_engine["name"]
                            engine_path = sec_engine["path"]
                            engine_slug = engine_path.split("/")[-1]
                        else:
                            p.vehicle_engine = ask_manual("Motor").strip()
                            engine_slug = slugify(p.vehicle_engine) if p.vehicle_engine else ""
                    else:
                        print("  Motor listesi okunamadı. Elle girin.")
                        p.vehicle_engine = ask_manual("Motor").strip()
                        engine_slug = slugify(p.vehicle_engine) if p.vehicle_engine else ""

                    # ---- kasa tipi (body type) seçenekleri ----
                    body_slug = ""
                    if engine_slug:
                        body_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/"
                        print(f"\n{p.vehicle_model} {p.vehicle_engine} kasa tipleri okunuyor...")
                        await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}")
                        await wait_until_ready(page, wait_seconds=180)
                        bodies = await discover_children(page, body_prefix, depth=5, container_sel=".jspPane ul")
                        if bodies:
                            sec_body = pick_from_list(f"{p.vehicle_model} {p.vehicle_engine} kasa tipleri:", bodies, "Hepsi / Elle gir")
                            if sec_body:
                                p.vehicle_body_type = sec_body["name"]
                                body_path = sec_body["path"]
                                body_slug = body_path.split("/")[-1]
                            else:
                                p.vehicle_body_type = ask_manual("Kasa tipi").strip()
                                body_slug = slugify(p.vehicle_body_type) if p.vehicle_body_type else ""
                        else:
                            print("  Kasa tipi listesi okunamadı. Elle girin.")
                            p.vehicle_body_type = ask_manual("Kasa tipi").strip()
                            body_slug = slugify(p.vehicle_body_type) if p.vehicle_body_type else ""

                    # ---- alt model / donanım (trim) ----
                    trim_slug = ""
                    if body_slug:
                        trim_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/{body_slug}/"
                        print(f"\n{p.vehicle_model} {p.vehicle_engine} {p.vehicle_body_type} donanım (trim) seçenekleri okunuyor...")
                        await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/{body_slug}")
                        await wait_until_ready(page, wait_seconds=180)
                        trims = await discover_children(page, trim_prefix, depth=6, container_sel=".jspPane ul")
                        if trims:
                            sec_trim = pick_from_list(f"{p.vehicle_model} {p.vehicle_engine} {p.vehicle_body_type} donanımlar:", trims, "Hepsi / Elle gir")
                            if sec_trim:
                                p.vehicle_submodel = sec_trim["name"]
                                trim_path = sec_trim["path"]
                                trim_slug = trim_path.split("/")[-1]
                            else:
                                p.vehicle_submodel = ask_manual("Donanım (trim)").strip()
                                trim_slug = slugify(p.vehicle_submodel) if p.vehicle_submodel else ""
                        else:
                            print("  Donanım listesi okunamadı. Elle girin.")
                            p.vehicle_submodel = ask_manual("Donanım (trim)").strip()
                            trim_slug = slugify(p.vehicle_submodel) if p.vehicle_submodel else ""

                    # ---- vites (transmission) ----
                    trans_options = [("Otomatik", "otomatik"), ("Manuel", "manuel")]
                    print("\nVites türü seçin:")
                    trans_sec = pick_from_list("Vites:", [{"name": n, "path": v} for n, v in trans_options], "Hepsi")
                    if trans_sec:
                        p.vehicle_transmission = trans_sec["path"]
                    else:
                        p.vehicle_transmission = ""
            else:
                print("  Model listesi okunamadı. Elle girin.")
                p.vehicle_model = ask_manual("Model").strip()
                # proceed to motor/kasa/trim even for manual model
                model_slug = slugify(p.vehicle_model)
                # ---- motor (engine) seçenekleri ----
                engine_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/"
                print(f"\n{p.vehicle_model} motor seçenekleri okunuyor...")
                await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}")
                await wait_until_ready(page, wait_seconds=180)
                engines = await discover_children(page, engine_prefix, depth=4, container_sel=".jspPane ul")
                engine_slug = ""
                if engines:
                    sec_engine = pick_from_list(f"{p.vehicle_model} motorları:", engines, "Hepsi / Elle gir")
                    if sec_engine:
                        p.vehicle_engine = sec_engine["name"]
                        engine_path = sec_engine["path"]
                        engine_slug = engine_path.split("/")[-1]
                    else:
                        p.vehicle_engine = ask_manual("Motor").strip()
                        engine_slug = slugify(p.vehicle_engine) if p.vehicle_engine else ""
                else:
                    print("  Motor listesi okunamadı. Elle girin.")
                    p.vehicle_engine = ask_manual("Motor").strip()
                    engine_slug = slugify(p.vehicle_engine) if p.vehicle_engine else ""

                # ---- kasa tipi (body type) seçenekleri ----
                body_slug = ""
                if engine_slug:
                    body_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/"
                    print(f"\n{p.vehicle_model} {p.vehicle_engine} kasa tipleri okunuyor...")
                    await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}")
                    await wait_until_ready(page, wait_seconds=180)
                    bodies = await discover_children(page, body_prefix, depth=5, container_sel=".jspPane ul")
                    if bodies:
                        sec_body = pick_from_list(f"{p.vehicle_model} {p.vehicle_engine} kasa tipleri:", bodies, "Hepsi / Elle gir")
                        if sec_body:
                            p.vehicle_body_type = sec_body["name"]
                            body_path = sec_body["path"]
                            body_slug = body_path.split("/")[-1]
                        else:
                            p.vehicle_body_type = ask_manual("Kasa tipi").strip()
                            body_slug = slugify(p.vehicle_body_type) if p.vehicle_body_type else ""
                    else:
                        print("  Kasa tipi listesi okunamadı. Elle girin.")
                        p.vehicle_body_type = ask_manual("Kasa tipi").strip()
                        body_slug = slugify(p.vehicle_body_type) if p.vehicle_body_type else ""

                # ---- alt model / donanım (trim) ----
                trim_slug = ""
                if body_slug:
                    trim_prefix = f"{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/{body_slug}/"
                    print(f"\n{p.vehicle_model} {p.vehicle_engine} {p.vehicle_body_type} donanım (trim) seçenekleri okunuyor...")
                    await goto(page, f"{BASE_URL}/{cat_slug}/{brand_slug}/{model_slug}/{engine_slug}/{body_slug}")
                    await wait_until_ready(page, wait_seconds=180)
                    trims = await discover_children(page, trim_prefix, depth=6, container_sel=".jspPane ul")
                    if trims:
                        sec_trim = pick_from_list(f"{p.vehicle_model} {p.vehicle_engine} {p.vehicle_body_type} donanımlar:", trims, "Hepsi / Elle gir")
                        if sec_trim:
                            p.vehicle_submodel = sec_trim["name"]
                            trim_path = sec_trim["path"]
                            trim_slug = trim_path.split("/")[-1]
                        else:
                            p.vehicle_submodel = ask_manual("Donanım (trim)").strip()
                            trim_slug = slugify(p.vehicle_submodel) if p.vehicle_submodel else ""
                    else:
                        print("  Donanım listesi okunamadı. Elle girin.")
                        p.vehicle_submodel = ask_manual("Donanım (trim)").strip()
                        trim_slug = slugify(p.vehicle_submodel) if p.vehicle_submodel else ""

                # ---- vites (transmission) ----
                trans_options = [("Otomatik", "otomatik"), ("Manuel", "manuel")]
                print("\nVites türü seçin:")
                trans_sec = pick_from_list("Vites:", [{"name": n, "path": v} for n, v in trans_options], "Hepsi")
                if trans_sec:
                    p.vehicle_transmission = trans_sec["path"]
                else:
                    p.vehicle_transmission = ""
        else:
            p.vehicle_model = ask_manual("Model").strip()
            p.vehicle_submodel = ""
            p.vehicle_transmission = ""

        # ---- yıl, km, fiyat aralıkları ----
        p.vehicle_year_min = ask_int("Minimum model yılı", 0)
        p.vehicle_year_max = ask_int("Maksimum model yılı", 0)
        p.vehicle_km_min = ask_int("Minimum kilometre", 0)
        p.vehicle_km_max = ask_int("Maksimum kilometre", 0)
        p.vehicle_price_min = ask_int("Minimum fiyat (TL)", 0)
        p.vehicle_price_max = ask_int("Maksimum fiyat (TL)", 0)

        # ---- vites ----
        trans_options = ["Düz", "Otomatik"]
        print("\nVites türü seçin:")
        trans_sec = pick_from_list("Vites:", [{"name": t, "path": t.lower()} for t in trans_options], "Hepsi")
        if trans_sec:
            p.vehicle_transmission = [trans_sec["name"]]

        # ---- değişen parça ----
        p.vehicle_degisen = ask_bool("Değişen parça var mı?")

        # ---- ağır hasar ----
        p.vehicle_agir_hasar = ask_bool("Ağır hasar var mı?")

        # ---- hasarlı araçlar dahil mi? ----
        p.vehicle_damage = ask_bool("Hasarlı araçlar dahil mi?")

        # emlak alanları sıfırla
        p.estate = ""
        p.rooms = ""
        p.min_m2 = p.max_m2 = 0
        p.building_age = -1
        p.site_icinde = p.acik_mutfak = p.dogalgaz = False
    else:
        # ---- emlak için il/ilçe/mahalle ----
        code = ask_plaka()
        il = PLAKA[code]
        il_slug = slugify(il)
        p = Params(plaka=code, il=il, location_path=il_slug)
        p.market_type = market_type
        p.transaction = transaction

        # discovery_cat for location lists (use a generic category that works for both)
        discovery_cat = f"{p.transaction}-daire"

        # ---- ilçeler ----
        print(f"\n{il} ilçeleri sahibinden.com'dan okunuyor...")
        await goto(page, f"{BASE_URL}/{discovery_cat}/{il_slug}")
        await wait_until_ready(page, wait_seconds=180)
        ilceler = await discover_links(page, il_slug + "-")
        if ilceler:
            sec = pick_from_list(f"{il} ilçeleri:", ilceler, "Tüm ilçeler")
            if sec:
                p.ilce = sec["name"]
                p.location_path = sec["path"].split("/")[-1]
        else:
            print("  İlçe listesi sayfadan okunamadı (debug_ilce.html kaydedildi). Elle girin.")
            await _dump(page, "debug_ilce.html")
            name = ask_manual("İlçe")
            if name:
                p.ilce = name
                p.location_path = f"{il_slug}-{slugify(name)}"

        # ---- mahalleler ----
        if p.ilce:
            print(f"\n{p.ilce} mahalleleri okunuyor...")
            await goto(page, f"{BASE_URL}/{discovery_cat}/{p.location_path}")
            await wait_until_ready(page, wait_seconds=180)
            mahalleler = await discover_links(page, p.location_path + "-")
            if mahalleler:
                sec = pick_from_list(f"{p.ilce} mahalleleri:", mahalleler, "Tüm mahalleler")
                if sec:
                    p.mahalle = sec["name"]
                    p.location_path = sec["path"].split("/")[-1]
            else:
                print("  Mahalle listesi sayfadan okunamadı (debug_mahalle.html kaydedildi). Elle girin.")
                await _dump(page, "debug_mahalle.html")
                name = ask_manual("Mahalle")
                if name:
                    p.mahalle = name
                    p.location_path = f"{p.location_path}-{slugify(name)}-mah"

        # ---- emlak tipi ----
        p.estate = pick_estate()
        need_room = p.estate in ROOM_TYPES
        need_area = need_room
        need_age = need_room
        need_feat = need_room

        if need_room:
            p.rooms = ask_rooms()
        else:
            p.rooms = ""

        if need_area:
            p.min_m2 = ask_int("Minimum metrekare")
            p.max_m2 = ask_int("Maksimum metrekare")
        else:
            p.min_m2 = p.max_m2 = 0

        if need_age:
            print("\nBina yaşı (0 = 0‑1 arası, 1 = 1‑2 arası, … 9 = 9‑10 arası, boş = hepsi):")
            s = input("Yaş aralığı (0‑9): ").strip()
            p.building_age = int(s) if s.isdigit() and 0 <= int(s) <= 9 else -1
        else:
            p.building_age = -1

        if need_feat:
            p.site_icinde = ask_bool("Site içinde mi?")
            p.acik_mutfak = ask_bool("Açık mutfak mı?")
            p.dogalgaz = ask_bool("Doğalgazlı mı?")
        else:
            p.site_icinde = p.acik_mutfak = p.dogalgaz = False

    return p


async def _dump(page, name):
    from .config import OUTPUT_DIR
    try:
        (OUTPUT_DIR / name).write_text(await page.content(), encoding="utf-8")
    except Exception:
        pass


FILTER_MAP = {
    "min_m2": "a107889_min",
    "max_m2": "a107889_max",
    "building_age_min": "a20_min",
    "building_age_max": "a20_max",
    "site_icinde": "1297863",
    "acik_mutfak": "1297864",
    "dogalgaz": "40606",
}


def build_list_url(p: Params) -> str:
    # Emlak mı Vasıta mı?
    if p.market_type == "vasita":
        # Vasıta kategori slug'ı transaction'a göre seç
        if p.transaction == "kiralik":
            cat_map = VEHICLE_CATEGORIES_KIRALIK
        else:
            cat_map = VEHICLE_CATEGORIES_SATILIK
        # vehicle_category zaten slug (örn. "otomobil")
        base_path = p.vehicle_category or next(iter(cat_map.values()))

        # marka/model/engine/body/trim ekle
        if p.vehicle_brand or p.vehicle_model:
            brand_slug = slugify(p.vehicle_brand) if p.vehicle_brand else ""
            model_slug = slugify(p.vehicle_model) if p.vehicle_model else ""
            engine_slug = slugify(p.vehicle_engine) if p.vehicle_engine else ""
            body_slug = slugify(p.vehicle_body_type) if p.vehicle_body_type else ""
            trim_slug = slugify(p.vehicle_submodel) if p.vehicle_submodel else ""

            # İlk segment: marka-model
            segment = ""
            if brand_slug and model_slug:
                segment = f"{brand_slug}-{model_slug}"
            elif brand_slug:
                segment = brand_slug
            elif model_slug:
                segment = model_slug

            if segment:
                base_path = f"{base_path}/{segment}"

            # motor
            if engine_slug:
                base_path = f"{base_path}/{engine_slug}"
            # kasa tipi
            if body_slug:
                base_path = f"{base_path}/{body_slug}"
            # donanım (trim)
            if trim_slug:
                base_path = f"{base_path}/{trim_slug}"

        # vites (transmission) varsa bir segment daha ekle
        if p.vehicle_transmission:
            base_path = f"{base_path}/{p.vehicle_transmission}"
        base_url = f"{BASE_URL}/{base_path}/{p.location_path}"
        qs = []
        if p.vehicle_year_min:
            qs.append(f"{VEHICLE_FILTER_MAP['year_min']}={p.vehicle_year_min}")
        if p.vehicle_year_max:
            qs.append(f"{VEHICLE_FILTER_MAP['year_max']}={p.vehicle_year_max}")
        if p.vehicle_km_min:
            qs.append(f"{VEHICLE_FILTER_MAP['km_min']}={p.vehicle_km_min}")
        if p.vehicle_km_max:
            qs.append(f"{VEHICLE_FILTER_MAP['km_max']}={p.vehicle_km_max}")
        if p.vehicle_price_min:
            qs.append(f"{VEHICLE_FILTER_MAP['price_min']}={p.vehicle_price_min}")
        if p.vehicle_price_max:
            qs.append(f"{VEHICLE_FILTER_MAP['price_max']}={p.vehicle_price_max}")
        # Çoklu seçimli a812 parametreleri
        for val in p.vehicle_fuel:
            qs.append(f"a812={val}")
        for val in p.vehicle_gear:
            qs.append(f"a812={val}")
        for val in p.vehicle_body:
            qs.append(f"a812={val}")
        for val in p.vehicle_color:
            qs.append(f"a812={val}")
        if qs:
            base_url += "?" + "&".join(qs)
        return base_url

    # ---- Emlak (eski mantık) ----
    estate_slug = ESTATE_TYPES[p.estate]
    base_category = estate_slug.split("-", 1)[1]
    base_path = f"{p.transaction}-{base_category}"
    base_url = f"{BASE_URL}/{base_path}/{p.location_path}"
    qs = []
    if p.min_m2:
        qs.append(f"{FILTER_MAP['min_m2']}={p.min_m2}")
    if p.max_m2:
        qs.append(f"{FILTER_MAP['max_m2']}={p.max_m2}")
    if p.building_age >= 0:
        age_val = (p.building_age + 1) * 1000 + p.building_age
        qs.append(f"{FILTER_MAP['building_age_min']}={age_val}")
        qs.append(f"{FILTER_MAP['building_age_max']}={age_val}")
    if p.site_icinde:
        qs.append(f"a812={FILTER_MAP['site_icinde']}")
    if p.acik_mutfak:
        qs.append(f"a812={FILTER_MAP['acik_mutfak']}")
    if p.dogalgaz:
        qs.append(f"a812={FILTER_MAP['dogalgaz']}")
    if qs:
        base_url += "?" + "&".join(qs)
    return base_url
