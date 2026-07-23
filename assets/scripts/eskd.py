#!/usr/bin/env python3
"""
eskd.py — примитивы чертежей ЕСКД → SVG · 1 мм = 3 px

Источник: §9 reference М20×100 (line 432+ в daniya_full.html).
Match STRUCTURE (head path, shaft path, face lines, arc chamfers, dimensions),
НЕ pixel coords. Все координаты вычисляются из Table 10 (d, l, l0, S, D, h, c).

msgId 1001 patch (v4 + pictorial):
  - Iter4 #1: размерные отступы h_y = head_y_bot+30, l0_y = shaft_y_bot+30,
             l_y = l0_y+21 (НЕ l0_y+51 от shaft_y_bot? см. v4 vt.10)
             На самом деле по Даня feedback: l₀ y=низ стержня+30, l y=низ стержня+51
  - Iter4 #2: d-dim стрелки СНАРУЖИ (зона < 36 px) — уже сделано
  - Iter4 #3: толщины строго {2.4, 1}
  - Iter4 #4: фаска торца — два зеркальных скоса без промежуточных точек
  - Pictorial: iso-view группа rotate(-35), белые заливки, тонкие диагонали
             резьбы шаг 9 px, головка сжата по y (k≈0,45), выноски Резьба/
             Стержень/Фаска/Головка с подчёркиванием
"""
import math
import re

MM = 3
INK = "#1A1A18"
WHITE = "#FFFFFF"
THICK = 2.4
THIN = 1.0
AXIS = "24 5 3 5"

DIM_0 = 30   # первая размерная от контура (vt.7, v4 vt.10)
DIM_D = 21   # шаг между размерными
ISO_ANGLE = -35   # аксонометрия
ISO_K = 0.45      # сжатие головки по оси y в iso (k≈0,45)


DEFS = (
    '<defs>'
    '<marker id="ar" orient="auto-start-reverse" markerUnits="userSpaceOnUse"'
    ' markerWidth="26" markerHeight="10" viewBox="-13 -5 26 10" refX="0" refY="0">'
    '<path d="M0,0 L-12,2.4 L-12,-2.4 Z" fill="#1A1A18"/></marker>'
    '<pattern id="ht" width="9" height="9" patternUnits="userSpaceOnUse"'
    ' patternTransform="rotate(45)">'
    '<line x2="9" stroke="#1A1A18" stroke-width="1"/></pattern>'
    '</defs>'
)


def ln(x1, y1, x2, y2, w=THIN, dash="", arrows=False):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    a = ' marker-start="url(#ar)" marker-end="url(#ar)"' if arrows else ""
    return ('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#1A1A18"'
            ' stroke-width="%g"%s%s/>' % (x1, y1, x2, y2, w, d, a))


def txt(x, y, s, rot=0, size=15, color=INK):
    r = ' transform="rotate(%g %g %g)"' % (rot, x, y) if rot else ""
    return ('<text x="%g" y="%g" text-anchor="middle" fill="%s"'
            ' font-family="\'PT Sans\'" font-style="italic" font-size="%g"%s>%s</text>'
            % (x, y, color, size, r, s))


def path(d, w=THICK, fill="none"):
    return ('<path d="%s" fill="%s" stroke="#1A1A18" stroke-width="%g"/>'
            % (d, fill, w))


def hexagon(cx, cy, r_mm):
    p = " ".join("%.1f,%.1f" % (cx + r_mm * MM * math.sin(math.pi * k / 3),
                                cy - r_mm * MM * math.cos(math.pi * k / 3))
                 for k in range(6))
    return ('<polygon points="%s" fill="none" stroke="#1A1A18"'
            ' stroke-width="%g"/>' % (p, THICK))


# ============================================================================
# Композиция: главный вид болта
# ============================================================================

