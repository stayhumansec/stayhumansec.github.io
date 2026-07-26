"""
generate_post.py — reusable slide-rendering library for stay(human).sec

This is the core rendering toolkit built up across many iterations to match
the established brand exactly (see ../CLAUDE.md for the full brand brief).
Claude Code sessions should IMPORT and extend these functions rather than
rewriting the rendering logic from scratch each time.

Usage pattern for a new post:

    from generate_post import *

    img1, d1 = base_card()
    linux_chrome(d1, 1080, "alert.md")
    x = 96
    tag_pill(img1, x, 130, "YOUR TAG", bg=pink, angle=-3.5)
    d1 = ImageDraw.Draw(img1)
    # ... draw your headline, body text, etc using the helpers below ...
    draw_swipe_hook(img1, d1, "swipe hook text", 900, seed=11)
    footer(img1, d1, x, "1/4")
    img1.save("outputs/slide1.png")

IMPORTANT: after generating each slide, verify it with:
    img = Image.open("slideN.png")
    assert img.getbbox() is not None, "slide is blank!"
This project has a history of grid-alignment bugs when patching existing
images in place — prefer rebuilding a slide fully with this library rather
than editing pixels of a previous version.
"""

import os
from PIL import Image, ImageDraw, ImageFont
import math
import random

# ============================================================
# BRAND COLORS — do not change without updating CLAUDE.md too
# ============================================================
cream3 = (244, 241, 232)
orange3 = (255, 122, 61)
blue = (76, 141, 255)
green = (63, 207, 142)
violet = (150, 110, 230)
gold = (232, 167, 0)
pink = (232, 90, 130)
gray = (154, 148, 136)
gray_light = (199, 193, 178)

# ============================================================
# FONTS
#
# Poppins isn't guaranteed to be installed system-wide in every environment
# this project runs in, so the two Poppins weights this library needs are
# bundled directly in instagram/fonts/ (Google Fonts, SIL Open Font License —
# see instagram/fonts/OFL.txt) and loaded by a path relative to this file,
# not a system path. DejaVu Sans Mono is kept as a system-font reference
# since it ships as part of the base OS font package on every Debian/Ubuntu
# container this project has run in so far — if that ever isn't true in a
# future environment, bundle it the same way Poppins is bundled here.
# ============================================================
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
BOLD = os.path.join(_FONT_DIR, "Poppins-Bold.ttf")
REG = os.path.join(_FONT_DIR, "Poppins-Regular.ttf")
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


# ============================================================
# CORE GEOMETRY HELPERS
# ============================================================
def quad_bezier(p0, p1, p2, steps=90):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def wobbly(draw, points, color, width, jitter_amt=1.0, seed=1):
    """Hand-drawn look: jitters points along a path and stamps circles.
    This is THE signature texture of the brand's doodle illustrations —
    use this instead of draw.line() for anything meant to feel hand-drawn."""
    random.seed(seed)
    pts = [(x + random.uniform(-jitter_amt, jitter_amt),
            y + random.uniform(-jitter_amt, jitter_amt)) for (x, y) in points]
    r = max(width / 2, 1.4)
    for (x, y) in pts:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def circle_pts(cx, cy, r, step_deg=8):
    return [(cx + r * math.cos(math.radians(d)), cy + r * math.sin(math.radians(d)))
            for d in range(0, 361, step_deg)]


def rounded_rect_points(x0, y0, x1, y1, radius, arc_step_deg=8, edge_step=10):
    """Ordered perimeter points for a rounded rectangle -- straight edges plus
    four corner arcs, walked clockwise from the top-left corner back to itself.
    Exists so a rectangular shape (a phone body, a card outline, etc.) can be
    fed into wobbly()/wobbly_animated() exactly like any other point list --
    those two functions don't care whether the points came from a bezier
    curve or a straight edge, they just jitter-and-stamp whatever they're given."""
    r = radius
    pts = []

    def edge(p0, p1):
        n = max(2, int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / edge_step))
        return [(p0[0] + (p1[0] - p0[0]) * t / n, p0[1] + (p1[1] - p0[1]) * t / n) for t in range(n + 1)]

    def arc(cx, cy, start_deg, end_deg):
        return [(cx + r * math.cos(math.radians(d)), cy + r * math.sin(math.radians(d)))
                for d in range(start_deg, end_deg + 1, arc_step_deg)]

    pts += edge((x0 + r, y0), (x1 - r, y0))
    pts += arc(x1 - r, y0 + r, -90, 0)
    pts += edge((x1, y0 + r), (x1, y1 - r))
    pts += arc(x1 - r, y1 - r, 0, 90)
    pts += edge((x1 - r, y1), (x0 + r, y1))
    pts += arc(x0 + r, y1 - r, 90, 180)
    pts += edge((x0, y1 - r), (x0, y0 + r))
    pts += arc(x0 + r, y0 + r, 180, 270)
    return pts


