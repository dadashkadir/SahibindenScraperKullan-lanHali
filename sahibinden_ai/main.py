"""Giriş noktası: parametreleri sorar, ilanları tarar, PDF rapor üretir."""
import asyncio
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sahibinden_ai.config import OUTPUT_DIR
from sahibinden_ai.locations import slugify
from sahibinden_ai.browser import launch_chrome_with_debug, connect_playwright, close_playwright
from sahibinden_ai.cli import collect_params, build_list_url
from sahibinden_ai.orchestrator import run_scrape
from sahibinden_ai.analyzer.stats import run_analysis
from sahibinden_ai.storage.report_pdf import generate_pdf


async def async_main():
    print("=" * 56)
    print("  SAHIBINDEN TARAYICI + PDF RAPOR")
    print("=" * 56)

    launch_chrome_with_debug()
    pw, browser, context, page = await connect_playwright()
    try:
        await page.goto("https://www.sahibinden.com", wait_until="domcontentloaded", timeout=60000)
        params = await collect_params(page)
        url = build_list_url(params)

        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        if params.market_type == "vasita":
            parts = [
                slugify(params.il),
                slugify(params.ilce) if params.ilce else "",
                slugify(params.mahalle) if params.mahalle else "",
                slugify(params.vehicle_category) if params.vehicle_category else "",
                slugify(params.vehicle_brand) if params.vehicle_brand else "",
                slugify(params.vehicle_model) if params.vehicle_model else "",
                stamp,
            ]
        else:
            parts = [
                slugify(params.il),
                slugify(params.ilce) if params.ilce else "",
                slugify(params.mahalle) if params.mahalle else "",
                slugify(params.estate) if params.estate else "",
                slugify(params.rooms) if params.rooms else "",
                stamp,
            ]
        prefix = "_".join(filter(None, parts))

        listings = await run_scrape(page, url, prefix, rooms=params.rooms)
        if not listings:
            print("\nİlan bulunamadı; rapor üretilmedi.")
            return

        print("\nAnaliz ve PDF hazırlanıyor...")
        stats = run_analysis(listings)

        stats.update({
            "transaction": params.transaction,
            "market_type": params.market_type,
        })

        if params.market_type == "vasita":
            stats.update({
                "vehicle_category": params.vehicle_category,
                "vehicle_brand": params.vehicle_brand,
                "vehicle_model": params.vehicle_model,
                "vehicle_year_min": params.vehicle_year_min,
                "vehicle_year_max": params.vehicle_year_max,
                "vehicle_km_min": params.vehicle_km_min,
                "vehicle_km_max": params.vehicle_km_max,
                "vehicle_price_min": params.vehicle_price_min,
                "vehicle_price_max": params.vehicle_price_max,
                "vehicle_damage": params.vehicle_damage,
            })
            price_block = stats.get("price", {})
            min_price = price_block.get("min")
            mean_price = price_block.get("mean")
            median_price = price_block.get("median")
            if min_price:
                stats["galerici_price"] = round(min_price * 0.8)
            if mean_price:
                stats["resale_price"] = round(mean_price)
            elif median_price:
                stats["resale_price"] = round(median_price)

            from sahibinden_ai.analyzer.stats import _tl
            lines = []
            lines.append("🚗 **Vasıta Değerleme Özeti**")
            lines.append(f"Kategori: {params.vehicle_category}")
            if params.vehicle_brand or params.vehicle_model:
                lines.append(f"Marka/Model: {params.vehicle_brand} {params.vehicle_model}")
            if params.vehicle_year_min or params.vehicle_year_max:
                lines.append(f"Yıl aralığı: {params.vehicle_year_min or '–'} – {params.vehicle_year_max or '–'}")
            if params.vehicle_km_min or params.vehicle_km_max:
                lines.append(f"Km aralığı: {params.vehicle_km_min or '–'} – {params.vehicle_km_max or '–'} km")
            if params.vehicle_price_min or params.vehicle_price_max:
                lines.append(f"Fiyat aralığı: {params.vehicle_price_min or '–'} – {params.vehicle_price_max or '–'} TL")
            lines.append(f"Hasarlı dahil: {'Evet' if params.vehicle_damage else 'Hayır'}")
            if stats.get("galerici_price"):
                lines.append(f"\n🔧 **Galerici Alış Fiyatı (hızlı satış -%20)**: {_tl(stats['galerici_price'])} TL")
            if stats.get("resale_price"):
                lines.append(f"💰 **Önerilen Satış Fiyatı (aliciya)**: {_tl(stats['resale_price'])} TL")
            lines.append("\n*Bu değerler ilan fiyatlarının istatistiksel analizine dayanır; gerçek pazarlık sürecinde farklılık gösterebilir.*")
            stats["recommendation"] = "\n".join(lines)

            filter_parts = [
                f"İşlem: {'Kiralık' if params.transaction == 'kiralik' else 'Satılık'}",
                f"Kategori: {params.vehicle_category}",
            ]
            if params.vehicle_brand or params.vehicle_model:
                model_txt = f"{params.vehicle_brand} {params.vehicle_model}"
                if params.vehicle_submodel:
                    model_txt += f" {params.vehicle_submodel}"
                filter_parts.append(f"Marka/Model: {model_txt}")
            if params.vehicle_transmission:
                filter_parts.append(f"Vites: {params.vehicle_transmission.capitalize()}")
            if params.vehicle_year_min or params.vehicle_year_max:
                filter_parts.append(f"Yıl: {params.vehicle_year_min or '–'}–{params.vehicle_year_max or '–'}")
            if params.vehicle_km_min or params.vehicle_km_max:
                filter_parts.append(f"Km: {params.vehicle_km_min or '–'}–{params.vehicle_km_max or '–'}")
            if params.vehicle_price_min or params.vehicle_price_max:
                filter_parts.append(f"Fiyat: {params.vehicle_price_min or '–'}–{params.vehicle_price_max or '–'} TL")
            filter_parts.append(f"Hasarlı: {'Evet' if params.vehicle_damage else 'Hayır'}")
            filters = " | ".join(filter_parts)
        else:
            stats.update({
                "estate": params.estate,
                "rooms": params.rooms or "–",
                "min_m2": params.min_m2,
                "max_m2": params.max_m2,
                "building_age": params.building_age,
                "site_icinde": params.site_icinde,
                "acik_mutfak": params.acik_mutfak,
                "dogalgaz": params.dogalgaz,
            })
            filter_parts = [
                f"İşlem: {'Kiralık' if params.transaction == 'kiralik' else 'Satılık'}",
                f"Emlak: {params.estate}",
            ]
            if params.rooms:
                filter_parts.append(f"Oda: {params.rooms}")
            if params.min_m2 or params.max_m2:
                filter_parts.append(f"Metrekare: {params.min_m2 or 0}-{params.max_m2 or '∞'} m²")
            if params.building_age >= 0:
                filter_parts.append(f"Bina yaşı: {params.building_age}-{params.building_age+1} yr")
            feats = []
            if params.site_icinde: feats.append("Site içi")
            if params.acik_mutfak: feats.append("Açık mutfak")
            if params.dogalgaz: feats.append("Doğalgaz")
            if feats:
                filter_parts.append("Özellikler: " + ", ".join(feats))
            filters = " | ".join(filter_parts)

        pdf_path = generate_pdf(stats, params.title, filters, OUTPUT_DIR / f"{prefix}_rapor.pdf")
        print(f"\nPDF rapor: {pdf_path}")
        try:
            import os
            os.startfile(str(pdf_path))
        except Exception:
            pass
    finally:
        await close_playwright(pw, browser)


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nİptal edildi.")
    except Exception as e:
        print("\nHATA:", e)
        traceback.print_exc()
    input("\nÇıkmak için Enter'a basın...")


if __name__ == "__main__":
    main()