def bolt_front_view(d, l, l0, S, D, h, c):
    head_x_right = h * MM
    shaft_x_right = l * MM + head_x_right

    D_px = D * MM
    d_px = d * MM
    head_y_top, head_y_bot = -D_px / 2, +D_px / 2
    shaft_y_top, shaft_y_bot = -d_px / 2, +d_px / 2
    vpad_y_top, vpad_y_bot = -0.425 * d_px, +0.425 * d_px

    chamfer_x_start = shaft_x_right - c * MM
    chamfer_y_top = -d_px / 2 + c * MM
    chamfer_y_bot = +d_px / 2 - c * MM

    thread_bx = shaft_x_right - l0 * MM

    cf_head = h * MM * 0.155
    face_y_top, face_y_bot = -D_px / 4, +D_px / 4

    parts = []

    # 1. ОСЕВАЯ
    pad_axis = 8
    parts.append(ln(-pad_axis, 0, shaft_x_right + pad_axis, 0, THIN, AXIS))

    # 2. ГОЛОВКА — замкнутый path + 2 грани + 3 дуги фаски
    parts.append(path(
        "M 0,%g L %g,%g L %g,%g L %g,%g L %g,%g L 0,%g Z"
        % (head_y_top + cf_head, cf_head, head_y_top,
           head_x_right, head_y_top, head_x_right, head_y_bot,
           cf_head, head_y_bot, head_y_bot - cf_head), THICK))
    parts.append(ln(0, face_y_top, head_x_right, face_y_top, THICK))
    parts.append(ln(0, face_y_bot, head_x_right, face_y_bot, THICK))
    # Дуги фаски (3 по эталону)
    ax1 = cf_head + 1
    parts.append(path(
        "M %g,%g Q %g,%g %g,%g"
        % (ax1, -D_px / 2 + 1, 2 * cf_head + 2, -D_px / 2 + 13, ax1, face_y_top - 2),
        THICK))
    parts.append(path(
        "M %g,%g Q %g,%g %g,%g"
        % (2 * cf_head, face_y_top - 1, cf_head - 1, 0, 2 * cf_head, face_y_bot + 1),
        THICK))
    parts.append(path(
        "M %g,%g Q %g,%g %g,%g"
        % (ax1, D_px / 2 - 1, 2 * cf_head + 2, D_px / 2 - 13, ax1, -face_y_top + 2),
        THICK))

    # 3. СТЕРЖЕНЬ — ЗАМКНУТЫЙ path (vt.1, vt.9 — NUM self-check)
    parts.append(path(
        "M %g,%g L %g,%g L %g,%g L %g,%g L %g,%g L %g,%g Z"
        % (head_x_right, shaft_y_top, chamfer_x_start, shaft_y_top,
           shaft_x_right, chamfer_y_top, shaft_x_right, chamfer_y_bot,
           chamfer_x_start, shaft_y_bot, head_x_right, shaft_y_bot),
        THICK))
    parts.append(ln(head_x_right, head_y_top, head_x_right, shaft_y_top, THICK))
    parts.append(ln(head_x_right, shaft_y_bot, head_x_right, head_y_bot, THICK))

    # 4. РЕЗЬБА
    parts.append(ln(thread_bx, shaft_y_top, thread_bx, shaft_y_bot, THICK))
    vpad_x_end = chamfer_x_start + 3.5
    parts.append(ln(thread_bx, vpad_y_top, vpad_x_end, vpad_y_top, THIN))
    parts.append(ln(thread_bx, vpad_y_bot, vpad_x_end, vpad_y_bot, THIN))

    # 5. РАЗМЕРЫ — v4 vt.10: каждая от своего контура
    # h: от нижней грани головки (head_y_bot) + 30
    h_y = head_y_bot + 30
    parts.append(ln(0, head_y_bot + 1, 0, h_y, THIN))
    parts.append(ln(head_x_right, head_y_bot + 3, head_x_right, h_y, THIN))
    h_width = head_x_right
    if h_width < 36:
        parts.append(ln(-4, h_y, head_x_right + 4, h_y, THIN, arrows=True))
    else:
        parts.append(ln(0, h_y, head_x_right, h_y, THIN, arrows=True))
    parts.append(txt(head_x_right / 2, h_y - 5, "h"))

    # l₀: от НИЗА СТЕРЖНЯ (shaft_y_bot) + 30 — v4 vt.10
    l0_y = shaft_y_bot + 30
    parts.append(ln(thread_bx, shaft_y_bot + 3, thread_bx, l0_y, THIN))
    parts.append(ln(shaft_x_right, shaft_y_bot + 3, shaft_x_right, l0_y, THIN))
    l0_width = shaft_x_right - thread_bx
    if l0_width < 36:
        parts.append(ln(thread_bx - 4, l0_y, shaft_x_right + 4, l0_y, THIN, arrows=True))
    else:
        parts.append(ln(thread_bx, l0_y, shaft_x_right, l0_y, THIN, arrows=True))
    parts.append(txt((thread_bx + shaft_x_right) / 2, l0_y - 5, "l₀"))

    # l: от НИЗА СТЕРЖНЯ + 51 — v4 vt.10 (отдельная база, шаг 21 от l₀)
    l_y = l0_y + 21
    parts.append(ln(head_x_right, l0_y, head_x_right, l_y, THIN))  # продление выносной от h/l₀
    # Правая выносная для l — та же, что для l₀, продлённая вниз
    parts.append(ln(shaft_x_right, l0_y, shaft_x_right, l_y, THIN))
    l_width = shaft_x_right - head_x_right
    if l_width < 36:
        parts.append(ln(head_x_right - 4, l_y, shaft_x_right + 4, l_y, THIN, arrows=True))
    else:
        parts.append(ln(head_x_right, l_y, shaft_x_right, l_y, THIN, arrows=True))
    parts.append(txt((head_x_right + shaft_x_right) / 2, l_y - 5, "l"))

    # c×45° — vt.12: от верха стержня + 30 (ПАРАЛЛЕЛЬНЫЕ вертикали)
    c_y = shaft_y_top - 30
    parts.append(ln(chamfer_x_start, shaft_y_top - 1, chamfer_x_start, c_y, THIN))
    parts.append(ln(shaft_x_right, shaft_y_top - 1, shaft_x_right, c_y, THIN))
    parts.append(ln(chamfer_x_start - 4, c_y, shaft_x_right + 4, c_y,
                    THIN, arrows=True))
    parts.append(txt((chamfer_x_start + shaft_x_right) / 2, c_y - 5, "c×45°"))

    # ≈30° — vt.14: тонкие линии, контур головки не пересекают
    arc_y_start = head_y_top + cf_head
    arc_v_end_y = arc_y_start - 22
    parts.append(ln(0, arc_y_start, 0, arc_v_end_y, THIN))
    slant_dx = cf_head * 1.2
    slant_dy = -cf_head * 1.2
    slant_end_y = arc_y_start + slant_dy
    parts.append(ln(0, arc_y_start, slant_dx, slant_end_y, THIN))
    parts.append(path(
        "M 0,%g A 12 12 0 0 1 %g,%g"
        % (arc_v_end_y + 4, slant_dx * 0.5, slant_end_y + 2), THIN))
    parts.append(txt(-3, arc_v_end_y - 4, "≈30°", size=14))

    # d — vt.13: через гладкую часть, линии не пересекают контур
    d_x = (head_x_right + thread_bx) / 2
    if (shaft_y_bot - shaft_y_top) < 36:
        d_x_out = d_x - 12
        parts.append(ln(d_x_out, shaft_y_top - 6, d_x_out, shaft_y_bot + 6,
                        THIN, arrows=True))
        parts.append(ln(d_x_out + 6, shaft_y_top, d_x, shaft_y_top, THIN))
        parts.append(ln(d_x_out + 6, shaft_y_bot, d_x, shaft_y_bot, THIN))
        parts.append(txt(d_x_out - 6, 0, "d", rot=-90))
    else:
        parts.append(ln(d_x, shaft_y_top - 4, d_x, shaft_y_bot + 4,
                        THIN, arrows=True))
        parts.append(txt(d_x - 8, 0, "d", rot=-90))

    return "".join(parts)


