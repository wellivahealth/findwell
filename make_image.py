#!/usr/bin/env python3
"""Regenerate a responsive image set from a full-resolution source.

    python3 make_image.py photo.jpg hero          # 16:10, biased right
    python3 make_image.py photo.jpg about 2.0     # 2:1, centred

Writes 900/1400/2000px JPEG and WebP into public/assets/img as <name>-<width>.
Run build.py afterwards so the content hashes in the HTML update.
"""
import sys, os
from PIL import Image

if len(sys.argv) < 3 or not os.path.exists(sys.argv[1]):
    sys.exit("Usage: python3 make_image.py path/to/photo.jpg <name> [ratio] [bias]")

src_path, name = sys.argv[1], sys.argv[2]
RATIO = float(sys.argv[3]) if len(sys.argv) > 3 else (16 / 10)
BIAS  = float(sys.argv[4]) if len(sys.argv) > 4 else (0.58 if name == "hero" else 0.5)

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
    top = int((h - nh) * 0.12)
    base = src.crop((0, top, w, top + nh))

for px in (900, 1400, 2000):
    im = base.resize((px, round(px / RATIO)), Image.LANCZOS)
    im.save(f"{out}/{name}-{px}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
    im.save(f"{out}/{name}-{px}.webp", "WEBP", quality=78, method=6)
    print(f"wrote {name}-{px}.jpg / .webp")
