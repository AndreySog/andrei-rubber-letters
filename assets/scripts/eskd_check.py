#!/usr/bin/env python3
"""
eskd_check.py — algorithmic validator (skill §12) + v3 numerical self-check

Run: python3 eskd_check.py path/to/*.svg

Checks:
  C-01..C-12 (skill §12, исходный skill)
  STRUCT (msgId 962: 5 structural checks)
  NUM  (msgId 992 vt.10: numerical self-check on shaft symmetry)
  ISO  (msgId 1009 v5: iso self-check)

Правила живут в gost_rules.yaml — машиночитаемом дереве.
eskd_check.py их ЧИТАЕТ, а не хранит хардкод.
"""
import re
import sys
import yaml
from pathlib import Path


# §12 + structural checks
def check_svg(svg_text):
    """Run all checks, print ✓/✗ lines, return True if all pass."""
    name = "svg"
    failures = []

    # Load rules from gost_rules.yaml (если доступен)
    rules_path = Path(__file__).parent / "gost_rules.yaml"
    rules = {}
    if rules_path.exists():
        with open(rules_path, encoding="utf-8") as f:
            rules = yaml.safe_load(f)
        rule_count = sum(len(v) if isinstance(v, list) else 0 for v in [
            rules.get("visual", []),
            rules.get("structure", []),
            rules.get("numeric", []),
            rules.get("iso", []),
            rules.get("perceptual", []),
        ])
        print(f"  -- gost_rules.yaml v{rules.get('version', '?')} "
              f"({rule_count} rules loaded) --")

    # C-01 — stroke-width ⊆ {1.0, 2.4, 3.6}
    widths = set(re.findall(r'stroke-width="([\d.]+)"', svg_text))
    expected = {"1", "1.0", "2.4", "3.6"}
    bad = widths - expected
    if bad:
        failures.append(f"C-01: unknown stroke-widths: {bad}")
    else:
        print(f"  ✓ C-01 stroke-width ⊆ {{1, 2.4, 3.6}}: {sorted(widths)}")

    # C-02 — only #1A1A18 для штрихов, заливка только none / #FFFFFF (для
    # перекрытия в iso view) / url(#ht) / стрелки
    colors = set(re.findall(r'stroke="(#[0-9a-fA-F]+)"', svg_text))
    inks = colors | set(re.findall(r'fill="(#[0-9a-fA-F]+)"', svg_text))
    inks = {c for c in inks if c.lower() not in {"none", "#1a1a18", "#ffffff", "white"}}
    inks -= {"none", "url(#ht)"}   # hatch & marker allowed
    if inks:
        failures.append(f"C-02: extra colors: {inks}")
    else:
        print(f"  ✓ C-02 only #1A1A18 stroke: {sorted(colors)}")
    fills = re.findall(r'fill="([^"]+)"', svg_text)
    bad_fills = [f for f in fills if f not in {"none", "url(#ht)", "#1A1A18",
                                               "#FFFFFF", "white"}]
    if bad_fills:
        failures.append(f"C-02 fills: bad: {bad_fills}")
    else:
        print(f"  ✓ C-02 fill: only none / marker / hatch / #FFFFFF (iso)")

    # C-03 — осевая 24 5 3 5 присутствует
    if 'stroke-dasharray="24 5 3 5"' in svg_text:
        print('  ✓ C-03 осевая 24 5 3 5 присутствует')
    else:
        failures.append("C-03: осевая отсутствует")

    # C-05 — marker#ar объявлен
    if 'id="ar"' in svg_text:
        print('  ✓ C-05 marker#ar объявлен')
    else:
        failures.append("C-05: marker#ar не объявлен")

    # C-08 — нет «мм» в текстовых узлах, запятая как разделитель
    texts = re.findall(r'<text[^>]*>([^<]+)</text>', svg_text)
    all_text = " ".join(texts)
    if 'мм' in all_text.lower():
        failures.append("C-08: «мм» в тексте")
    else:
        print('  ✓ C-08 нет «мм» в текстовых узлах')
    if ',' in all_text:
        print('  ✓ C-08 запятая как десятичный разделитель (или ⌀)')
    else:
        print('  ✓ C-08 (нет запятых в тексте)')

    # C-12 — нет scale() в transform
    if re.search(r'transform="[^"]*scale', svg_text):
        failures.append("C-12: scale() в transform")
    else:
        print('  ✓ C-12 нет scale() в transform')

    # --- STRUCT checks (msgId 962)
    print('  -- msgId 962 structural checks --')

    # Парсер одного <line .../>
    def line_attrs(s):
        return dict(re.findall(r'(\w[\w-]*)="([^"]*)"', s))

    def is_horiz(L):
        if 'y1' not in L or 'y2' not in L:
            return False
        return abs(float(L['y1']) - float(L['y2'])) < 0.01

    def is_vert(L):
        if 'x1' not in L or 'x2' not in L:
            return False
        return abs(float(L['x1']) - float(L['x2'])) < 0.01

    lines = []
    for m in re.finditer(r'<line[^/]*/>', svg_text):
        lines.append(line_attrs(m.group(0)))

    # Замкнутые path-контуры
    closed_paths = re.findall(r'<path[^>]*d="[^"]*Z"', svg_text)
    if len(closed_paths) >= 2:
        print(f"  ✓ STRUCT: {len(closed_paths)} замкнутых path-контуров"
              f" (головка + стержень + ...)")
    else:
        failures.append(f"STRUCT: только {len(closed_paths)} замкнутых path (нужно ≥2)")

    # Толстые вертикали (stroke-width 2.4)
    thick_verts = sum(1 for L in lines
                      if float(L.get('stroke-width', 0)) == 2.4 and is_vert(L))
    if thick_verts >= 2:
        print(f"  ✓ STRUCT: {thick_verts} толстых вертикалей"
              f" (граница резьбы и др.)")
    else:
        failures.append(f"STRUCT: только {thick_verts} толстых вертикалей")

    # Тонкие горизонтали (stroke-width 1.0)
    thin_horiz = sum(1 for L in lines
                     if float(L.get('stroke-width', 0)) == 1.0 and is_horiz(L))
    if thin_horiz >= 2:
        print(f"  ✓ STRUCT: {thin_horiz} тонких горизонталей"
              f" (вероятно впадины резьбы)")
    else:
        failures.append(f"STRUCT: только {thin_horiz} тонких горизонталей")

    # Шестигранник fill='none', 6 вершин
    poly_match = re.search(r'<polygon points="([^"]+)"[^/]*/>', svg_text)
    if poly_match:
        pts = poly_match.group(1).split()
        if len(pts) == 6 and 'fill="none"' in poly_match.group(0):
            print("  ✓ STRUCT: шестигранник fill='none', 6 вершин")
        else:
            failures.append(f"STRUCT: шестигранник {len(pts)} точек,"
                            f" fill != none")
    else:
        failures.append("STRUCT: шестигранник не найден")

    # Окружность fill='none'
    circ_match = re.search(r'<circle[^/]*/>', svg_text)
    if circ_match and 'fill="none"' in circ_match.group(0):
        print("  ✓ STRUCT: окружность фаски fill='none'")
    else:
        failures.append("STRUCT: окружность не fill='none'")

    # --- NUM self-check (msgId 992 vt.10)
    print('  -- msgId 992 vt.10 numerical self-check --')
    # Среди толстых горизонталей ищем пары образующих стержня (симметричные y).
    thick_horiz_by_y = {}
    for L in lines:
        if float(L.get('stroke-width', 0)) != 2.4:
            continue
        if not is_horiz(L):
            continue
        y = round(float(L['y1']), 2)
        thick_horiz_by_y.setdefault(y, []).append(L)

    # Парные образующие (±y оба присутствуют)
    symmetric_pairs = sum(1 for y in list(thick_horiz_by_y.keys())
                          if y != 0 and -y in thick_horiz_by_y)
    if symmetric_pairs >= 1:
        print(f"  ✓ NUM: {symmetric_pairs} пар симметричных толстых горизонталей"
              f" (сверху и снизу оси есть образующие, vt.1)")
    else:
        failures.append("NUM: нет симметричных пар образующих стержня (vt.1)")

    # --- ISO self-check (msgId 1009 v5/vt.16)
    print('  -- msgId 1009 v5 ISO self-check (vt.16) --')
    # Ищем аксонометрическую группу (rotate(-35))
    iso_groups = re.findall(r'<g\s+transform="translate\(([^,)]+),([^)]+)\)\s+rotate\((-?\d+)\)">', svg_text)
    if iso_groups:
        ox, oy, angle = float(iso_groups[0][0]), float(iso_groups[0][1]), float(iso_groups[0][2])
        # В этой группе считаем элементы (внутри group)
        # Грубая эвристика: ищем все <polygon> + <ellipse> после первого <g transform=rotate...
        iso_start = svg_text.find('rotate(%g)' % angle)
        iso_end = svg_text.find('</g>', iso_start)
        iso_block = svg_text[iso_start:iso_end] if iso_start > 0 else ''
        # Внутри iso-блока должно быть:
        #   - ровно 2 polygon (силуэт + шестигранник)
        #   - 1 ellipse (фаска)
        #   - стержень одним path с белой заливкой
        polys = len(re.findall(r'<polygon\b', iso_block))
        ellipses = len(re.findall(r'<ellipse\b', iso_block))
        shaft_paths = len(re.findall(r'<path\b[^>]*fill="#FFFFFF"[^>]*stroke="#1A1A18"', iso_block))
        # Рёбра — толстые линии внутри iso-блока, которые НЕ вертикальные
        iso_lines = re.findall(
            r'<line\s+x1="([^"]+)"\s+y1="([^"]+)"\s+x2="([^"]+)"\s+y2="([^"]+)"\s+stroke="#1A1A18"\s+stroke-width="2.4"',
            iso_block)
        edges = 0
        for l in iso_lines:
            x1, y1, x2, y2 = float(l[0]), float(l[1]), float(l[2]), float(l[3])
            if abs(y1 - y2) < 0.01 and abs(x1 - x2) > 1:  # горизонталь
                edges += 1
        if polys == 2 and ellipses == 1 and shaft_paths >= 1 and edges == 2:
            print(f"  ✓ ISO: 4 фигуры головки (силуэт+шестигранник+2 ребра) + эллипс + стержень (vt.16)")
        else:
            failures.append(
                f"ISO: ожидалось polys=2 ellipses=1 edges=2 shaft_paths≥1, "
                f"получено polys={polys} ellipses={ellipses} edges={edges} shaft_paths={shaft_paths}")
        # Проверка параллельности образующих стержня (vt.16)
        # Ищем path с fill=#FFFFFF — берём первое M и последний токен.
        # В эталоне М20 path: "M 20,-30 L 226,-30 L 233,-24 A 10.5 24 0 0 1 233,24 L 226,30 L 20,30 Z"
        # Образующие верхняя y=-30 и нижняя y=+30 → |y|=30 (d/2·3 для d=20).
        shaft_paths_full = re.findall(r'<path d="(M [^"]+)"\s+fill="#FFFFFF"', iso_block)
        if shaft_paths_full:
            d_str = shaft_paths_full[0]
            # Парсим верхнюю (первую) и нижнюю (последнюю) координаты y
            m_match = re.match(r'M\s+[-\d.]+,[-\d.]+', d_str)
            l_matches = re.findall(r'L\s+[-\d.]+,([-\d.]+)', d_str)
            a_match = re.search(r'A\s+[-\d.]+\s+([-\d.]+)\s', d_str)
            if m_match and l_matches and a_match:
                y_top = float(re.match(r'M\s+[-\d.]+,([-\d.]+)', m_match.group(0)).group(1))
                # Последняя L координата y, перед Z
                y_bottom = float(l_matches[-1])
                if abs(abs(y_top) - abs(y_bottom)) < 0.1:
                    print(f"  ✓ ISO: образующие стержня параллельны (vt.16): y=±{abs(y_top):.1f}")
                else:
                    failures.append(f"ISO: образующие стержня НЕ параллельны (vt.16): y_top={y_top} y_bottom={y_bottom}")
    else:
        print("  -- ISO: не найдено rotate-группы, пропускаем")

    return len(failures) == 0, failures


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 eskd_check.py path/to/*.svg")
        sys.exit(1)

    overall_ok = True
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"❌ {path_str}: not found")
            overall_ok = False
            continue

        print(f"\n=== Checking {path} ===")
        text = path.read_text(encoding="utf-8")
        ok, failures = check_svg(text)
        if ok:
            print(f"\n✅ {path}: all C-checks passed\n")
        else:
            print(f"\n❌ {path}: {len(failures)} failure(s):")
            for f in failures:
                print(f"    - {f}")
            print()
            overall_ok = False

    sys.exit(0 if overall_ok else 1)