#!/usr/bin/env python3
"""Prepare a practitioner logo downloaded from a Formspree submission.

    python3 make_logo.py ~/Downloads/their-logo.png hibiscus-acupuncture

Writes a square 400px PNG and WebP to public/assets/img/providers/<slug>.*,
padding rather than cropping so nothing is cut off, and keeping transparency.

Then set the logo field on that practitioner in build.py:

    logo="/assets/img/providers/hibiscus-acupuncture.png",

and run build.py.
"""
import sys, os
from PIL import Image

if len(sys.argv) < 3 or not os.path.exists(sys.argv[1]):
    sys.exit("Usage: python3 make_logo.py path/to/logo.png <provider-slug>")

src_path, slug = sys.argv[1], sys.argv[2].strip("/")
SIZE = 400
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "public/assets/img/providers")
os.makedirs(out, exist_ok=True)

im = Image.open(src_path)
im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")

# Fit inside a square without cropping — logos are often wide wordmarks.
w, h = im.size
scale = min(SIZE / w, SIZE / h)
im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)

canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
canvas.paste(im, ((SIZE - im.size[0]) // 2, (SIZE - im.size[1]) // 2),
             im if im.mode == "RGBA" else None)

canvas.save(f"{out}/{slug}.png", "PNG", optimize=True)
canvas.save(f"{out}/{slug}.webp", "WEBP", quality=88, method=6)
print(f"wrote providers/{slug}.png and .webp")
print(f'set  logo="/assets/img/providers/{slug}.png",  then run build.py')
