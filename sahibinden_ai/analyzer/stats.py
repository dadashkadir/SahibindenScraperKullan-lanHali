"""İlanların istatistiksel analizi."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


def _tl(v) -> str:
    """Sayıyı Türkçe binlik ayracı (nokta) ile formatla: 2450000 -> '2.450.000'."""
    try:
        return f"{v:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def _num(txt):
    """'2.450.000 TL' -> 2450000, '1.250' -> 1250 (Türkçe: nokta binlik ayracı, virgül ondalık)."""
    if not txt:
        return np.nan
    s = re.sub(r"[^\d\.,]", "", str(txt))
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def to_dataframe(listings: list) -> pd.DataFrame:
    df = pd.DataFrame(listings)
    for col in ("title", "url", "price", "gross_m2", "room", "location"):
        if col not in df:
            df[col] = ""
    df["price_num"] = df["price"].apply(_num)
    df["m2_num"] = df["gross_m2"].apply(_num)
    df["price_per_m2"] = df["price_num"] / df["m2_num"]
    df.loc[~np.isfinite(df["price_per_m2"]), "price_per_m2"] = np.nan
    return df


def _block(s: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {}
    return {"count": int(s.size), "min": float(s.min()), "p25": float(s.quantile(.25)),
            "median": float(s.median()), "mean": float(s.mean()),
            "p75": float(s.quantile(.75)), "max": float(s.max())}


def run_analysis(listings: list) -> dict:
    df = to_dataframe(listings)
    valid = df.dropna(subset=["price_num"])
    if valid.empty:
        raise ValueError("Fiyat bilgisi olan ilan bulunamadı.")
    res = {"df": df, "count_total": int(len(df)), "count_priced": int(len(valid))}
    res["price"] = _block(valid["price_num"])
    res["ppm2"] = _block(valid["price_per_m2"])
    res["m2"] = _block(valid["m2_num"])

    by_room = {}
    if (df["room"] != "").any():
        for room, sub in df[df["room"] != ""].groupby("room"):
            if sub["price_num"].notna().sum() >= 1:
                by_room[str(room)] = {"count": int(len(sub)),
                                      "median_price": float(sub["price_num"].median()),
                                      "median_ppm2": float(sub["price_per_m2"].median())
                                      if sub["price_per_m2"].notna().any() else float("nan")}
    res["by_room"] = dict(sorted(by_room.items()))

    ppm = valid["price_per_m2"].dropna()
    if len(ppm) >= 8:
        q1, q3 = ppm.quantile(.25), ppm.quantile(.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        res["outlier_count"] = int(((ppm < lo) | (ppm > hi)).sum())
        clean = valid[(valid["price_per_m2"] >= lo) & (valid["price_per_m2"] <= hi)]
    else:
        res["outlier_count"] = 0
        clean = valid
    res["clean_df"] = clean

    # Fast / Slow / Average sale metrics based on price per m2 distribution
    if not ppm.empty:
        fast_thr = ppm.quantile(0.25)   # alt %25 -> hızlı satış beklentisi
        slow_thr = ppm.quantile(0.75)   # üst %25 -> yavaş satış beklentisi
        fast_series = ppm[ppm <= fast_thr]
        slow_series = ppm[ppm >= slow_thr]
        avg_series = ppm  # genel dağılım

        res["fast_sale"] = _block(fast_series)
        res["slow_sale"] = _block(slow_series)
        res["average_sale"] = _block(avg_series)
    else:
        res["fast_sale"] = {}
        res["slow_sale"] = {}
        res["average_sale"] = {}

    # Total price quartiles for valuation ranges
    price_series = valid["price_num"].dropna()
    if not price_series.empty:
        res["price_quartiles"] = {
            "p25": float(price_series.quantile(0.25)),
            "p50": float(price_series.quantile(0.50)),
            "p75": float(price_series.quantile(0.75)),
            "count": int(price_series.size)
        }
    else:
        res["price_quartiles"] = {}

    # Location feature analysis
    location_features = _analyze_location_features(df)
    res["location_features"] = location_features

    # AI‑style recommendation text
    res["recommendation"] = _generate_recommendation(res)
    return res


def _analyze_location_features(df: pd.DataFrame) -> dict:
    """İlan konum metinlerinden basit anahtar kelimelerle özellik çıkarıp yüzdelik oran döndürür."""
    total = len(df)
    if total == 0:
        return {}
    loc_series = df["location"].fillna("").str.lower()
    keywords = {
        "Deniz Kenarı": ["deniz", "sahil", "kıyı", "sea", "beach"],
        "AVM Yakınlığı": ["avm", "alışveriş merkezi", "mall", "optimum", "forum", "panora", "akmerkez"],
        "Merkez Yakınlığı": ["merkez", "center", "şehir merkezi", "merkez mah"],
        "Metro/Toplu Taşıma": ["metro", "metrobüs", "istasyon", "tramvay"]
    }
    result = {}
    for label, kws in keywords.items():
        mask = loc_series.apply(lambda x: any(kw in x for kw in kws))
        count = int(mask.sum())
        pct = round(count / total * 100, 1)
        result[label] = {"count": count, "percentage": pct}
    return result


def _generate_recommendation(stats: dict) -> str:
    """İstatistiklere dayalı, doğal dilde profesyonel değerleme raporu üretir."""
    lines = []

    # ---- Özellik özeti (filtreler) ----
    transaction = stats.get("transaction", "satilik")
    estate = stats.get("estate", "")
    rooms = stats.get("rooms", "")
    min_m2 = stats.get("min_m2", 0)
    max_m2 = stats.get("max_m2", 0)
    building_age = stats.get("building_age", -1)
    site_icinde = stats.get("site_icinde", False)
    acik_mutfak = stats.get("acik_mutfak", False)
    dogalgaz = stats.get("dogalgaz", False)

    is_rent = transaction == "kiralik"
    unit = "TL/ay" if is_rent else "TL"
    verb = "kira" if is_rent else "satış"

    prop_lines = [f"🏠 **Taşınmaz Özellikleri**"]
    if estate:
        prop_lines.append(f"Tip: {estate}" + (f" {rooms}" if rooms else ""))
    if min_m2 or max_m2:
        prop_lines.append(f"Alan: {min_m2 or 0}–{max_m2 or '∞'} m²")
    if building_age >= 0:
        prop_lines.append(f"Bina yaşı: {building_age}-{building_age+1} yıl")
    feats = []
    if site_icinde: feats.append("Site içinde")
    if acik_mutfak: feats.append("Açık mutfak")
    if dogalgaz: feats.append("Doğalgaz")
    if feats:
        prop_lines.append("Özellikler: " + ", ".join(feats))
    lines.append("\n".join(prop_lines))

    # ---- Emsal / Piyasa verisi özeti ----
    pq = stats.get("price_quartiles", {})
    if pq:
        p25 = pq.get("p25", 0)
        p50 = pq.get("p50", 0)
        p75 = pq.get("p75", 0)
        cnt = pq.get("count", 0)
        lines.append(f"\n📊 **Güncel Emsaller ({cnt} ilan)**")
        lines.append(f"Alt çeyrek (hızlı {verb}) : {_tl(p25)} {unit}")
        lines.append(f"Medyan (normal {verb})   : {_tl(p50)} {unit}")
        lines.append(f"Üst çeyrek (yavaş {verb}) : {_tl(p75)} {unit}")

        # Valuation ranges
        fast_low = p25
        fast_high = p50
        normal_low = p50
        normal_high = p75
        slow_low = p75
        slow_high = stats.get("price", {}).get("max", p75 * 1.1)

        lines.append("\n📈 **Değerleme Aralıkları**")
        lines.append(f"🔴 **Hızlı {verb.capitalize()}**   : {_tl(fast_low)} – {_tl(fast_high)} {unit}  (alıcıyı bekletmeden)")
        lines.append(f"🟡 **Normal / Makul {verb.capitalize()}** : {_tl(normal_low)} – {_tl(normal_high)} {unit}  (piyasa şartlarında gerçekçi)")
        lines.append(f"🟢 **Yavaş / Sabırlı {verb.capitalize()}** : {_tl(slow_low)} – {_tl(slow_high)} {unit}  (doğru alıcı beklenerek)")

        # Recommended listing price
        target = (p50 + p75) / 2
        lines.append(f"\n💡 **Önerilen İlan Fiyatı** : {_tl(target)} {unit}")
        lines.append("→ Pazarlık payı bırakarak hedef satış: "
                     f"{_tl(p50)} – {_tl(p75)} {unit}")
        lines.append("→ Çok hızlı olması gerekiyorsa: "
                     f"{_tl(p25)} – {_tl((p25+p50)/2)} {unit}")

    # ---- Genel strateji notu ----
    lines.append("\n📌 **Strateji Notu**")
    lines.append("Bu analiz, sahibinden.com'daki güncel ilan fiyatlarına dayanır; gerçekleşen tapu satış fiyatları "
                 "farklı olabilir. İlan metninizde m² fiyatı, aidat, tapu durumu, kredi uygunluğu, "
                 "bahçe/teras, cephe, park yeri gibi avantajları net belirtin. "
                 "Farklı portallarda (emlakjet, hepsiemlak) ve bölgedeki ofislerle karşılama yaparak fiyatı test edin.")

    return "\n".join(lines)
