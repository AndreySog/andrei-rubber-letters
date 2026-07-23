#!/usr/bin/env python3
"""
generate_references.py — batch-генерирует эталонные SVG + PNG для всех болтов ГОСТ 7798-70.

Для каждого (d, l) из gost_7798_table:
  - Вызывает bolt_front_view, bolt_side_view, bolt_iso_view
  - Создаёт SVG в /data/.openclaw/workspace/site/assets/img/bolt-m{d}-x{l}-reference.svg
  - Рендерит PNG через cairosvg для перцептуального сравнения
  - Проверяет eskd_check (C + STRUCT + NUM + ISO)

Результат: эталонная база для perceptual_check (Track 1) + автогенерация новых болтов.
"""
import sys
import os
import math
import yaml
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
import eskd
import gost_7798_table as gost


OUT_DIR = SCRIPT_DIR.parent / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_one(d, l):
    """Генерация одного болта (d, l). Возвращает dict с путями."""
    p = gost.get_params(d, l)
    l0 = p["l0"]
    S = p["S"]
    D = p["D"]
    h = p["h"]
    c = p["c"]

    front = eskd.bolt_front_view(d, l, l0, S, D, h, c)
    R = D / 2 * eskd.MM
    side_cx = l * eskd.MM + h * eskd.MM + 100
    side = eskd.bolt_side_view(S, D, D * 0.95, side_cx, 0)
    iso_ox = side_cx + R + 60
    iso_oy = 70
    iso = eskd.bolt_iso_view(d, l, l0, S, D, h, c, iso_ox, iso_oy)
    leaders = eskd.iso_leaders(d, iso_ox, iso_oy, text_size=16)

    cf_head = h * eskd.MM * 0.155
    pad = 45
    vb_x = -cf_head - pad
    vb_y = -D / 2 * eskd.MM - 60
    vb_w = iso_ox + 320 - vb_x
    vb_h = (l * eskd.MM + h * eskd.MM) - vb_y + 80 + 30

    body = (f"{eskd.DEFS}"
            f"<g transform=\"translate(0,0)\">{front}</g>"
            f"<g transform=\"translate(0,0)\">{side}</g>"
            f"{iso}{leaders}"
            f"{eskd.txt(vb_x + vb_w / 2, vb_y + vb_h - 12, 'Рис.', size=15)}")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'viewBox="{vb_x} {vb_y} {vb_w} {vb_h}">{body}</svg>')

    slug = f"bolt-m{d}-x{l}-reference"
    svg_path = OUT_DIR / f"{slug}.svg"
    png_path = OUT_DIR / f"{slug}.png"
    svg_path.write_text(svg, encoding="utf-8")

    # Render PNG via cairosvg
    import cairosvg
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path),
                     output_width=2000)
    return {
        "d": d, "l": l,
        "l0": l0, "S": S, "D": D, "h": h, "c": c, "P": p["P"],
        "svg": str(svg_path), "png": str(png_path),
    }


def validate_one(svg_path):
    """Запуск eskd_check.py на одном SVG. Возвращает (passed, stdout)."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "eskd_check.py"), str(svg_path)],
        capture_output=True, text=True
    )
    return (result.returncode == 0, result.stdout)


def main():
    sizes = gost.all_sizes()
    print(f"Generating references for {len(sizes)} bolts from ГОСТ 7798-70...")
    catalog = []
    failures = []
    for d, l in sizes:
        try:
            meta = generate_one(d, l)
            ok, _ = validate_one(meta["svg"])
            meta["eskd_check"] = "PASS" if ok else "FAIL"
            catalog.append(meta)
            status = "✓" if ok else "✗"
            print(f"  {status} М{d}×{l}")
            if not ok:
                failures.append((d, l, meta["svg"]))
        except Exception as e:
            print(f"  ✗ М{d}×{l}: ERROR {e}")
            failures.append((d, l, str(e)))

    # Save catalog
    cat_path = SCRIPT_DIR / "bolt_catalog.yaml"
    with open(cat_path, "w", encoding="utf-8") as f:
        yaml.dump({"catalog": catalog,
                   "total": len(catalog),
                   "passed": sum(1 for c in catalog if c["eskd_check"] == "PASS"),
                   "failed": sum(1 for c in catalog if c["eskd_check"] == "FAIL")},
                  f, default_flow_style=False, allow_unicode=True)
    print(f"\nCatalog saved to {cat_path}")
    print(f"Total: {len(catalog)}, passed: {len(catalog) - len(failures)}, failed: {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())