def draw_thick_path(draw, points, offx, offy, iscale, color, width):
    r = max(width * iscale / 2, 1.6)
    for (x, y) in points:
        px, py = offx + x * iscale, offy + y * iscale
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color)


# ============================================================
# BRAND ICON — the bracket-person mark, used in every footer
# ============================================================
def draw_icon(draw, offx, offy, iscale, bracket_color, person_color):
    left_bracket = quad_bezier((38, 16), (20, 50), (38, 84))
    draw_thick_path(draw, left_bracket, offx, offy, iscale, bracket_color, 7)
    right_bracket = quad_bezier((112, 16), (130, 50), (112, 84))
    draw_thick_path(draw, right_bracket, offx, offy, iscale, bracket_color, 7)
    cx, cy = offx + 75 * iscale, offy + 38 * iscale
    r = max(13 * iscale, 6)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=person_color)
    body_arc = [(75 + 17 * math.cos(math.radians(a)), 78 + 17 * math.sin(math.radians(a)))
                for a in range(180, 361, 4)]
    draw_thick_path(draw, body_arc, offx, offy, iscale, person_color, 5)


# ============================================================
# CARD / CHROME / LAYOUT PRIMITIVES
# ============================================================
def base_card(size=1080):
    """The base 1080x1080 slide: black bg, 24px grid, rounded cream border."""
    img = Image.new("RGB", (size, size), (0, 0, 0))
    d = ImageDraw.Draw(img)
    grid_color = (40, 36, 32)
    for x in range(0, size, 24):
        d.line([(x, 0), (x, size)], fill=grid_color, width=1)
    for y in range(0, size, 24):
        d.line([(0, y), (size, y)], fill=grid_color, width=1)
    d.rounded_rectangle((10, 10, size - 10, size - 10), radius=46, outline=cream3, width=6)
    return img, d


def dashed_hline(draw, y, x0, x1, color, width=2, dash=8, gap=6):
    x = x0
    while x < x1:
        draw.line([(x, y), (min(x + dash, x1), y)], fill=color, width=width)
        x += dash + gap


def linux_chrome(d, size, filename):
    """Terminal chrome bar at the top of every slide."""
    cf = font(MONO_REG, 22)
    d.text((36, 30), f"stay(human).sec:~$ cat {filename}", font=cf, fill=gray)
    btn_y = 42
    btn_font = font(MONO_REG, 24)
    d.text((size - 150, btn_y - 16), "_", font=btn_font, fill=gray)
    d.rectangle([size - 110, btn_y - 10, size - 92, btn_y + 8], outline=gray, width=2)
    d.line([(size - 64, btn_y - 9), (size - 46, btn_y + 9)], fill=(255, 90, 54), width=3)
    d.line([(size - 64, btn_y + 9), (size - 46, btn_y - 9)], fill=(255, 90, 54), width=3)
    dashed_hline(d, 78, 30, size - 30, (90, 82, 70), 2, 10, 7)