# ============================================================================
# Вид слева (по эталону М20 reference)
# ============================================================================

def bolt_side_view(S, D, D1, cx, cy):
    R = D / 2 * MM
    R1 = D1 / 2 * MM
    parts = []
    pad = 10
    parts.append(ln(cx - R - pad, cy, cx + R + pad, cy, THIN, AXIS))
    parts.append(ln(cx, cy - R - pad, cx, cy + R + pad, THIN, AXIS))
    parts.append(hexagon(cx, cy, D / 2))
    parts.append('<circle cx="%g" cy="%g" r="%g" fill="none"'
                 ' stroke="#1A1A18" stroke-width="%g"/>'
                 % (cx, cy, R1, THICK))
    s_y = cy + R + DIM_0
    parts.append(ln(cx - S / 2 * MM, cy + R + 4, cx - S / 2 * MM, s_y, THIN))
    parts.append(ln(cx + S / 2 * MM, cy + R + 4, cx + S / 2 * MM, s_y, THIN))
    parts.append(ln(cx - S / 2 * MM, s_y, cx + S / 2 * MM, s_y, THIN, arrows=True))
    parts.append(txt(cx, s_y - 5, "S"))
    d_x = cx + R + DIM_0
    parts.append(ln(cx + R + 4, cy - R, d_x, cy - R, THIN))
    parts.append(ln(cx + R + 4, cy + R, d_x, cy + R, THIN))
    parts.append(ln(d_x, cy - R, d_x, cy + R, THIN, arrows=True))
    parts.append(txt(d_x - 6, cy, "D", rot=-90))
    return "".join(parts)


