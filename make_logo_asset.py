#!/usr/bin/env python3
"""Prepare the FindWell logo lockup for the site.

    python3 make_logo_asset.py FindWell.png

The supplied file sits on a soft grey-green gradient rather than transparency.
A flat-colour key would leave a halo, so this keeps per-pixel colour and
derives alpha from how far each pixel is from the local background, which is
estimated with a heavy blur of the image itself.

Writes public/assets/img/logo.png (trimmed, transparent) plus 400/800/1200px
wide copies as PNG and WebP.
"""
import sys, os
from PIL import Image, ImageFilter

if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
    sys.exit("Usage: python3 make_logo_asset.py path/to/logo.png")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public/assets/img")
os.makedirs(out, exist_ok=True)

im = Image.open(sys.argv[1]).convert("RGB")
w, h = im.size

# The backdrop is a pale, almost neutral gradient. The artwork is either dark
# (the wordmark) or saturated (the leaves), so key on those two properties
# rather than on a single background colour — that avoids a halo where the
# gradient shifts.
px = im.load()
alpha = Image.new("L", (w, h), 0)
apx = alpha.load()

for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        mx, mn = max(r, g, b), min(r, g, b)
        sat = mx - mn                       # 0 for neutral grey
        lum = (r * 299 + g * 587 + b * 114) // 1000

        # The backdrop carries a faint green tint (saturation up to ~13) and
        # sits above luminance 200, so the thresholds clear it comfortably.
        sat_score = (sat - 17) / 13.0       # saturated -> opaque
        dark_score = (198 - lum) / 26.0     # dark -> opaque
        score = max(sat_score, dark_score)
        apx[x, y] = 0 if score <= 0 else (255 if score >= 1 else int(255 * score))

logo = im.convert("RGBA")
logo.putalpha(alpha)

bbox = logo.getbbox()
if bbox:
    logo = logo.crop(bbox)
print(f"trimmed to {logo.size[0]}x{logo.size[1]}"
      f"  (aspect {logo.size[0] / logo.size[1]:.2f}:1)")

logo.save(f"{out}/logo.png", "PNG", optimize=True)
print(f"full-size png: {os.path.getsize(out + '/logo.png') // 1024} KB")
for wpx in (400, 800, 1200):
    if wpx > logo.size[0] * 1.5:
        continue
    scaled = logo.resize((wpx, round(wpx * logo.size[1] / logo.size[0])), Image.LANCZOS)
    # Quantise: a flat-colour logo needs nothing like 24-bit, and this cuts
    # the file by roughly 75%.
    q = scaled.quantize(colors=192, method=Image.FASTOCTREE, dither=Image.NONE)
    q.save(f"{out}/logo-{wpx}.png", "PNG", optimize=True)
    scaled.save(f"{out}/logo-{wpx}.webp", "WEBP", quality=90, method=6)
    print(f"wrote logo-{wpx}.png / .webp")
print("wrote logo.png (full size, transparent)")
