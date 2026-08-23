#!/usr/bin/env python3
"""Regenerate the hero image sizes from a full-resolution source.

    python3 make_hero.py path/to/photo.jpg

Crops to 3:2 biased toward the right of the frame (where the practitioner
stands), then writes 900/1400/2000px JPEG and WebP into public/assets/img.
"""
import sys, os
from PIL import Image

src_path = sys.argv[1] if len(sys.argv) > 1 else None
if not src_path or not os.path.exists(src_path):
    sys.exit("Usage: python3 make_hero.py path/to/photo.jpg")

RATIO = 16 / 10
BIAS = 0.58          # 0 = keep left of frame, 1 = keep right
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public/assets/img")
os.makedirs(out, exist_ok=True)

src = Image.open(src_path).convert("RGB")
w, h = src.size
if w / h > RATIO:
    nw = int(h * RATIO)
    left = int((w - nw) * BIAS)
    base = src.crop((left, 0, left + nw, h))
else:
    nh = int(w / RATIO)
    top = int((h - nh) * 0.25)
    base = src.crop((0, top, w, top + nh))

for px in (900, 1400, 2000):
    im = base.resize((px, round(px / RATIO)), Image.LANCZOS)
    im.save(f"{out}/hero-{px}.jpg", "JPEG", quality=80, optimize=True, progressive=True)
    im.save(f"{out}/hero-{px}.webp", "WEBP", quality=76, method=6)
    print(f"wrote hero-{px}.jpg / .webp")
