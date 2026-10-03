"""PDF rapor (fpdf2 + Noto Sans, Türkçe karakter destekli)."""
import sys
from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def _font_dir() -> Path:
    # Windows sistem fontlarını kullan (Arial Türkçe karakterleri destekler)
    system_fonts = Path("C:/Windows/Fonts")
    if system_fonts.exists():
        return system_fonts
    # fallback: bundled fonts if ever added
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "sahibinden_ai" / "storage" / "fonts"
    return Path(__file__).parent / "fonts"


def _tl(v) -> str:
    try:
        return f"{v:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def _cut(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1] + "…"


class Report(FPDF):
    def __init__(self, title):
        super().__init__()
        self.report_title = title
        fd = _font_dir()
        # Arial regular ve bold (Windows'ta mevcut)
        regular = fd / "arial.ttf"
        bold = fd / "arialbd.ttf"
        if regular.exists() and bold.exists():
            self.add_font("Arial", "", str(regular))
            self.add_font("Arial", "B", str(bold))
            self.add_font("Arial", "I", str(regular))  # italik yok, normal kullan
            self.font_family = "Arial"
        else:
            # fallback to Noto if bundled
            self.add_font("Noto", "", str(fd / "NotoSans-Regular.ttf"))
            self.add_font("Noto", "B", str(fd / "NotoSans-Bold.ttf"))
            self.add_font("Noto", "I", str(fd / "NotoSans-Regular.ttf"))
            self.font_family = "Noto"
        self.set_auto_page_break(True, 15)
        self.alias_nb_pages()

    def header(self):
        self.set_font(self.font_family, "B", 13)
        title_text = "Sahibinden Vasıta Değerleme Raporu" if getattr(self, "is_vasita", False) else "Sahibinden Emlak Analiz Raporu"
        self.cell(0, 8, title_text, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(self.font_family, "", 9)
        self.cell(0, 5, self.report_title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.line(10, self.get_y() + 1, 200, self.get_y() + 1)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font(self.font_family, "I", 8)
        self.cell(0, 8, f"Sayfa {self.page_no()}/{{nb}}", align="C")

    def h2(self, t):
        self.ln(2)
        self.set_font(self.font_family, "B", 11)
        self.cell(0, 7, t, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def table(self, headers, rows, widths, aligns=None, size=8.5):
        aligns = aligns or ["L"] * len(headers)
        self.set_font(self.font_family, "B", size)
        self.set_fill_color(230, 230, 230)
        for h, w in zip(headers, widths):
            self.cell(w, 6.5, h, border=1, align="C", fill=True)
        self.ln()
        self.set_font(self.font_family, "", size)
        for r in rows:
            if self.get_y() > 275:
                self.add_page()
                self.set_font(self.font_family, "B", size)
                for h, w in zip(headers, widths):
                    self.cell(w, 6.5, h, border=1, align="C", fill=True)
                self.ln()
                self.set_font(self.font_family, "", size)
            for v, w, a in zip(r, widths, aligns):
                self.cell(w, 5.8, str(v), border=1, align=a)
            self.ln()

    def bars(self, labels, values, unit=""):
        """Basit yatay çubuk grafik (ek kütüphane gerektirmez)."""
        vmax = max(values) if values else 1
        x0, maxw = 40, 110
        for lab, v in zip(labels, values):
            y = self.get_y()
            self.set_font(self.font_family, "", 9)
            self.cell(30, 6, str(lab))
            self.set_fill_color(70, 130, 180)
            self.rect(x0, y + 1, max(1, maxw * v / vmax), 4, style="F")
            self.set_x(x0 + maxw + 3)
            self.cell(0, 6, f"{_tl(v)} {unit}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def kv_bold(self, label, value, unit=""):
        """Etiket normal, değer kalın yazdırır."""
        self.set_font(self.font_family, "", 10)
        self.cell(0, 6, label, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(self.font_family, "B", 10)
        self.cell(0, 6, f"{value} {unit}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)


def generate_pdf(stats: dict, title: str, filters: str, out_path: Path):
    pdf = Report(title)
    pdf.is_vasita = stats.get("market_type") == "vasita"
    if pdf.is_vasita:
        pdf.report_title = "Sahibinden Vasıta Değerleme Raporu"
    pdf.add_page()

    # Show filters on first page
    pdf.h2("Filtreler")
    pdf.set_font(pdf.font_family, "", 9)
    pdf.multi_cell(0, 5, filters)
    pdf.ln(4)

    if pdf.is_vasita:
        # Özet değerler
        gp = stats.get("galerici_price")
        rp = stats.get("resale_price")
        if gp or rp:
            pdf.h2("Özet Değerler")
            pdf.set_font(pdf.font_family, "", 9)
            if gp:
                pdf.cell(0, 6, f"Galerici Alış Fiyatı (hızlı satış -%20): {_tl(gp)} TL", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if rp:
                pdf.cell(0, 6, f"Önerilen Satış Fiyatı (alıcıya): {_tl(rp)} TL", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(4)

        # AI Öneri (içinde tablolar yer alıyor)
        recommendation = stats.get("recommendation")
        if recommendation:
            pdf.add_page()
            pdf.h2("Yapay Zeka Önerileri")
            pdf.set_font(pdf.font_family, "", 9)
            for para in recommendation.split("\n\n"):
                pdf.multi_cell(0, 5, para)
                pdf.ln(2)

        pdf.output(str(out_path))
        return out_path

    # ----- EMLAK RAPOR (eski mantık) -----
    pdf.set_font(pdf.font_family, "", 10)
    pdf.cell(0, 6, f"Tarih: {datetime.now():%d.%m.%Y %H:%M}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Filtre: {filters}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Taranan ilan: {stats['count_total']}  |  Fiyatı okunan: {stats['count_priced']}"
                   f"  |  Uç değer (m² fiyatı): {stats['outlier_count']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.h2("Fiyat Özeti")
    rows = []
    for label, key in (("Toplam fiyat (TL)", "price"), ("m² fiyatı (TL/m²)", "ppm2"), ("Alan (m²)", "m2")):
        b = stats.get(key) or {}
        if b:
            rows.append([label, _tl(b["min"]), _tl(b["p25"]), _tl(b["median"]), _tl(b["mean"]),
                         _tl(b["p75"]), _tl(b["max"])])
    pdf.table(["Metrik", "En düşük", "Alt çeyrek", "Medyan", "Ortalama", "Üst çeyrek", "En yüksek"],
              rows, [40, 25, 25, 25, 25, 25, 25], ["L"] + ["R"] * 6)

    # Hızlı / Yavaş / Ortalama Satış Metrikleri
    metric_name = {
        "fast_sale": "Hızlı Satış",
        "slow_sale": "Yavaş Satış",
        "average_sale": "Ortalama Satış"
    }
    for label_key, section_title in (("fast_sale", "Hızlı Satış Beklentisi (Alt %25)"),
                                    ("slow_sale", "Yavaş Satış Riski (Üst %25)"),
                                    ("average_sale", "Genel Piyasa (Ortalama)")):
        block = stats.get(label_key, {})
        if block:
            pdf.h2(section_title)
            pdf.table(["Metrik", "En düşük", "Alt çeyrek", "Medyan", "Ortalama", "Üst çeyrek", "En yüksek"],
                      [[metric_name.get(label_key, label_key), _tl(block.get("min")), _tl(block.get("p25")), _tl(block.get("median")),
                        _tl(block.get("mean")), _tl(block.get("p75")), _tl(block.get("max"))]],
                      [40, 25, 25, 25, 25, 25, 25], ["L"] + ["R"] * 6)

    if stats["by_room"]:
        pdf.h2("Oda Sayısına Göre")
        rooms = stats["by_room"]
        pdf.table(["Oda", "İlan", "Medyan fiyat (TL)", "Medyan m² fiyatı (TL/m²)"],
                  [[r, s["count"], _tl(s["median_price"]), _tl(s["median_ppm2"])] for r, s in rooms.items()],
                  [30, 25, 50, 60], ["L", "C", "R", "R"])
        pdf.ln(3)
        pdf.set_font(pdf.font_family, "B", 9)
        pdf.cell(0, 6, "Medyan m² fiyatı", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        good = [(r, s["median_ppm2"]) for r, s in rooms.items() if s["median_ppm2"] == s["median_ppm2"]]
        if good:
            pdf.bars([g[0] for g in good], [g[1] for g in good], "TL/m²")

    clean = stats["clean_df"].dropna(subset=["price_per_m2"]).sort_values("price_per_m2")
    if not clean.empty:
        cols = ["Başlık", "Oda", "m²", "Fiyat (TL)", "TL/m²"]
        w = [80, 15, 18, 35, 30]
        al = ["L", "C", "R", "R", "R"]

        def rows_of(d):
            return [[_cut(r.title, 48), r.room, r.gross_m2, _tl(r.price_num), _tl(r.price_per_m2)]
                    for r in d.itertuples()]

        pdf.h2("Fırsat Olabilecek İlanlar (en düşük m² fiyatı, ilk 10)")
        pdf.table(cols, rows_of(clean.head(10)), w, al)
        pdf.h2("En Pahalı İlanlar (m² fiyatı, ilk 10)")
        pdf.table(cols, rows_of(clean.tail(10).iloc[::-1]), w, al)

    # AI Öneri Bölümü
    recommendation = stats.get("recommendation")
    if recommendation:
        pdf.add_page()
        pdf.h2("Yapay Zeka Önerileri")
        pdf.set_font(pdf.font_family, "", 9)
        # split paragraphs
        for para in recommendation.split("\n\n"):
            pdf.multi_cell(0, 5, para)
            pdf.ln(2)

    # Satış Hızı Özeti (kalın değerler)
    fast = stats.get("fast_sale", {})
    slow = stats.get("slow_sale", {})
    avg = stats.get("average_sale", {})
    if fast or slow or avg:
        pdf.add_page()
        pdf.h2("Satış Hızı Özeti")
        if fast:
            pdf.kv_bold("Hızlı Satış Fiyatı (Alt %25, medyan m²):", _tl(fast.get("median", 0)), "TL/m²")
        if slow:
            pdf.kv_bold("Yavaş Satış Fiyatı (Üst %25, medyan m²):", _tl(slow.get("median", 0)), "TL/m²")
        if avg:
            pdf.kv_bold("Ortalama Satış Fiyatı (Genel medyan m²):", _tl(avg.get("median", 0)), "TL/m²")

    # Bölge Özellikleri
    loc_feats = stats.get("location_features", {})
    if loc_feats:
        pdf.add_page()
        pdf.h2("Bölge Özellikleri")
        loc_rows = []
        for feat, data in loc_feats.items():
            loc_rows.append([feat, str(data["count"]), f"{data['percentage']}%"])
        pdf.table(["Özellik", "İlan Sayısı", "Yüzde (%)"], loc_rows, [80, 30, 30], ["L", "C", "C"])

    df = stats["df"].sort_values("price_num")
    pdf.add_page()
    pdf.h2("Tüm İlanlar (fiyata göre, artan)")
    pdf.table(["Başlık", "Oda", "m²", "Fiyat (TL)", "Konum"],
              [[_cut(r.title, 44), r.room, r.gross_m2, _tl(r.price_num), _cut(r.location.replace("\n", " "), 24)]
               for r in df.itertuples()],
              [78, 14, 18, 32, 48], ["L", "C", "R", "R", "L"], size=7.5)

    pdf.output(str(out_path))
    return out_path
