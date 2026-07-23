#!/usr/bin/env python3
"""
perceptual_check.py — перцептуальная валидация чертежа болта против эталона.

Использует три метрики:
  1. SSIM (Structural Similarity Index) — skimage
  2. Perceptual hash (phash) — imagehash
  3. Хэмминг расстояние между фингерпринтами

Аргументы:
  python3 perceptual_check.py <draft.png> <reference.png>

Выход:
  SSIM: <score> (0..1, выше = лучше)
  phash: <hamming> (0..64, ниже = лучше)
  Pass thresholds: SSIM >= 0.75, hamming <= 12
"""
import sys
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import imagehash


def load_gray(path, size=512):
    """Загрузить PNG в оттенках серого нужного размера."""
    img = Image.open(path).convert("L")
    img = img.resize((size, size), Image.LANCZOS)
    return np.asarray(img), img


def main():
    if len(sys.argv) != 3:
        print("Usage: perceptual_check.py <draft.png> <reference.png>")
        sys.exit(1)
    draft_path, ref_path = sys.argv[1], sys.argv[2]

    draft_arr, draft_pil = load_gray(draft_path)
    ref_arr, ref_pil = load_gray(ref_path)

    # 1. SSIM
    ssim_score = ssim(draft_arr, ref_arr, data_range=255)
    print(f"SSIM: {ssim_score:.4f}  ({'PASS' if ssim_score >= 0.75 else 'FAIL'})")

    # 2. Perceptual hash (phash)
    draft_hash = imagehash.phash(draft_pil)
    ref_hash = imagehash.phash(ref_pil)
    hamming = (draft_hash - ref_hash)
    print(f"phash hamming: {hamming}  ({'PASS' if hamming <= 12 else 'FAIL'})")
    print(f"  draft phash:  {draft_hash}")
    print(f"  reference:    {ref_hash}")

    # 3. Difference map (для отладки)
    diff_arr = np.abs(draft_arr.astype(int) - ref_arr.astype(int)).astype(np.uint8)
    diff_pil = Image.fromarray(diff_arr)
    diff_pil.save("/tmp/perceptual_diff.png")
    print(f"  diff saved to /tmp/perceptual_diff.png (mean abs diff: {diff_arr.mean():.2f})")

    # Вердикт
    if ssim_score >= 0.75 and hamming <= 12:
        print("✓ PERCEPTUAL: passes both thresholds")
        sys.exit(0)
    else:
        print("✗ PERCEPTUAL: fails one or both thresholds")
        sys.exit(1)


if __name__ == "__main__":
    main()