# ============================================================================
# Наглядное изображение (msgId 1001 pictorial, §9 эталон rotate(-35))
# ============================================================================

# М20 reference ISO constants (Даня §9 эталон, scaled by k = d/20)
M20_SHAFT_PATH_D = "M 20,-30 L 226,-30 L 233,-24 A 10.5 24 0 0 1 233,24 L 226,30 L 20,30 Z"
M20_THREAD_BX = 118
M20_THREAD_LINES = [(x, -29, x - 6, 29) for x in range(126, 226, 9)]
M20_HEAD_BACK = "-20,-25 0,-50 28,-50 48,-25 48,25 28,50 0,50 -20,25"
M20_HEAD_FRONT = "0,-50 20,-25 20,25 0,50 -20,25 -20,-25"
M20_HEAD_EDGES = [(20, -25, 48, -25), (20, 25, 48, 25)]
M20_CHAMFER = (19, 42.8)

# Опорные точки выносок М20 относительно центра головки (695, 318) —
# (text_x, text_y), (arrow_start_x, arrow_start_y), (arrow_end_x, arrow_end_y).
M20_LEADERS = {
    "Резьба":   {"text": (884, 112), "arrow_start": (890, 120), "arrow_end": (820, 196)},
    "Стержень": {"text": (856, 342), "arrow_start": (860, 344), "arrow_end": (788, 298)},
    "Фаска":    {"text": (556, 262), "arrow_start": (600, 270), "arrow_end": (660, 295)},
    "Головка":  {"text": (628, 412), "arrow_start": (668, 408), "arrow_end": (726, 357)},
}
M20_LEADER_OFFSETS = {
    name: {"text": (data["text"][0] - 695, data["text"][1] - 318),
           "arrow_start": (data["arrow_start"][0] - 695, data["arrow_start"][1] - 318),
           "arrow_end": (data["arrow_end"][0] - 695, data["arrow_end"][1] - 318)}
    for name, data in M20_LEADERS.items()
}


