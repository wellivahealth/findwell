#!/usr/bin/env python3
"""Compose the social share card — the image shown when a link is pasted into
Slack, iMessage, LinkedIn, Facebook or X.

    python3 make_card.py

Builds a 1200x630 card: the practitioner photograph on the right, a deep green
panel on the left carrying the logo, a headline and the domain. Writes
public/assets/img/share-card.jpg (and .png for platforms that prefer it).

Re-run after changing the hero image or the logo.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "public/assets/img")

W, H = 1200, 630
PANEL = 0.56                      # left share of the canvas given to the panel
INK = (19, 42, 41)                # brand-deeper
INK_SOFT = (185, 206, 204)        # on-brand-soft
ACCENT = (194, 58, 75)            # prickly pear

SERIF = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"
SANS = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
SANS_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, f, max_w):
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=f) <= max_w:
            line = trial
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def build():
    card = Image.new("RGB", (W, H), INK)

    # --- photograph on the right ---
    photo = Image.open(f"{IMG}/hero-2000.jpg").convert("RGB")
    ph, pw = H, int(W * (1 - PANEL) + 260)          # extra width to bleed under the fade
    scale = max(pw / photo.width, ph / photo.height)
    photo = photo.resize((round(photo.width * scale), round(photo.height * scale)),
                         Image.LANCZOS)
    # keep the practitioner in frame: she sits right of centre in the source
    left = int((photo.width - pw) * 0.62)
    top = int((photo.height - ph) * 0.30)
    photo = photo.crop((left, top, left + pw, top + ph))
    card.paste(photo, (W - pw, 0))

    # --- soften the photo into the panel with a horizontal fade ---
    fade = Image.new("L", (W, H), 0)
    fd = ImageDraw.Draw(fade)
    x0, x1 = int(W * PANEL) - 150, int(W * PANEL) + 170
    for x in range(W):
        if x <= x0:
            v = 255
        elif x >= x1:
            v = 0
        else:
            v = int(255 * (1 - (x - x0) / (x1 - x0)) ** 1.4)
        fd.line([(x, 0), (x, H)], fill=v)
    card = Image.composite(Image.new("RGB", (W, H), INK), card,
                           fade.filter(ImageFilter.GaussianBlur(2)))

    d = ImageDraw.Draw(card)
    pad = 68
    text_w = int(W * PANEL) - pad - 40

    # --- logo, reversed to white ---
    logo = Image.open(f"{IMG}/logo-800.png").convert("RGBA")
    lw = 300
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    white = Image.new("RGBA", logo.size, (255, 255, 255, 255))
    white.putalpha(logo.getchannel("A"))
    card.paste(white, (pad, pad), white)

    y = pad + logo.height + 46

    # --- headline ---
    f_head = font(SERIF, 52)
    for line in wrap(d, "Find trusted holistic practitioners", f_head, text_w):
        d.text((pad, y), line, font=f_head, fill=(255, 255, 255))
        y += 62

    # --- supporting line ---
    y += 14
    f_sub = font(SANS, 24)
    for line in wrap(d, "Licensure, training, years in practice and pricing "
                        "on every listing.", f_sub, text_w):
        d.text((pad, y), line, font=f_sub, fill=INK_SOFT)
        y += 34

    # --- domain, anchored to the bottom ---
    f_url = font(SANS_MED, 24)
    d.text((pad, H - pad - 26), "findwelldirectory.com", font=f_url, fill=(255, 255, 255))
    d.line([(pad, H - pad - 44), (pad + 46, H - pad - 44)], fill=ACCENT, width=3)

    card.save(f"{IMG}/share-card.jpg", "JPEG", quality=88, optimize=True)
    card.save(f"{IMG}/share-card.png", "PNG", optimize=True)
    print(f"wrote share-card.jpg ({os.path.getsize(IMG + '/share-card.jpg') // 1024} KB) "
          f"and share-card.png — {W}x{H}")


if __name__ == "__main__":
    build()