def tag_pill(base_img, x, y, text, bg, fg=(255, 255, 255), angle=-3.4, font_size=24):
    """Rotated rounded 'sticker' tag pill — used for QUICK QUESTION, MY STORY,
    FILE_001.md, etc. Uses a generous transparent margin before rotating to
    avoid the edge-clipping artifact this project ran into before."""
    f = font(BOLD, font_size)
    tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    tw = td.textlength(text, font=f)
    pad = 22
    w, h = int(tw + pad * 2), 50
    margin = 60
    pill = Image.new("RGBA", (w + margin * 2, h + margin * 2), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle([margin, margin, margin + w, margin + h], radius=h // 2, fill=bg + (255,))
    pd.text((margin + pad, margin + 13), text, font=f, fill=fg + (255,))
    rotated = pill.rotate(angle, resample=Image.BICUBIC, expand=True)
    base_img.paste(rotated, (int(x - margin), int(y - margin)), rotated)


def footer(base_img, d, x, right_text):
    """Standard footer: brand icon + wordmark on the left, slide counter on the right."""
    foot_y = 972
    dashed_hline(d, foot_y, 30, 1050, (90, 82, 70), 2, 10, 7)
    iscale = 0.55
    icon_h = 100 * iscale
    icon_y = foot_y + (60 - icon_h) / 2 + 6
    draw_icon(d, x, icon_y, iscale, cream3, orange3)
    icon_w = 150 * iscale
    ff = font(MONO_REG, 26)
    d.text((x + icon_w + 16, foot_y + 18), "stay(human).sec", font=ff, fill=cream3)
    rw = d.textlength(right_text, font=ff)
    d.text((1050 - rw, foot_y + 22), right_text, font=ff, fill=gray)


def draw_swipe_hook(img, d, text, y_pos, seed=1):
    """The bottom-right 'keep reading' arrow + text, used on every slide except the last."""
    hook_font = font(BOLD, 22)
    tw = d.textlength(text, font=hook_font)
    x_text = 1050 - tw - 70
    d.text((x_text, y_pos), text, font=hook_font, fill=orange3)
    ax0 = x_text + tw + 14
    ay0 = y_pos + 12
    shaft = quad_bezier((ax0, ay0), (ax0 + 30, ay0 - 8), (ax0 + 56, ay0 + 6), 60)
    wobbly(d, shaft, orange3, 5, 0.8, seed)
    ex, ey = shaft[-1]
    ex2, ey2 = shaft[-6]
    ang = math.atan2(ey - ey2, ex - ex2)
    head_len, spread = 14, math.radians(30)
    h1 = (ex - head_len * math.cos(ang - spread), ey - head_len * math.sin(ang - spread))
    h2 = (ex - head_len * math.cos(ang + spread), ey - head_len * math.sin(ang + spread))
    wobbly(d, quad_bezier((ex, ey), ((ex + h1[0]) / 2, (ey + h1[1]) / 2), h1, 16), orange3, 5, 0.6, seed + 1)
    wobbly(d, quad_bezier((ex, ey), ((ex + h2[0]) / 2, (ey + h2[1]) / 2), h2, 16), orange3, 5, 0.6, seed + 2)


def wrap_text(draw, text, font_obj, max_w):
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if draw.textlength(test, font=font_obj) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def clean_smiley(d, cx, cy, s=1.0):
    """The wobbly-line smiley mascot doodle."""
    head = circle_pts(cx, cy, 80 * s, 6)
    wobbly(d, head, cream3, 6, 1.4, seed=101)
    eye_l = quad_bezier((cx - 34 * s, cy - 8 * s), (cx - 22 * s, cy - 20 * s), (cx - 10 * s, cy - 8 * s))
    eye_r = quad_bezier((cx + 10 * s, cy - 8 * s), (cx + 22 * s, cy - 20 * s), (cx + 34 * s, cy - 8 * s))
    wobbly(d, eye_l, cream3, 5, 0.9, seed=102)
    wobbly(d, eye_r, cream3, 5, 0.9, seed=103)
    smile = quad_bezier((cx - 36 * s, cy + 16 * s), (cx, cy + 46 * s), (cx + 36 * s, cy + 16 * s))
    wobbly(d, smile, orange3, 6, 1.0, seed=104)


def verify_slide(path):
    """Call this after saving every slide. Catches the 'blank image' bug class
    this project ran into repeatedly."""
    img = Image.open(path)
    bbox = img.getbbox()
    assert img.size == (1080, 1080), f"{path}: wrong size {img.size}"
    assert bbox is not None, f"{path}: image is blank!"
    print(f"✓ {path} — {img.size}, bbox {bbox}")
    return True


if __name__ == "__main__":
    print("This is a library, not a script to run directly.")
    print("Import it: from generate_post import *")
    print("See the module docstring at the top of this file for usage.")