def bolt_iso_view(d, l, l0, S, D, h, c, ox=0, oy=0):
    """
    Аксонометрия v5 (msgId 1009) — копия эталона М20 §9 с масштабом k = d/20.

    Не конструируется с нуля — каждая координата берётся из эталона и
    умножается на k. ПОРЯДОК СЛОЁВ критичен (vt.16):
      1. Стержень (замкнутый, белая заливка = перекрытие с головкой)
      2. Резьба (толстая граница + тонкие наклонные шаг 9·k)
      3. Головка (восьмиугольник + шестигранник + 2 ребра)
      4. Окружность фаски (эллипс)
    """
    k = d / 20.0

    def s(x): return x * k

    parts = []

    # 1. СТЕРЖЕНЬ — закрытый path с белой заливкой
    shaft_d = ("M %g,%g L %g,%g L %g,%g A %g %g 0 0 1 %g,%g L %g,%g L %g,%g Z"
               % (s(20), s(-30),
                  s(226), s(-30),
                  s(233), s(-24),
                  s(10.5), s(24),
                  s(233), s(24),
                  s(226), s(30),
                  s(20), s(30)))
    parts.append(
        '<path d="%s" fill="#FFFFFF" stroke="#1A1A18" stroke-width="2.4"/>'
        % shaft_d)

    # 2. РЕЗЬБА — толстая граница + тонкие наклонные
    parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#1A1A18"'
                 ' stroke-width="2.4"/>'
                 % (k * M20_THREAD_BX, k * -30, k * M20_THREAD_BX, k * 30))
    for x1, y1, x2, y2 in M20_THREAD_LINES:
        parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#1A1A18"'
                     ' stroke-width="1"/>'
                     % (k * x1, k * y1, k * x2, k * y2))

    # 3a. Задний силуэт (восьмиугольник) — белая заливка
    head_back = " ".join("%g,%g" % (k * float(p.split(",")[0]),
                                      k * float(p.split(",")[1]))
                          for p in M20_HEAD_BACK.split())
    parts.append('<polygon points="%s" fill="#FFFFFF" stroke="#1A1A18"'
                 ' stroke-width="2.4"/>' % head_back)

    # 3b. Передний шестигранник — контур без заливки
    head_front = " ".join("%g,%g" % (k * float(p.split(",")[0]),
                                       k * float(p.split(",")[1]))
                           for p in M20_HEAD_FRONT.split())
    parts.append('<polygon points="%s" fill="none" stroke="#1A1A18"'
                 ' stroke-width="2.4"/>' % head_front)

    # 3c. Рёбра
    for x1, y1, x2, y2 in M20_HEAD_EDGES:
        parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#1A1A18"'
                     ' stroke-width="2.4"/>'
                     % (k * x1, k * y1, k * x2, k * y2))

    # 4. Эллиптическая окружность фаски на передней грани
    parts.append('<ellipse cx="0" cy="0" rx="%g" ry="%g" fill="none"'
                 ' stroke="#1A1A18" stroke-width="1"/>'
                 % (k * M20_CHAMFER[0], k * M20_CHAMFER[1]))

    return '<g transform="translate(%g,%g) rotate(%g)">%s</g>' % (
        ox, oy, ISO_ANGLE, "".join(parts))


def iso_leaders(d, head_cx, head_cy, text_size=16):
    """4 выноски в абсолютных координатах листа, scaled by k=d/20."""
    k = d / 20.0
    parts = []
    for name, off in M20_LEADER_OFFSETS.items():
        tx = head_cx + off["text"][0] * k
        ty = head_cy + off["text"][1] * k
        asx = head_cx + off["arrow_start"][0] * k
        asy = head_cy + off["arrow_start"][1] * k
        aex = head_cx + off["arrow_end"][0] * k
        aey = head_cy + off["arrow_end"][1] * k
        parts.append(leader(tx, ty, aex, aey, name,
                            text_size=text_size * k,
                            line_start=(asx, asy)))
    return "".join(parts)


# ============================================================================
# Выноски (вне повёрнутой группы)
# ============================================================================

def leader(x_text, y_text, x_arr, y_arr, label, text_size=16, line_start=None):
    """Leader line: italic text + underline + arrow line to element.

    text position is INDEPENDENT from arrow-start position (М20 ref has
    text at (884,112) and arrow line starts at (890,120) — separated by
    a short horizontal segment that visually anchors the text to the line).
    """
    parts = []
    # Текст — курсив italic
    parts.append('<text x="%g" y="%g" text-anchor="middle" fill="#1A1A18"'
                 ' font-family="\'PT Sans\'" font-style="italic" font-size="%g">%s</text>'
                 % (x_text, y_text, text_size, label))
    # Подчёркивание — тонкая линия под текстом
    text_w = len(label) * text_size * 0.55  # примерная ширина
    parts.append(ln(x_text - text_w / 2, y_text + 5,
                    x_text + text_w / 2, y_text + 5, THIN))
    # Линия со стрелкой остриём на элемент — от (line_start) до (x_arr, y_arr)
    if line_start is None:
        line_start = (x_text, y_text + 8)
    parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#1A1A18"'
                 ' stroke-width="1" marker-end="url(#ar)"/>'
                 % (line_start[0], line_start[1], x_arr, y_arr))
    return "".join(parts)


