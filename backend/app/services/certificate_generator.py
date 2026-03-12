"""
PDF Certificate Generator for Anasteisha Beauty Courses
Palette: cream background, gold accents, dark brown text
"""
import os
import uuid
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# Anasteisha brand colors (from style.css)
CREAM        = HexColor("#F5F2EE")   # --cream
CREAM_DARK   = HexColor("#EBE7E2")   # --cream-dark
GOLD         = HexColor("#B8860B")   # --gold
GOLD_LIGHT   = HexColor("#E8D5A8")   # --gold-light
GOLD_ACCENT  = HexColor("#DAA520")   # --gold-accent
GOLD_RICH    = HexColor("#CD950C")   # --gold-rich
DARK         = HexColor("#1C1408")   # --black (dark brown)
GRAY_DARK    = HexColor("#3A2E1E")   # --gray-dark
GRAY         = HexColor("#6B5D4A")   # --gray
GRAY_LIGHT   = HexColor("#9A8D7A")   # --gray-light

FONT_REGULAR = "Arial"
FONT_BOLD    = "Arial-Bold"

_fonts_registered = False


def _register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return

    paths = [
        ("C:/Windows/Fonts/arial.ttf",   FONT_REGULAR),
        ("C:/Windows/Fonts/arialbd.ttf", FONT_BOLD),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      FONT_REGULAR),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", FONT_BOLD),
        ("/Library/Fonts/Arial.ttf",      FONT_REGULAR),
        ("/Library/Fonts/Arial Bold.ttf", FONT_BOLD),
    ]

    registered = set()
    for path, name in paths:
        if name not in registered and os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            registered.add(name)

    _fonts_registered = True


def generate_certificate_code() -> str:
    """Generate unique code like ANS-2026-A3F8B2"""
    year = datetime.utcnow().year
    uid = uuid.uuid4().hex[:6].upper()
    return f"ANS-{year}-{uid}"


def _draw_ornament_line(c, cx, y, half_w):
    """Draw a decorative line with a diamond in the centre."""
    c.setStrokeColor(GOLD_ACCENT)
    c.setLineWidth(1.2)
    c.line(cx - half_w, y, cx + half_w, y)

    d = 2.5 * mm
    c.setFillColor(GOLD_ACCENT)
    c.saveState()
    c.translate(cx, y)
    c.rotate(45)
    c.rect(-d / 2, -d / 2, d, d, fill=True, stroke=False)
    c.restoreState()


