#!/usr/bin/env python3
"""Build favicons from the logo, using only the graphic mark.

    python3 make_favicon.py findwell-logo-trans.png

The FindWell logo is a leaf mark followed by a wordmark. A favicon renders at
16-32px, where a wordmark is an unreadable smudge, so this keeps the mark only.

It trims transparent margins, then finds the vertical gap between the mark and
the type and cuts there. Check the preview it writes; if the split lands wrong,
pass an explicit fraction of the width to keep:

    python3 make_favicon.py logo.png 0.28

Outputs to public/assets/img/: favicon.png (512), favicon-180.png (Apple),
favicon-32.png, favicon.ico (16+32+48).
"""
import sys, os
from PIL import Image

if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
    sys.exit("Usage: python3 make_favicon.py path/to/logo.png [keep-fraction]")

src_path = sys.argv[1]
manual = float(sys.argv[2]) if len(sys.argv) > 2 else None
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public/assets/img")
os.makedirs(out, exist_ok=True)

im = Image.open(src_path).convert("RGBA")

# 1. trim fully transparent margins
bbox = im.getbbox()
if bbox:
    im = im.crop(bbox)
w, h = im.size
print(f"trimmed to {w}x{h}")

# 2. isolate the mark
#    An already-square file is taken to be the mark on its own — no split.
if manual is None and w and h and max(w, h) / min(w, h) < 1.3:
    print("source is already square — treating it as the mark, no split needed")
    cut = w
elif manual:
    cut = int(w * manual)
else:
    # Column occupancy: a column counts as "ink" if any pixel is meaningfully
    # opaque. The mark and the wordmark are separated by a run of empty columns.
    alpha = im.split()[-1]
    px = alpha.load()
    occupied = []
    for x in range(w):
        ink = False
        for y in range(0, h, max(1, h // 200)):     # sample rows for speed
            if px[x, y] > 40:
                ink = True
                break
        occupied.append(ink)

    # find the first gap of empty columns at least 2% of the width, after the
    # mark has started
    min_gap = max(4, int(w * 0.02))
    cut, run, started = 0, 0, False
    for x, ink in enumerate(occupied):
        if ink:
            started = True
            run = 0
        elif started:
            run += 1
            if run >= min_gap:
                cut = x - run
                break
    if not cut or cut < w * 0.05:
        cut = int(w * 0.25)
        print("! could not find a clean split, falling back to the left 25%")

mark = im.crop((0, 0, cut, h))
bbox = mark.getbbox()
if bbox:
    mark = mark.crop(bbox)
print(f"mark is {mark.size[0]}x{mark.size[1]} (cut at {cut}px of {w})")

# 2b. If the file has a flat light background rather than transparency,
#     lift it out so the icon sits cleanly on any tab colour.
if mark.getextrema()[3][0] == 255:            # fully opaque everywhere
    px = mark.convert("RGBA")
    w2, h2 = px.size
    corners = [px.getpixel(c) for c in ((0, 0), (w2 - 1, 0), (0, h2 - 1), (w2 - 1, h2 - 1))]
    avg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    if min(avg) > 200:                        # a pale background
        data = []
        for r, g, b, a in px.getdata():
            dist = max(abs(r - avg[0]), abs(g - avg[1]), abs(b - avg[2]))
            if dist < 12:
                data.append((r, g, b, 0))
            elif dist < 34:                   # feather the edge, no halo
                data.append((r, g, b, int(255 * (dist - 12) / 22)))
            else:
                data.append((r, g, b, a))
        px.putdata(data)
        bb = px.getbbox()
        mark = px.crop(bb) if bb else px
        print(f"lifted a flat background of rgb{avg}")

# 3. square it with a little breathing room, keeping transparency
mw, mh = mark.size
side = int(max(mw, mh) * 1.10)
canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
canvas.paste(mark, ((side - mw) // 2, (side - mh) // 2), mark)

# Don't upscale past the source: a soft favicon looks worse than a small one.
big = min(512, max(256, side))
canvas.resize((big, big), Image.LANCZOS).save(f"{out}/favicon.png", "PNG", optimize=True)
canvas.resize((180, 180), Image.LANCZOS).save(f"{out}/favicon-180.png", "PNG", optimize=True)
canvas.resize((32, 32), Image.LANCZOS).save(f"{out}/favicon-32.png", "PNG", optimize=True)
canvas.save(f"{out}/favicon.ico", "ICO", sizes=[(16, 16), (32, 32), (48, 48)])

# a preview at real favicon size, so the crop can be judged before shipping
preview = Image.new("RGBA", (240, 80), (255, 255, 255, 255))
for i, size in enumerate((16, 32, 48)):
    thumb = canvas.resize((size, size), Image.LANCZOS)
    preview.paste(thumb, (20 + i * 70, (80 - size) // 2), thumb)
preview.save(f"{out}/favicon-preview.png", "PNG")

print(f"wrote favicon.png ({big}px), favicon-180.png, favicon-32.png, favicon.ico")
print("check favicon-preview.png — that is how it will look in a tab")
