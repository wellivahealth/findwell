#!/usr/bin/env python3
"""Crop a photograph into a discipline tile image.

    python3 make_tile.py photo.jpg integrative 0.72 0.61 0.70

Arguments: source, output name, and optionally the centre of interest as
fractions of width and height (0.5 0.5 is the middle of the frame), and a zoom
factor where 1.0 is the widest possible crop and 0.7 crops in tighter. Tiles
are 4:3, so a wide photograph needs to be told where to look.

Writes 500/750/1000px JPEG and WebP to public/assets/img/disciplines/<name>-<w>.*

Then point that discipline's `img` at the stem in build.py:

    img="/assets/img/disciplines/integrative"
"""
import sys, os
from PIL import Image

if len(sys.argv) < 3 or not os.path.exists(sys.argv[1]):
    sys.exit("Usage: python3 make_tile.py photo.jpg <name> [centre-x] [centre-y] [zoom]")

src_path, name = sys.argv[1], sys.argv[2]
cx = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
cy = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
# Fraction of the largest possible 4:3 window. Below 1.0 crops in tighter,
# which is how you fill the tile with the subject instead of empty backdrop.
zoom = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0

RATIO = 4 / 3
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "public/assets/img/disciplines")
os.makedirs(out, exist_ok=True)

im = Image.open(src_path).convert("RGB")
w, h = im.size

if w / h > RATIO:                       # too wide: trim the sides
    nw, nh = int(h * RATIO), h
else:                                   # too tall: trim top and bottom
    nw, nh = w, int(w / RATIO)
nw, nh = int(nw * zoom), int(nh * zoom)

left = int(cx * w - nw / 2)
top = int(cy * h - nh / 2)
left = max(0, min(left, w - nw))        # keep the window inside the frame
top = max(0, min(top, h - nh))
base = im.crop((left, top, left + nw, top + nh))
print(f"cropped {w}x{h} -> {base.size[0]}x{base.size[1]} from ({left},{top})")

for px in (500, 750, 1000):
    scaled = base.resize((px, round(px / RATIO)), Image.LANCZOS)
    scaled.save(f"{out}/{name}-{px}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
    scaled.save(f"{out}/{name}-{px}.webp", "WEBP", quality=78, method=6)
    print(f"wrote disciplines/{name}-{px}.jpg / .webp")
print(f'set  img="/assets/img/disciplines/{name}"  then run build.py')