# ============================================================================
# Чертёж — болт М8×40 с тремя изображениями
# ============================================================================
if __name__ == "__main__":
    d, l, l0 = 8, 40, 22
    S, D, D1, h, c = 13, 14.2, 13 * 0.95, 5.5, 1.2

    front = bolt_front_view(d, l, l0, S, D, h, c)

    R = D / 2 * MM
    side_cx = l * MM + h * MM + 100
    side = bolt_side_view(S, D, D1, side_cx, 0)

    # Iso view — place it to the right
    iso_ox = side_cx + R + 60
    iso_oy = 70
    iso = bolt_iso_view(d, l, l0, S, D, h, c, iso_ox, iso_oy)

    # Выноски в абсолютных координатах (М20 §9 эталон, scaled by k=d/20).
    # Центр головки в iso-local = (0,0). После translate(iso_ox, iso_oy)
    # центр головки = (iso_ox, iso_oy). Смещения выносок определены
    # относительно центра головки в М20 reference.
    leaders = iso_leaders(d, iso_ox, iso_oy, text_size=16)

    cf_head = h * MM * 0.155
    pad = 45
    vb_x = -cf_head - pad
    vb_y = -D / 2 * MM - 60  # extra room for ≈30° + c×45°
    vb_w = iso_ox + 320 - vb_x   # include iso + leaders (М20 offsets max ~250)
    vb_h = (l * MM + h * MM) - vb_y + 80 + 30  # l below + iso depth + caption

    svg_body = ('%s'
                '<g transform="translate(0,0)">%s</g>'
                '<g transform="translate(0,0)">%s</g>'
                '%s'
                '%s'
                % (DEFS, front, side, iso, leaders))

    out = "/data/.openclaw/workspace/site/assets/img/bolt-m8-nacherti.svg"
    open(out, "w", encoding="utf-8").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%g %g %g %g">%s</svg>'
                                            % (vb_x, vb_y, vb_w, vb_h, svg_body))
    print("Wrote %s (%.1f KB)" % (out, len(svg_body) / 1024))


# ============================================================================
# Чертёж — болт М10×50
# ============================================================================
if __name__ == "__main__":
    d, l, l0 = 10, 50, 26
    S, D, D1, h, c = 17, 18.7, 17 * 0.95, 7, 1.5

    front = bolt_front_view(d, l, l0, S, D, h, c)

    R = D / 2 * MM
    side_cx = l * MM + h * MM + 100
    side = bolt_side_view(S, D, D1, side_cx, 0)

    iso_ox = side_cx + R + 60
    iso_oy = 70
    iso = bolt_iso_view(d, l, l0, S, D, h, c, iso_ox, iso_oy)

    # Выноски в абсолютных координатах (М20 §9 эталон, scaled by k=d/20).
    leaders = iso_leaders(d, iso_ox, iso_oy, text_size=16)

    cf_head = h * MM * 0.155
    pad = 45
    vb_x = -cf_head - pad
    vb_y = -D / 2 * MM - 60
    vb_w = iso_ox + 320 - vb_x
    vb_h = (l * MM + h * MM) - vb_y + 80 + 30

    svg_body = ('%s'
                '<g transform="translate(0,0)">%s</g>'
                '<g transform="translate(0,0)">%s</g>'
                '%s'
                '%s'
                '%s'
                % (DEFS, front, side, iso, leaders,
                   txt(vb_x + vb_w / 2, vb_y + vb_h - 12, "Рис. 52", size=15)))

    out = "/data/.openclaw/workspace/site/assets/img/bolt-m10-nacherti.svg"
    open(out, "w", encoding="utf-8").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%g %g %g %g">%s</svg>'
                                            % (vb_x, vb_y, vb_w, vb_h, svg_body))
    print("Wrote %s (%.1f KB)" % (out, len(svg_body) / 1024))
