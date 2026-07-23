#!/usr/bin/env python3
"""
self_correct.py — петля самокоррекции для чертежей болтов.

Алгоритм (Track 5):
  1. Базовая генерация eskd.py (есть)
  2. Перцептуальная оценка (perceptual_check.py — есть)
  3. Мутации параметров в пространстве поиска:
     - Толщины штрихов {1, 2.4} ± 0.2
     - Размерные отступы DIM_0 = 30 ± 5, DIM_D = 21 ± 3
     - Угол фаски c (от 0.5·d_standard до 1.5·d_standard)
     - Угол ≈30° константа в iso (но фиксировано по эталону — пропуск)
     - k сжатия iso-головки (от 0.40 до 0.50, default 0.45)
  4. Селекция: оставить top-2 мутантов, повторить N поколений

Запуск:
  python3 self_correct.py --target m8-x40 --generations 5 --population 4
"""
import sys
import os
import math
import random
import subprocess
import argparse
from pathlib import Path
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity as ssim
import imagehash

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
import eskd
import gost_7798_table as gost


OUT_DIR = SCRIPT_DIR.parent / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def render_bolt(d, l, params):
    """Генерация SVG + PNG для болта с изменёнными параметрами."""
    l0 = params["l0"]
    S = params["S"]
    D = params["D"]
    h = params["h"]
    c = params["c"]
    k_iso = params.get("k_iso", 0.45)
    dim_0 = params.get("dim_0", 30)
    dim_d = params.get("dim_d", 21)

    # Временно подменяем константы в модуле
    eskd.DIM_0 = dim_0
    eskd.DIM_D = dim_d
    eskd.ISO_K = k_iso

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

    slug = f"mutant-{d}-{l}-{random.randint(0, 99999):05d}"
    svg_path = OUT_DIR / f"{slug}.svg"
    png_path = OUT_DIR / f"{slug}.png"
    svg_path.write_text(svg, encoding="utf-8")
    import cairosvg
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=2000)
    return svg_path, png_path


def perceptual_score(png_path, ref_png_path):
    """SSIM + phash hamming → числовой score (чем ниже, тем лучше)."""
    draft = Image.open(png_path).convert("L").resize((512, 512), Image.LANCZOS)
    ref = Image.open(ref_png_path).convert("L").resize((512, 512), Image.LANCZOS)
    draft_arr = np.asarray(draft)
    ref_arr = np.asarray(ref)
    s = ssim(draft_arr, ref_arr, data_range=255)
    h = (imagehash.phash(draft) - imagehash.phash(ref))
    # Низкий score = лучше. SSIM invert: 1 - ssim, hamming already inverted
    return (1 - s) + (h / 64.0) * 0.5


def mutate_params(base, mutation_rate=0.3):
    """Мутация параметров в небольших пределах."""
    new = dict(base)
    if random.random() < mutation_rate:
        new["c"] = round(base["c"] * random.uniform(0.85, 1.15), 2)
    if random.random() < mutation_rate:
        new["dim_0"] = max(20, min(40, base["dim_0"] + random.choice([-3, 3])))
    if random.random() < mutation_rate:
        new["dim_d"] = max(15, min(27, base["dim_d"] + random.choice([-2, 2])))
    if random.random() < mutation_rate:
        new["k_iso"] = round(max(0.38, min(0.52, base["k_iso"] + random.uniform(-0.03, 0.03))), 3)
    return new


def validate_svg(svg_path):
    """eskd_check проходит? Возвращает bool."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "eskd_check.py"), str(svg_path)],
        capture_output=True, text=True
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="m8-x40", help="Целевой размер (m{d}-x{l})")
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--population", type=int, default=4)
    parser.add_argument("--ref-svg", default=None, help="Эталонный SVG для сравнения")
    args = parser.parse_args()

    # Parse target
    import re
    m = re.match(r"m(\d+)-x(\d+)", args.target)
    if not m:
        print(f"Bad target format: {args.target}")
        sys.exit(1)
    d, l = int(m.group(1)), int(m.group(2))

    base = gost.get_params(d, l)
    base["dim_0"] = 30
    base["dim_d"] = 21
    base["k_iso"] = 0.45

    # Reference PNG: same size, default params
    ref_png = OUT_DIR / f"bolt-m{d}-x{l}-reference.png"
    if not ref_png.exists():
        print(f"Reference PNG missing: {ref_png}. Run generate_references.py first.")
        sys.exit(1)

    print(f"Self-correction for М{d}×{l}")
    print(f"Reference: {ref_png}")
    print(f"Generations: {args.generations}, Population: {args.population}")

    # Генерим базовую популяцию
    population = [dict(base)]  # baseline (no mutation)
    for _ in range(args.population - 1):
        population.append(mutate_params(base))

    best_overall = None
    best_score = float("inf")

    for gen in range(args.generations):
        scored = []
        for i, p in enumerate(population):
            svg_path, png_path = render_bolt(d, l, p)
            eskd_ok = validate_svg(svg_path)
            score = perceptual_score(png_path, ref_png) if eskd_ok else 100
            scored.append((score, p, eskd_ok, svg_path, png_path))
            status = "✓" if eskd_ok else "✗"
            print(f"  gen={gen} ind={i} score={score:.4f} eskd={status} c={p['c']} d0={p['dim_0']} dd={p['dim_d']} k={p['k_iso']}")

        scored.sort(key=lambda x: x[0])
        best = scored[0]
        if best[0] < best_score:
            best_score = best[0]
            best_overall = best
        print(f"  → gen {gen} best: score={best[0]:.4f} (c={best[1]['c']}, d0={best[1]['dim_0']}, dd={best[1]['dim_d']}, k={best[1]['k_iso']})")

        # Селекция: top-2 → мутируются в следующее поколение
        top2 = [scored[0][1], scored[1][1]] if len(scored) > 1 else [scored[0][1]]
        new_pop = []
        for parent in top2:
            new_pop.append(parent)  # elitism
            for _ in range(args.population // len(top2) - 1):
                new_pop.append(mutate_params(parent))
        # Если популяция короче — добиваем мутациями лучшего
        while len(new_pop) < args.population:
            new_pop.append(mutate_params(top2[0]))
        population = new_pop[:args.population]

    if best_overall:
        print(f"\n=== Best after {args.generations} generations ===")
        print(f"Score: {best_overall[0]:.4f}")
        print(f"Params: c={best_overall[1]['c']} d0={best_overall[1]['dim_0']} dd={best_overall[1]['dim_d']} k_iso={best_overall[1]['k_iso']}")
        print(f"SVG: {best_overall[3]}")
        print(f"PNG: {best_overall[4]}")
        return best_overall[3], best_overall[4]
    return None, None


if __name__ == "__main__":
    main()