def generate_certificate_pdf(
    student_name: str,
    course_title: str,
    completion_date: datetime,
    verification_code: str,
    output_dir: str,
    site_url: str = "anasteisha.ru",
) -> str:
    """
    Generate a beauty-styled PDF certificate (A4 landscape).
    Returns the filename of the generated PDF.
    """
    _register_fonts()
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{verification_code}.pdf"
    filepath = os.path.join(output_dir, filename)

    width, height = landscape(A4)
    c = canvas.Canvas(filepath, pagesize=landscape(A4))
    cx = width / 2

    # ── Background ──────────────────────────────────────────────────────────
    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # Subtle inner cream-dark fill strip at top and bottom
    strip_h = 18 * mm
    c.setFillColor(CREAM_DARK)
    c.rect(0, height - strip_h, width, strip_h, fill=True, stroke=False)
    c.rect(0, 0, width, strip_h, fill=True, stroke=False)

    # ── Outer border ────────────────────────────────────────────────────────
    margin = 12 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin,
           fill=False, stroke=True)

    # Inner thin border
    inner = 16 * mm
    c.setStrokeColor(GOLD_LIGHT)
    c.setLineWidth(0.6)
    c.rect(inner, inner, width - 2 * inner, height - 2 * inner,
           fill=False, stroke=True)

    # ── Corner accents ───────────────────────────────────────────────────────
    cs = 10 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    for (bx, by) in [(margin, margin), (width - margin, margin),
                     (width - margin, height - margin), (margin, height - margin)]:
        dx = cs  if bx == margin else -cs
        dy = cs  if by == margin else -cs
        c.line(bx, by, bx + dx, by)
        c.line(bx, by, bx, by + dy)

    # ── Brand name (top strip) ───────────────────────────────────────────────
    c.setFillColor(GOLD_ACCENT)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(cx, height - 12 * mm, "ANASTEISHA")

    # Small dots on each side of brand name
    dot_y = height - 11 * mm
    for dx in [-45 * mm, 45 * mm]:
        c.setFillColor(GOLD)
        c.circle(cx + dx, dot_y, 1.5 * mm, fill=True, stroke=False)

    # ── "СЕРТИФИКАТ" ─────────────────────────────────────────────────────────
    c.setFillColor(GRAY_DARK)
    c.setFont(FONT_REGULAR, 13)
    c.drawCentredString(cx, height - 32 * mm, "С Е Р Т И Ф И К А Т")

    # Ornament line under title
    _draw_ornament_line(c, cx, height - 40 * mm, 55 * mm)

    # ── "Настоящим подтверждается, что" ──────────────────────────────────────
    c.setFillColor(GRAY)
    c.setFont(FONT_REGULAR, 11)
    c.drawCentredString(cx, height - 55 * mm, "Настоящим подтверждается, что")

    # ── Student name ─────────────────────────────────────────────────────────
    c.setFillColor(DARK)
    c.setFont(FONT_BOLD, 30)
    display_name = student_name if len(student_name) <= 40 else student_name[:37] + "..."
    c.drawCentredString(cx, height - 75 * mm, display_name)

    # Decorative underline for name
    c.setStrokeColor(GOLD_RICH)
    c.setLineWidth(1)
    c.line(cx - 75 * mm, height - 79 * mm, cx + 75 * mm, height - 79 * mm)

    # ── "успешно завершила курс" ──────────────────────────────────────────────
    c.setFillColor(GRAY)
    c.setFont(FONT_REGULAR, 11)
    c.drawCentredString(cx, height - 92 * mm, "успешно завершила курс")

    # ── Course title ─────────────────────────────────────────────────────────
    c.setFillColor(GOLD)
    c.setFont(FONT_BOLD, 17)
    if len(course_title) > 50:
        mid = len(course_title) // 2
        split = course_title.rfind(" ", 0, mid + 10) or mid
        c.drawCentredString(cx, height - 107 * mm, f"\u00ab{course_title[:split]}")
        c.drawCentredString(cx, height - 118 * mm, f"{course_title[split+1:]}\u00bb")
    else:
        c.drawCentredString(cx, height - 107 * mm, f"\u00ab{course_title}\u00bb")

    # ── Bottom ornament line ──────────────────────────────────────────────────
    _draw_ornament_line(c, cx, 52 * mm, 55 * mm)

    # ── Bottom info row ───────────────────────────────────────────────────────
    bottom_y = 35 * mm
    formatted_date = completion_date.strftime("%d.%m.%Y")

    # Date
    c.setFillColor(GRAY_LIGHT)
    c.setFont(FONT_REGULAR, 8)
    c.drawCentredString(cx - 70 * mm, bottom_y + 6 * mm, "Дата выдачи")
    c.setFillColor(GRAY_DARK)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(cx - 70 * mm, bottom_y - 3 * mm, formatted_date)

    # Certificate number
    c.setFillColor(GRAY_LIGHT)
    c.setFont(FONT_REGULAR, 8)
    c.drawCentredString(cx, bottom_y + 6 * mm, "Номер сертификата")
    c.setFillColor(GRAY_DARK)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(cx, bottom_y - 3 * mm, verification_code)

    # Verify URL
    c.setFillColor(GRAY_LIGHT)
    c.setFont(FONT_REGULAR, 8)
    c.drawCentredString(cx + 70 * mm, bottom_y + 6 * mm, "Проверить подлинность")
    c.setFillColor(GOLD)
    c.setFont(FONT_REGULAR, 8)
    c.drawCentredString(cx + 70 * mm, bottom_y - 3 * mm,
                        f"{site_url}/verify/{verification_code}")

    # ── Bottom strip brand ────────────────────────────────────────────────────
    c.setFillColor(GOLD_ACCENT)
    c.setFont(FONT_BOLD, 8)
    c.drawCentredString(cx, 9 * mm, "anasteisha.ru  ·  косметология")

    c.save()
    return filename
