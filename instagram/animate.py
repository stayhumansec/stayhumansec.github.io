"""
animate.py — progressive "draws itself" frame rendering + MP4 assembly for
stay(human).sec's doodle style, built on top of generate_post.py.

This does NOT introduce a new visual style. wobbly_animated() below uses the
exact same jitter math as wobbly() in generate_post.py — it's a temporal
split of the same rendering (draw N% of the dots, save a frame, draw more),
not a different look. A finished animation's last frame is pixel-identical
to what the existing still-image functions (clean_smiley, draw_icon, tag
pills, etc.) already produce, since those are untouched and still draw
instantly when called directly.

Requires ffmpeg on PATH for the assembly step (`apt-get install ffmpeg` if
missing). Unlike the bundled Poppins fonts in instagram/fonts/, ffmpeg is a
system binary, not an asset file this repo can carry — any environment that
wants to run assemble_video() needs it installed separately.

Usage pattern:

    from animate import FrameRecorder, wobbly_animated, assemble_video
    from generate_post import base_card

    img, d = base_card()
    rec = FrameRecorder(img, d, "outputs/smiley_frames")
    # ... draw strokes progressively with wobbly_animated(rec, ...) ...
    rec.hold_last_frame(8)  # optional: linger on the finished drawing
    assemble_video("outputs/smiley_frames", "outputs/smiley.mp4", fps=20)

See animate_clean_smiley() at the bottom for a full worked example.
"""

import math
import os
import random
import shutil
import struct
import subprocess
import wave

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from generate_post import cream3, orange3


class FrameRecorder:
    """Holds one persistent (img, draw) pair and saves numbered PNG frames
    into out_dir as drawing progresses. Frames are named frame_0001.png,
    frame_0002.png, ... so ffmpeg's %04d pattern picks them up in order."""

    def __init__(self, img, draw, out_dir, clean=True):
        self.img = img
        self.draw = draw
        self.out_dir = out_dir
        if clean and os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        self.index = 1
        self.click_frames = []  # frame indices where a keystroke sound should land
        self.blink_frames = []  # frame indices where a soft ambient cursor-tick sound should land

    def snapshot(self):
        path = os.path.join(self.out_dir, f"frame_{self.index:04d}.png")
        self.img.save(path)
        self.index += 1
        return path

    def hold_last_frame(self, extra_frames):
        """Duplicates the most recent frame extra_frames more times, so the
        finished drawing lingers on screen for a moment instead of the video
        cutting off the instant the last dot lands."""
        if self.index <= 1:
            return
        last_path = os.path.join(self.out_dir, f"frame_{self.index - 1:04d}.png")
        for _ in range(extra_frames):
            new_path = os.path.join(self.out_dir, f"frame_{self.index:04d}.png")
            shutil.copyfile(last_path, new_path)
            self.index += 1


def wobbly_animated(recorder, points, color, width, jitter_amt=1.0, seed=1, num_frames=10):
    """Progressive version of wobbly() in generate_post.py. Draws the same
    jittered, hand-drawn stroke — identical random jitter formula, identical
    dot-stamping — but in `num_frames` incremental chunks (10% at a time by
    default), calling recorder.snapshot() after each chunk instead of
    drawing every dot in one go. A stroke finished this way looks exactly
    like the equivalent wobbly() call, just spread across frames.

    num_frames controls granularity per stroke, not overall video length —
    a longer stroke (more points) with the same num_frames just means more
    dots land between each saved frame.
    """
    random.seed(seed)
    pts = [(px + random.uniform(-jitter_amt, jitter_amt),
            py + random.uniform(-jitter_amt, jitter_amt)) for (px, py) in points]
    r = max(width / 2, 1.4)
    n = len(pts)
    if n == 0:
        return

    checkpoints = sorted(set(max(1, round(n * (i / num_frames))) for i in range(1, num_frames + 1)))
    if checkpoints[-1] != n:
        checkpoints[-1] = n

    drawn = 0
    for cp in checkpoints:
        for (px, py) in pts[drawn:cp]:
            recorder.draw.ellipse([px - r, py - r, px + r, py + r], fill=color)
        drawn = cp
        recorder.snapshot()


def grow_circle(recorder, cx, cy, max_r, color, num_frames=8, min_r=0):
    """Fills in a solid circle by growing its radius from min_r to max_r over
    num_frames frames -- for things like a pupil/iris that should appear to
    bloom into place rather than "draw itself" stroke by stroke the way an
    outline does. Not built on wobbly_animated since there's no outline path
    to walk; this is a separate, simpler primitive for filled shapes."""
    for step in range(1, num_frames + 1):
        r = min_r + (max_r - min_r) * step / num_frames
        recorder.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        recorder.snapshot()


def fade_in_text(recorder, lines, font_obj, color, x, y, line_height, num_frames=12):
    """Fades in one or more lines of text over num_frames frames, alpha
    0 -> 255, composited on top of whatever's currently in recorder.img (the
    frozen illustration underneath). This is deliberately a different
    mechanism from wobbly_animated/grow_circle: text doesn't have a natural
    "draw itself" order the way a hand-drawn line or a growing circle does,
    so instead of accumulating strokes, every frame re-composites the same
    target text at a higher opacity over the same frozen base.

    x may be a fixed left-edge pixel position, or the string 'center' to
    horizontally center every line independently (e.g. for a hook headline
    under an illustration, where lines are different widths).

    After the final (fully opaque) frame, recorder.img/recorder.draw are
    updated in place to that fully-opaque composite, so anything drawn or
    held afterward (e.g. hold_last_frame()) builds on the text-visible
    frame, not the pre-text base underneath it.
    """
    base = recorder.img.convert('RGBA')
    overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    ty = y
    for line in lines:
        if x == 'center':
            lw = odraw.textlength(line, font=font_obj)
            line_x = (base.size[0] - lw) / 2
        else:
            line_x = x
        odraw.text((line_x, ty), line, font=font_obj, fill=color + (255,))
        ty += line_height

    composite = base
    for step in range(1, num_frames + 1):
        alpha_mult = step / num_frames
        faded = overlay.copy()
        alpha_channel = faded.split()[3].point(lambda a, m=alpha_mult: int(a * m))
        faded.putalpha(alpha_channel)
        composite = Image.alpha_composite(base, faded)
        composite.convert('RGB').save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        recorder.index += 1

    recorder.img = composite.convert('RGB')
    recorder.draw = ImageDraw.Draw(recorder.img)


def fade_in_segments(recorder, segments, font_obj, x, y, num_frames=12):
    """Like fade_in_text, but for a single line made of multiple colored
    runs in reading order (e.g. cream 'stay', orange '(human)', cream
    '.sec') instead of one uniform color -- same alpha-composite mechanism
    (0 -> 255 over num_frames, re-composited on the frozen base each
    frame), just with per-segment fill colors. `segments` is a list of
    (text, color) tuples. x is a fixed left-edge pixel, or 'center' to
    horizontally center the whole composed line. Updates recorder.img/
    recorder.draw to the fully-opaque composite afterward, same as
    fade_in_text, so anything drawn/held afterward builds on top of it."""
    base = recorder.img.convert('RGBA')
    overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    full_text = ''.join(s for s, _ in segments)
    total_w = odraw.textlength(full_text, font=font_obj)
    line_x = (base.size[0] - total_w) / 2 if x == 'center' else x
    cx = line_x
    for text, color in segments:
        odraw.text((cx, y), text, font=font_obj, fill=color + (255,))
        cx += odraw.textlength(text, font=font_obj)

    composite = base
    for step in range(1, num_frames + 1):
        alpha_mult = step / num_frames
        faded = overlay.copy()
        alpha_channel = faded.split()[3].point(lambda a, m=alpha_mult: int(a * m))
        faded.putalpha(alpha_channel)
        composite = Image.alpha_composite(base, faded)
        composite.convert('RGB').save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        recorder.index += 1

    recorder.img = composite.convert('RGB')
    recorder.draw = ImageDraw.Draw(recorder.img)


def type_text_animated(recorder, segments, font_obj, x, y, num_frames=20, cursor=True, cursor_color=None):
    """Terminal-style character-by-character reveal for a single line made
    of multiple colored runs -- the Python/PIL counterpart to the homepage
    news ticker's typing effect (initNewsTicker in site.js). The two can't
    literally share code (one runs in the browser via setInterval, this
    one bakes discrete PNG frames), but the visual mechanic matches: the
    concatenated text is revealed left-to-right over num_frames steps,
    each frame drawing whichever prefix is visible so far in each
    segment's own color, with a thin trailing cursor bar while typing is
    in progress. `segments` is a list of (text, color) tuples in reading
    order. x is a fixed left-edge pixel (no centering support, since a
    growing/shrinking line can't stay centered while typing without
    jittering horizontally). Updates recorder.img/recorder.draw to the
    fully-typed, cursor-free frame afterward, same pattern as
    fade_in_text/fade_in_segments."""
    full_text = ''.join(s for s, _ in segments)
    total_chars = len(full_text)
    if total_chars == 0:
        return
    cursor_color = cursor_color or orange3
    base = recorder.img.copy()

    def draw_prefix(frame_img, chars_shown, with_cursor):
        fdraw = ImageDraw.Draw(frame_img)
        cx = x
        remaining = chars_shown
        for text, color in segments:
            if remaining <= 0:
                break
            take = min(len(text), remaining)
            visible = text[:take]
            if visible:
                fdraw.text((cx, y), visible, font=font_obj, fill=color)
                cx += fdraw.textlength(visible, font=font_obj)
            remaining -= take
        if with_cursor:
            bar_w = max(int(font_obj.size * 0.12), 2)
            fdraw.rectangle([cx + 3, y, cx + 3 + bar_w, y + font_obj.size], fill=cursor_color)
        return cx

    prev_chars = 0
    for step in range(1, num_frames + 1):
        chars_shown = max(1, round(total_chars * step / num_frames))
        if chars_shown > prev_chars:
            recorder.click_frames.append(recorder.index)  # for synthesize_typing_track()
        prev_chars = chars_shown
        frame = base.copy()
        draw_prefix(frame, chars_shown, cursor and chars_shown < total_chars)
        frame.save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        recorder.index += 1

    final = base.copy()
    draw_prefix(final, total_chars, False)
    recorder.img = final
    recorder.draw = ImageDraw.Draw(recorder.img)


def type_and_erase_line(recorder, segments, font_obj, x, y, type_frames=18, hold_frames=25,
                         erase_frames=10, cursor_color=None):
    """Types `segments` in character-by-character at (x, y) (like
    type_text_animated), holds at full opacity, then backspaces it back
    out character by character -- leaving recorder.img/recorder.draw
    exactly as they were before this call, as if the line was never
    there. This is the terminal type+erase mechanic the homepage news
    ticker actually uses (type, hold ~2.6s, erase, pause, next --
    initNewsTicker in site.js), brought to the Python/PIL animation
    pipeline: chain several calls (same or different x/y) to build a
    type-hold-erase sequence for a run of beats, each one fully clearing
    before the next types in, rather than crossfade_text_beats' dissolve.

    Records a click in recorder.click_frames every time a character is
    added or removed, for synthesize_typing_track() to turn into
    keystroke sound effects afterward.
    """
    full_text = ''.join(s for s, _ in segments)
    total_chars = len(full_text)
    if total_chars == 0:
        return
    cursor_color = cursor_color or orange3
    base = recorder.img.copy()

    def draw_prefix(frame_img, chars_shown, with_cursor):
        fdraw = ImageDraw.Draw(frame_img)
        cx = x
        remaining = chars_shown
        for text, color in segments:
            if remaining <= 0:
                break
            take = min(len(text), remaining)
            visible = text[:take]
            if visible:
                fdraw.text((cx, y), visible, font=font_obj, fill=color)
                cx += fdraw.textlength(visible, font=font_obj)
            remaining -= take
        if with_cursor:
            bar_w = max(int(font_obj.size * 0.12), 2)
            fdraw.rectangle([cx + 3, y, cx + 3 + bar_w, y + font_obj.size], fill=cursor_color)

    def save_frame(chars_shown, with_cursor):
        frame = base.copy()
        draw_prefix(frame, chars_shown, with_cursor)
        frame.save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        recorder.index += 1

    prev_chars = 0
    for step in range(1, type_frames + 1):
        chars_shown = max(1, round(total_chars * step / type_frames))
        if chars_shown > prev_chars:
            recorder.click_frames.append(recorder.index)
        prev_chars = chars_shown
        save_frame(chars_shown, chars_shown < total_chars)

    for _ in range(hold_frames):
        save_frame(total_chars, False)

    prev_chars = total_chars
    for step in range(1, erase_frames + 1):
        chars_shown = max(0, total_chars - round(total_chars * step / erase_frames))
        if chars_shown < prev_chars:
            recorder.click_frames.append(recorder.index)
        prev_chars = chars_shown
        save_frame(chars_shown, chars_shown > 0)

    # fully erased -- recorder.img/draw are left untouched (still == base)


DECRYPT_CHARS = "!@#$%^&*<>[]{}/\\|?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def type_decrypt(recorder, segments, font_obj, x, y, total_frames):
    """Reveals text via a decrypt/scramble effect instead of left-to-
    right typing: every character position animates in parallel, each
    flickering through random glyphs before locking to its real value,
    with positions locking in a left-to-right staggered wave (not all
    at once, not strictly sequential either) -- completes in exactly
    total_frames frames regardless of string length, like text being
    decrypted rather than typed. Assumes font_obj is monospace (true
    for MONO_REG/MONO_BOLD) so per-character x-advance is constant and
    doesn't jitter while a position is still scrambling.

    Every 3rd frame logs a click to recorder.click_frames -- sparser
    than real typing's one-per-character, since a dense per-frame click
    here would read as noise, not keystrokes; enough to give the
    scramble a subtle "static" texture under it.

    Updates recorder.img/draw to the fully-settled frame afterward, same
    pattern as type_text_animated."""
    full_text = ''.join(s for s, _ in segments)
    n = len(full_text)
    if n == 0:
        return
    colors = []
    for text, color in segments:
        colors.extend([color] * len(text))

    char_w = ImageDraw.Draw(recorder.img).textlength('M', font=font_obj)
    total_frames = max(n, total_frames)  # never fewer frames than characters -- each needs a chance to flicker

    lock_frame = []
    for i in range(n):
        spread = int(total_frames * 0.6 * i / max(1, n - 1)) if n > 1 else 0
        lf = int(total_frames * 0.25) + spread + random.randint(-2, 2)
        lock_frame.append(max(0, min(total_frames - 1, lf)))

    base = recorder.img.copy()
    for f in range(total_frames):
        frame = base.copy()
        fdraw = ImageDraw.Draw(frame)
        cx = x
        for i in range(n):
            ch = full_text[i] if f >= lock_frame[i] else random.choice(DECRYPT_CHARS)
            fdraw.text((cx, y), ch, font=font_obj, fill=colors[i])
            cx += char_w
        frame.save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        if f % 3 == 0:
            recorder.click_frames.append(recorder.index)
        recorder.index += 1

    final = base.copy()
    fdraw = ImageDraw.Draw(final)
    cx = x
    for i in range(n):
        fdraw.text((cx, y), full_text[i], font=font_obj, fill=colors[i])
        cx += char_w
    recorder.img = final
    recorder.draw = ImageDraw.Draw(final)


def dim_region(img, y0, y1, factor=0.45):
    """Darkens a horizontal band of img in place (a uniform brightness
    multiply, not a per-pixel alpha trick) -- against this card's
    near-black background, this reads as the bright foreground text
    dimming to about half-strength while the background stays
    essentially unchanged, which is exactly the "scrolled-into-history,
    de-emphasized" look terminal scrollback has, without needing to
    track which pixels are text vs. background."""
    w = img.size[0]
    region = img.crop((0, y0, w, y1))
    dimmed = ImageEnhance.Brightness(region).enhance(factor)
    img.paste(dimmed, (0, y0))


def scroll_content(recorder, blank_template, shift_px, content_top=96, content_bottom=None, num_frames=10):
    """Animates the text-content band (from content_top, i.e. below the
    terminal chrome bar, down to content_bottom) scrolling upward by
    shift_px over num_frames frames, revealing blank space at the bottom
    for new content -- filled from `blank_template` (the chrome+grid+
    border with nothing typed below it yet, so the revealed area matches
    the card's real background instead of flat black). content_bottom
    defaults to 40px above the canvas edge specifically to exclude the
    card's own decorative outer border (drawn once, low on the canvas,
    as part of every base_card()) from the scrolled band -- an earlier
    version cropped all the way to the canvas edge, which swept that
    border into the moving band and produced a visible duplicate/ghost
    border wherever it landed after shifting. Content that scrolls above
    content_top is simply clipped by the canvas edge (standard terminal
    scrollback behavior -- older lines eventually scroll out of view).
    Call dim_region() on the not-yet-dimmed portion of the content band
    before calling this, so what scrolls away also reads as
    de-emphasized history, not just content that jumped position."""
    start_img = recorder.img.copy()
    w, h = start_img.size
    if content_bottom is None:
        content_bottom = h - 40
    band = start_img.crop((0, content_top, w, content_bottom))
    for step in range(1, num_frames + 1):
        dy = int(shift_px * step / num_frames)
        frame = blank_template.copy()
        frame.paste(band, (0, content_top - dy))
        frame.save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        recorder.index += 1
    final = blank_template.copy()
    final.paste(band, (0, content_top - shift_px))
    recorder.img = final
    recorder.draw = ImageDraw.Draw(final)


def draw_clean_icon(draw, kind, cx, cy, scale, color, width=5):
    """Draws one of a small set of pillar icons with plain PIL primitives
    (ellipse/polygon/line/rounded_rectangle) -- clean, anti-aliased,
    zero jitter, deliberately NOT the site's wobbly hand-drawn doodle
    style. Built for animate_silhouette_story()'s pillar act, where
    icons pop in via scale+alpha (see icon_pop_overlay()-style callers)
    rather than a stroke-by-stroke reveal, so the draw itself has to be
    clean to begin with -- there's no reveal animation here masking a
    rough line. `kind` is one of: 'shield', 'lightbulb', 'folder',
    'magnifier', 'document', 'chip', 'broadcast', 'chevron', 'book'."""
    s = scale
    if kind == 'shield':
        pts = [(cx - 26 * s, cy - 30 * s), (cx + 26 * s, cy - 30 * s), (cx + 26 * s, cy + 6 * s),
               (cx, cy + 40 * s), (cx - 26 * s, cy + 6 * s)]
        draw.line(pts + [pts[0]], fill=color, width=width, joint='curve')
    elif kind == 'lightbulb':
        draw.ellipse([cx - 16 * s, cy - 24 * s, cx + 16 * s, cy + 8 * s], outline=color, width=width)
        draw.rounded_rectangle([cx - 6 * s, cy + 8 * s, cx + 6 * s, cy + 18 * s], radius=3 * s, outline=color, width=width)
    elif kind == 'folder':
        draw.rounded_rectangle([cx - 30 * s, cy - 12 * s, cx + 30 * s, cy + 22 * s], radius=5 * s, outline=color, width=width)
        draw.line([(cx - 30 * s, cy - 12 * s), (cx - 18 * s, cy - 20 * s), (cx + 4 * s, cy - 20 * s), (cx + 12 * s, cy - 12 * s)],
                   fill=color, width=width, joint='curve')
    elif kind == 'magnifier':
        draw.ellipse([cx - 20 * s, cy - 20 * s, cx + 12 * s, cy + 12 * s], outline=color, width=width)
        draw.line([(cx + 9 * s, cy + 9 * s), (cx + 26 * s, cy + 26 * s)], fill=color, width=width + 1)
    elif kind == 'document':
        draw.rounded_rectangle([cx - 20 * s, cy - 28 * s, cx + 20 * s, cy + 28 * s], radius=4 * s, outline=color, width=width)
        for ly in (-10, 0, 10):
            draw.line([(cx - 11 * s, cy + ly * s), (cx + 11 * s, cy + ly * s)], fill=color, width=max(2, width - 2))
    elif kind == 'chip':
        draw.rounded_rectangle([cx - 22 * s, cy - 22 * s, cx + 22 * s, cy + 22 * s], radius=6 * s, outline=color, width=width)
        draw.ellipse([cx - 8 * s, cy - 8 * s, cx + 8 * s, cy + 8 * s], fill=color)
    elif kind == 'broadcast':
        draw.ellipse([cx - 5 * s, cy - 5 * s, cx + 5 * s, cy + 5 * s], fill=color)
        for r in (16, 28):
            draw.arc([cx - r * s, cy - r * s, cx + r * s, cy + r * s], start=-55, end=55, fill=color, width=width)
            draw.arc([cx - r * s, cy - r * s, cx + r * s, cy + r * s], start=125, end=235, fill=color, width=width)
    elif kind == 'chevron':
        draw.ellipse([cx - 28 * s, cy - 28 * s, cx + 28 * s, cy + 28 * s], outline=color, width=width)
        draw.line([(cx - 10 * s, cy - 8 * s), (cx, cy + 8 * s), (cx + 10 * s, cy - 8 * s)],
                   fill=color, width=width, joint='curve')
    elif kind == 'book':
        draw.line([(cx, cy - 16 * s), (cx, cy + 20 * s)], fill=color, width=width)
        draw.arc([cx - 30 * s, cy - 20 * s, cx, cy + 24 * s], start=-90, end=90, fill=color, width=width)
        draw.arc([cx, cy - 20 * s, cx + 30 * s, cy + 24 * s], start=90, end=270, fill=color, width=width)
    else:
        raise ValueError(f"unknown icon kind: {kind!r}")


def draw_terminal_chrome(recorder, prompt_text="user@stayhumansec:~$ ./explore.sh"):
    """Draws a persistent terminal-window title bar near the top of the
    card -- a rounded outline, a monospace prompt line on the left, and
    three window-control glyphs on the right (minimize/maximize/close,
    stroke icons matching the site's own `.win-controls` SVGs in
    index.html/post.html/etc., not generic macOS traffic-light dots,
    to stay on-brand) -- so the type-and-erase lines beneath it read as
    text appearing inside a real terminal window, not floating on the
    bare grid. Bakes directly into recorder.img/draw (persists across
    every subsequent frame until _fade_to_clean_base() removes it), and
    snapshots once so the chrome itself is visible on its own frame."""
    from generate_post import font, MONO_REG, gray_light

    d = recorder.draw
    x0, y0, x1, y1 = 40, 40, 1040, 92
    border_color = (58, 53, 44)  # matches --line
    d.rounded_rectangle([x0, y0, x1, y1], radius=10, outline=border_color, width=2)
    d.line([x0, y1, x1, y1], fill=border_color, width=2)

    prompt_font = font(MONO_REG, 22)
    d.text((x0 + 20, y0 + 15), prompt_text, font=prompt_font, fill=gray_light)

    icon_y = (y0 + y1) // 2
    mx = x1 - 96
    d.line([mx, icon_y, mx + 18, icon_y], fill=cream3, width=2)
    mx2 = x1 - 62
    d.rounded_rectangle([mx2, icon_y - 8, mx2 + 16, icon_y + 8], radius=2, outline=cream3, width=2)
    mx3 = x1 - 28
    d.line([mx3, icon_y - 8, mx3 + 16, icon_y + 8], fill=cream3, width=2)
    d.line([mx3, icon_y + 8, mx3 + 16, icon_y - 8], fill=cream3, width=2)

    recorder.snapshot()


def _fade_to_clean_base(recorder, num_frames=10):
    """Cross-dissolves from whatever's currently baked into recorder.img
    (e.g. draw_terminal_chrome()'s title bar) back to a freshly rendered,
    empty base_card() -- used to remove a persistent overlay before a
    differently-styled act begins (Act 3's brand lockup doesn't use the
    terminal-chrome look Acts 1-2 do), so the handoff is a fade rather
    than a hard cut. Updates recorder.img/draw to the clean base
    afterward, same pattern as fade_in_segments."""
    from generate_post import base_card

    clean_img, clean_d = base_card()
    start = recorder.img.convert('RGBA')
    end = clean_img.convert('RGBA')
    for step in range(1, num_frames + 1):
        t = step / num_frames
        frame = Image.blend(start, end, t)
        frame.convert('RGB').save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        recorder.index += 1
    recorder.img, recorder.draw = clean_img, clean_d


def _smoothstep(t):
    """Eased 0->1 progress curve (3t^2 - 2t^3) instead of linear -- motion
    starts and ends gently instead of at constant speed, which is what
    actually reads as "smooth" rather than mechanical. Used by
    crossfade_text_beats() for every fade so multi-beat sequences don't
    feel like a metronome. Symmetric -- eases in and out equally, unlike
    _ease_out_cubic()/_ease_out_back() below, which is exactly why pure
    smoothstep on every parameter at once reads as robotic: real motion
    rarely eases in and out by the same amount."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _ease_out_cubic(t):
    """Fast-start, slow-arrival progress curve (1-(1-t)^3) -- unlike
    _smoothstep()'s symmetric ease, this front-loads the motion so it
    reads as a real, slightly urgent movement settling into place
    (a head lowering quickly then arriving gently) rather than a
    uniform glide the whole way."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _ease_out_back(t, overshoot=1.0):
    """Progress curve that overshoots past 1.0 before settling back to
    it (Robert Penner's "back ease out") -- used for motions that should
    read as having real weight/momentum (shoulders tensing past their
    final position before easing back), not just arriving directly.
    `overshoot` controls how far past 1.0 it swings; keep this small
    (well under the default 1.70158) for a "very slight" overshoot
    rather than a bouncy cartoon one."""
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((overshoot + 1) * t + overshoot) + 1


def _render_beat_overlay(size, beat):
    """Renders one crossfade_text_beats() beat onto a transparent RGBA
    overlay, centered horizontally. `beat` is a dict:
      {"dot": color_or_None, "lines": [(segments, font_obj, y), ...]}
    segments is a list of (text, color) tuples. If "dot" is set, a small
    filled circle is drawn centered just above the first line -- the
    color-coded marker style used by the site's own router cards.
    Internal helper."""
    overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    lines = beat['lines']
    dot_color = beat.get('dot')
    if dot_color:
        r = 9
        cx, cy = size[0] / 2, lines[0][2] - 32
        od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dot_color + (255,))
    for segments, font_obj, y in lines:
        full_text = ''.join(s for s, _ in segments)
        line_w = od.textlength(full_text, font=font_obj)
        cx = (size[0] - line_w) / 2
        for text, color in segments:
            od.text((cx, y), text, font=font_obj, fill=color + (255,))
            cx += od.textlength(text, font=font_obj)
    return overlay


def _shift_vertical(img, dy):
    """Returns a copy of RGBA image `img` translated vertically by dy
    pixels (positive = down), transparent where it's shifted off-canvas.
    Used by crossfade_text_beats() to pair its fades with a drift instead
    of a static dissolve."""
    if dy == 0:
        return img
    shifted = Image.new('RGBA', img.size, (0, 0, 0, 0))
    shifted.paste(img, (0, int(round(dy))), img)
    return shifted


def crossfade_text_beats(recorder, beats, transition_frames=15, hold_frames=35):
    """Smoothly crossfades through a sequence of text "beats" on top of
    whatever's already frozen in recorder.img -- each beat fades in while
    the previous one simultaneously fades out (eased via _smoothstep, not
    linear), instead of a hard cut or a fade-to-black-then-fade-in. This
    is the primitive that makes a multi-beat sequence (a philosophy line,
    a tour of site sections, etc.) read as one continuous motion instead
    of a slideshow.

    IMPORTANT: pass the *entire* sequence of beats to ONE call, not one
    call per beat -- the crossfade-from-previous-beat state only carries
    across beats within a single call. Splitting a sequence across
    multiple calls silently degrades every later beat into a fade-in from
    the frozen base instead of a true crossfade from the beat before it.

    `beats` is a list of beat-specs, each either a dict
    `{"dot": color_or_None, "lines": [(segments, font_obj, y), ...]}`
    (segments = list of (text, color) tuples, lines centered horizontally,
    see `_render_beat_overlay`), or None/falsy for a "fade to clean base"
    beat (no text -- useful as the last beat before handing off to a
    different kind of animation, e.g. a drawn icon, so that handoff is
    also a fade rather than a cut). Every beat holds at full opacity for
    hold_frames before the next crossfade begins (the final beat's hold
    happens via whatever the caller does next, not here) -- hold_frames
    is either one int applied to every beat, or a list with one value per
    beat for per-beat pacing. Updates recorder.img/draw to the final
    composited frame afterward, same pattern as fade_in_segments.
    """
    hold_list = hold_frames if isinstance(hold_frames, (list, tuple)) else [hold_frames] * len(beats)
    if len(hold_list) != len(beats):
        raise ValueError(f"hold_frames list length ({len(hold_list)}) must match beats length ({len(beats)})")

    SHIFT = 36  # px of vertical drift during a crossfade -- see _shift_vertical note below

    base = recorder.img.convert('RGBA')
    prev_overlay = None
    for beat, beat_hold in zip(beats, hold_list):
        overlay = _render_beat_overlay(base.size, beat) if beat else Image.new('RGBA', base.size, (0, 0, 0, 0))
        for step in range(1, transition_frames + 1):
            t = _smoothstep(step / transition_frames)
            frame = base.copy()
            if prev_overlay is not None:
                # Pure alpha-dissolve reads as garbled overlapping text when
                # two different strings share the same position (unlike a
                # photo crossfade) -- pairing the fade with a vertical drift
                # (old text lifts away, new text settles into place) keeps
                # both legible throughout the transition instead of both
                # being half-visible in the same spot at once.
                fading_out = prev_overlay.copy()
                fading_out.putalpha(fading_out.split()[3].point(lambda a, m=(1 - t): int(a * m)))
                fading_out = _shift_vertical(fading_out, -SHIFT * t)
                frame = Image.alpha_composite(frame, fading_out)
            fading_in = overlay.copy()
            fading_in.putalpha(fading_in.split()[3].point(lambda a, m=t: int(a * m)))
            fading_in = _shift_vertical(fading_in, SHIFT * (1 - t))
            frame = Image.alpha_composite(frame, fading_in)
            frame.convert('RGB').save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
            recorder.index += 1

        held = Image.alpha_composite(base, overlay)
        for _ in range(beat_hold):
            held.convert('RGB').save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
            recorder.index += 1
        prev_overlay = overlay

    recorder.img = Image.alpha_composite(base, prev_overlay).convert('RGB')
    recorder.draw = ImageDraw.Draw(recorder.img)


def assemble_video(frame_dir, output_path, fps=20, pattern="frame_%04d.png"):
    """Stitches numbered frame PNGs in frame_dir into an MP4 via ffmpeg.

    fps is the readability control the brief asked for — roughly 15-25 fps
    is the sweet spot for a hand-drawn reveal: fast enough not to drag,
    slow enough to actually follow the stroke landing. Pass a lower value
    (e.g. 10) to linger longer, or higher (e.g. 30) for a snappier reveal.

    Explicitly encodes and tags full-range (PC/0-255) color rather than
    ffmpeg's default limited/broadcast range (16-235). Without this, many
    players assume limited range on an untagged stream and lift the
    blacks toward gray on playback -- the source frames are correct
    (verified pixel-for-pixel against the still-image renderer), but
    playback made the dark grid lines (and everything else against the
    pure-black background) look washed out/brighter than the actual
    slides. `in_range=full:out_range=full` on the scale filter fixes the
    conversion itself, not just the metadata tag, since libswscale can
    silently do a range conversion during scaling otherwise.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install it first (e.g. `apt-get install -y ffmpeg`) "
            "— it's a system dependency, not something bundled in this repo."
        )
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frame_dir, pattern),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1080:in_range=full:out_range=full",
        "-color_range", "pc",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    return output_path


def _decode_audio_to_samples(path, sample_rate=44100):
    """Decodes any audio file ffmpeg can read (mp3/wav/etc.) to a list of
    mono float samples in [-1, 1], via ffmpeg piping raw PCM to stdout --
    no extra Python audio-decoding library needed, same "ffmpeg is the
    only non-stdlib dependency" pattern the rest of this pipeline already
    relies on for video assembly/muxing."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH.")
    cmd = ["ffmpeg", "-y", "-i", path, "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "-"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio decode failed:\n{result.stderr.decode(errors='replace')}")
    raw = result.stdout
    n = len(raw) // 2
    ints = struct.unpack(f'<{n}h', raw[:n * 2])
    return [x / 32768.0 for x in ints]


def _extract_keyboard_clicks(path, sample_rate=44100, max_clicks=40, click_ms=45, min_gap_ms=70):
    """Detects individual keystroke transients in a real recording and
    extracts each one as a short standalone click sample, instead of
    playing the whole recording as one continuous background loop -- a
    loop runs on its own separate rhythm and reads as unsynced from the
    on-screen typing; individual extracted clicks, placed one per
    keystroke at that keystroke's exact frame (same mechanism the
    earlier from-scratch synthesis used), are what actually makes the
    sound track the visual typing.

    Onset detection: per-window average energy (~3ms windows) across the
    whole recording, a local peak counted as an onset once it clears 35%
    of the file's loudest window and sits at least min_gap_ms after the
    previous onset (so one keystroke's decay tail isn't picked up as a
    second click). Each onset is extracted as a click_ms-long slice,
    peak-normalized to 1.0 (so quiet/loud detections all play back at a
    consistent level once scaled by the caller) with a short fade-out on
    the tail so splicing it into the mix doesn't itself produce an
    audible click-off.
    """
    samples = _decode_audio_to_samples(path, sample_rate)
    n = len(samples)
    if n == 0:
        return []

    win = max(1, int(sample_rate * 0.003))
    energies = []
    i = 0
    while i < n:
        seg = samples[i:i + win]
        energies.append(sum(abs(x) for x in seg) / len(seg) if seg else 0.0)
        i += win

    peak_e = max(energies, default=0.0)
    if peak_e <= 0:
        return []
    threshold = peak_e * 0.35
    min_gap_windows = max(1, int((min_gap_ms / 1000.0) / (win / sample_rate)))

    onsets = []
    last_onset_w = -min_gap_windows
    for wi, e in enumerate(energies):
        if e >= threshold and (wi - last_onset_w) >= min_gap_windows:
            onsets.append(wi * win)
            last_onset_w = wi

    click_len = int(sample_rate * click_ms / 1000.0)
    fade_len = max(1, int(click_len * 0.25))
    clicks = []
    for onset in onsets[:max_clicks]:
        seg = list(samples[onset:onset + click_len])
        if not seg:
            continue
        peak = max((abs(x) for x in seg), default=0.0) or 1.0
        seg = [x / peak for x in seg]
        for k in range(min(fade_len, len(seg))):
            idx = len(seg) - 1 - k
            seg[idx] *= k / fade_len
        clicks.append(seg)
    return clicks


def _synth_blink_tick_samples(sample_rate):
    """Generates one synthesized ambient cursor-blink tick as a list of
    floats in [-1, 1] -- a very short, quiet, high-pitched sine blip
    under a fast decay. Deliberately soft/small (much quieter than a
    real keystroke click): this marks the cursor blinking during a
    pause between typed lines, a small ambient presence-of-life sound
    for moments when nothing is being typed, not a percussive event."""
    total_duration = 0.02
    n = max(1, int(sample_rate * total_duration))
    samples = []
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-t / 0.006)
        tone = math.sin(2 * math.pi * 1400 * t)
        samples.append(tone * env * 0.18)
    return samples


def _synth_chime_samples(sample_rate):
    """Generates one soft two-harmonic bell chime as a list of floats in
    [-1, 1] -- two sine tones (a fundamental + a fifth above it) under a
    gentle decay, marking a reveal moment. Used for animate_
    silhouette_story()'s brand-icon reflection appearing -- a small
    "aha" cue, not a percussive hit."""
    total_duration = 0.5
    n = max(1, int(sample_rate * total_duration))
    samples = []
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-t / 0.18)
        tone = math.sin(2 * math.pi * 660 * t) * 0.6 + math.sin(2 * math.pi * 990 * t) * 0.3
        samples.append(tone * env)
    return samples


def _synth_drone_segment(sample_rate, ramp_dur, hold_dur, relax_dur, base_freq=85, peak_freq=99, level=0.16):
    """Generates a continuous low ambient drone spanning ramp_dur +
    hold_dur + relax_dur seconds, as a list of floats in [-1, 1] --
    amplitude fades in over the ramp, sustains with a slow pitch wobble
    through the hold, then fades back out over the relax phase; pitch
    rises from base_freq to peak_freq over the ramp and eases back down
    over relax. Meant to sit under animate_silhouette_story()'s Act 1
    tension beat: rising in as the shoulders tense and the glow cools,
    sustaining (with the wobble reading as unease, not a glitch) through
    the held tense moment, fading back out as the posture relaxes --
    tracks the *visual* tension curve rather than being placed at a
    single frame the way every other sound in this file is."""
    total = ramp_dur + hold_dur + relax_dur
    n = max(1, int(sample_rate * total))
    samples = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / sample_rate
        if t < ramp_dur:
            p = t / ramp_dur if ramp_dur > 0 else 1.0
            amp = p
            freq = base_freq + (peak_freq - base_freq) * p
        elif t < ramp_dur + hold_dur:
            p = (t - ramp_dur) / hold_dur if hold_dur > 0 else 0.0
            amp = 1.0
            freq = peak_freq + 2.5 * math.sin(p * 6.0)
        else:
            p = (t - ramp_dur - hold_dur) / relax_dur if relax_dur > 0 else 1.0
            amp = max(0.0, 1.0 - p)
            freq = peak_freq - (peak_freq - base_freq) * p
        phase += 2 * math.pi * freq / sample_rate
        samples[i] = math.sin(phase) * amp * level
    return samples


def synthesize_silhouette_audio(fps, total_frames, out_wav, drone_events=None, chime_frames=None,
                                 tick_frames=None, sample_rate=44100):
    """Renders a WAV for animate_silhouette_story() -- a different mix
    than synthesize_sound_track() (which is built around click_frames/
    blink_frames tied to typed text): this video has no typing at all,
    so its sound design is three different things instead: a continuous
    ambient drone under the Act 1 tension beat (`drone_events`, a list
    of {"start_frame", "ramp_frames", "hold_frames", "relax_frames",
    optionally "base_freq"/"peak_freq"/"level"} dicts -- see
    _synth_drone_segment()), a soft chime at each entry in
    `chime_frames` (_synth_chime_samples() -- the icon-reflection
    reveal), and a soft ambient tick at each entry in `tick_frames`
    (_synth_blink_tick_samples() -- each pillar icon popping in during
    Act 2). Acts 3-6 deliberately get no sound at all: they're reading
    beats, and audio there would compete with reading time rather than
    reinforce anything."""
    duration_sec = total_frames / fps
    n_samples = int(duration_sec * sample_rate) + sample_rate
    buf = [0.0] * n_samples

    for ev in (drone_events or []):
        start = int((ev["start_frame"] / fps) * sample_rate)
        seg = _synth_drone_segment(
            sample_rate,
            ev["ramp_frames"] / fps, ev["hold_frames"] / fps, ev["relax_frames"] / fps,
            base_freq=ev.get("base_freq", 85), peak_freq=ev.get("peak_freq", 99), level=ev.get("level", 0.16),
        )
        for i, v in enumerate(seg):
            idx = start + i
            if idx < n_samples:
                buf[idx] += v

    for cf in (chime_frames or []):
        start = int((cf / fps) * sample_rate)
        chime = _synth_chime_samples(sample_rate)
        for i, v in enumerate(chime):
            idx = start + i
            if idx < n_samples:
                buf[idx] += v

    for tf in (tick_frames or []):
        start = int((tf / fps) * sample_rate)
        tick = _synth_blink_tick_samples(sample_rate)
        for i, v in enumerate(tick):
            idx = start + i
            if idx < n_samples:
                buf[idx] += v * 1.4  # a touch louder than the terminal video's blink tick -- this one carries more weight alone

    peak = max((abs(x) for x in buf), default=1.0) or 1.0
    scale = 0.85 / peak
    int_samples = [max(-32768, min(32767, int(x * scale * 32767))) for x in buf]

    with wave.open(out_wav, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f'<{len(int_samples)}h', *int_samples))
    return out_wav


def synthesize_sound_track(keyboard_audio_path, click_frames, blink_frames, fps,
                            total_frames, out_wav, sample_rate=44100):
    """Renders a WAV mixing two sound sources onto one track:

      1. Real keystroke clicks, extracted from a real recording
         (`keyboard_audio_path` -- see instagram/assets/sfx/
         keyboard_typing.mp3) via _extract_keyboard_clicks(), one placed
         at every entry in `click_frames` (frame indices recorded by
         type_text_animated()/type_and_erase_line() every time a
         character was added or removed) -- i.e. one real click per
         keystroke, synced to the exact frame that keystroke lands on.
         This is the primary sound design for this video: every line of
         typed text gets real keystroke sounds under it, not just one
         motto line the way an earlier version did.
      2. A soft synthesized ambient tick (_synth_blink_tick_samples) for
         every entry in `blink_frames` (frame indices recorded during a
         cursor-blink pause between typed lines), placed at that frame's
         exact timestamp -- a quiet presence-of-life cue for the pauses,
         much quieter than the keystroke clicks so it never competes
         with them.

    Deliberately does NOT fill every silent frame with something --
    holds with no click_frames/blink_frames entries (e.g. the beat held
    right before the brand icon reveals) stay genuinely silent, which is
    the point: real silence is what makes that moment land.

    ffmpeg (already a hard dependency for assemble_video()/mux_audio())
    does the mp3 decode; everything else is pure stdlib (wave/struct/
    math/random).
    """
    duration_sec = total_frames / fps
    n_samples = int(duration_sec * sample_rate) + sample_rate  # 1s pad so late sounds don't clip off
    buf = [0.0] * n_samples

    clicks = _extract_keyboard_clicks(keyboard_audio_path, sample_rate)
    for cf in click_frames:
        if not clicks:
            break
        start = int((cf / fps) * sample_rate)
        click = random.choice(clicks)
        amp = random.uniform(0.5, 0.8)  # slight per-keystroke level variation
        for i, v in enumerate(click):
            idx = start + i
            if idx < n_samples:
                buf[idx] += v * amp

    for bf in blink_frames:
        start = int((bf / fps) * sample_rate)
        tick = _synth_blink_tick_samples(sample_rate)
        for i, v in enumerate(tick):
            idx = start + i
            if idx < n_samples:
                buf[idx] += v

    peak = max((abs(x) for x in buf), default=1.0) or 1.0
    scale = 0.85 / peak
    int_samples = [max(-32768, min(32767, int(x * scale * 32767))) for x in buf]

    with wave.open(out_wav, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack(f'<{len(int_samples)}h', *int_samples))
    return out_wav


def mux_audio(video_path, audio_path, output_path):
    """Combines a (silent) video and a WAV audio track into one MP4 --
    video re-encoded to nothing new (stream-copied), audio encoded to AAC.
    `-shortest` trims to the video's length if the audio track (padded by
    synthesize_typing_track) runs slightly longer."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH.")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio mux failed:\n{result.stderr}")
    return output_path


def animate_clean_smiley(out_dir, video_path, cx=540, cy=540, s=1.0,
                          frames_per_stroke=10, hold_frames=8, fps=20):
    """Test case: an animated, progressively-drawn version of
    clean_smiley() from generate_post.py — same shape, same colors
    (cream3 head/eyes, orange3 smile), same jitter style, just drawn
    stroke by stroke instead of all at once. Proves the mechanism on the
    simplest existing brand element before it's used for anything bigger.
    """
    from generate_post import base_card, circle_pts, quad_bezier

    img, d = base_card()
    rec = FrameRecorder(img, d, out_dir)

    head = circle_pts(cx, cy, 80 * s, 6)
    wobbly_animated(rec, head, cream3, 6, 1.4, seed=101, num_frames=frames_per_stroke)

    eye_l = quad_bezier((cx - 34 * s, cy - 8 * s), (cx - 22 * s, cy - 20 * s), (cx - 10 * s, cy - 8 * s))
    wobbly_animated(rec, eye_l, cream3, 5, 0.9, seed=102, num_frames=frames_per_stroke)

    eye_r = quad_bezier((cx + 10 * s, cy - 8 * s), (cx + 22 * s, cy - 20 * s), (cx + 34 * s, cy - 8 * s))
    wobbly_animated(rec, eye_r, cream3, 5, 0.9, seed=103, num_frames=frames_per_stroke)

    smile = quad_bezier((cx - 36 * s, cy + 16 * s), (cx, cy + 46 * s), (cx + 36 * s, cy + 16 * s))
    wobbly_animated(rec, smile, orange3, 6, 1.0, seed=104, num_frames=frames_per_stroke)

    rec.hold_last_frame(hold_frames)

    total_frames = rec.index - 1
    assemble_video(out_dir, video_path, fps=fps)
    return total_frames


def animate_phone_eye_explainer(out_dir, video_path, fps=20):
    """"Is someone already inside your phone?" — a phone silhouette draws in,
    an eye appears inside the screen, a couple of crack lines animate
    outward from it (something breaking through), everything holds for a
    beat, then the hook text fades in underneath. Same brand primitives as
    animate_clean_smiley(): rounded_rect_points() + wobbly_animated() for
    the phone body and screen outline (proving the "straight/rounded shape"
    case, not just hand-drawn curves), quad_bezier() + wobbly_animated()
    for the eye outline and cracks, grow_circle() for the pupil, and
    fade_in_text() for the headline.
    """
    from generate_post import base_card, rounded_rect_points, quad_bezier, pink, font, BOLD

    img, d = base_card()
    rec = FrameRecorder(img, d, out_dir)

    cx = 540

    # ---- phone body ----
    body_pts = rounded_rect_points(390, 140, 690, 640, 40)
    wobbly_animated(rec, body_pts, cream3, 6, 1.0, seed=201, num_frames=20)

    # ---- screen inset ----
    screen_pts = rounded_rect_points(422, 188, 658, 592, 20)
    wobbly_animated(rec, screen_pts, cream3, 3, 0.8, seed=202, num_frames=10)

    # ---- eye outline (upper lid arc + lower lid arc, one continuous loop) ----
    ecx, ecy = cx, 390
    left, right = (ecx - 70, ecy), (ecx + 70, ecy)
    upper = quad_bezier(left, (ecx, ecy - 45), right, steps=40)
    lower = quad_bezier(right, (ecx, ecy + 30), left, steps=40)
    eye_pts = upper + lower[1:]
    wobbly_animated(rec, eye_pts, cream3, 5, 0.9, seed=203, num_frames=14)

    # ---- pupil: grows in rather than drawing stroke-by-stroke ----
    grow_circle(rec, ecx, ecy, max_r=28, color=orange3, num_frames=10)

    # ---- crack lines radiating out from the eye ----
    crack1 = quad_bezier((ecx - 55, ecy - 35), (ecx - 90, ecy - 90), (ecx - 130, ecy - 170), steps=30)
    wobbly_animated(rec, crack1, pink, 4, 1.0, seed=204, num_frames=8)
    crack2 = quad_bezier((ecx + 55, ecy - 35), (ecx + 95, ecy - 85), (ecx + 140, ecy - 160), steps=30)
    wobbly_animated(rec, crack2, pink, 4, 1.0, seed=205, num_frames=8)

    # ---- hold on the completed illustration (~0.5s) ----
    rec.hold_last_frame(10)

    # ---- hook text fades in underneath ----
    hook_font = font(BOLD, 52)
    fade_in_text(
        rec,
        ["Is someone already", "inside your phone?"],
        hook_font, cream3, x='center', y=730, line_height=68, num_frames=15,
    )

    # ---- final hold on illustration + text (~1s) ----
    rec.hold_last_frame(20)

    total_frames = rec.index - 1
    assemble_video(out_dir, video_path, fps=fps)
    return total_frames


def animate_brand_intro(out_dir, video_path, fps=20):
    """15-second standalone brand intro: the bracket-person mark draws in
    stroke by stroke (brackets, then the head circle, then the body arc --
    same construction order as draw_icon()), the wordmark fades in below
    it, the short-form motto types out terminal-style, the full tagline
    fades in under that, then everything holds together as one lockup for
    the final 2 seconds. Not tied to any specific post -- this introduces
    the brand itself, for someone landing on the profile cold.

    Frame budget at 20fps/15s = 300 frames total, split:
      0.0-3.0s (60f): icon draws in
      3.0-5.0s (40f): wordmark fades in
      5.0-8.0s (60f): motto types out
      8.0-13.0s (100f): tagline fades in, then holds
      13.0-15.0s (40f): full lockup holds

    Colors/text match the site exactly: wordmark split from the
    `.wordmark` styling in style.css, motto from `.hero-motto`
    ("FOR HUMAN. FOR PRIVACY." -- HUMAN/PRIVACY bold orange, rest
    cream-dim), tagline from `.hero-tagline`
    ("USE AI. REMAIN HUMAN. PRIVACY MATTERS." -- AI/HUMAN/PRIVACY bold
    orange, rest cream) -- see CLAUDE.md's "Motto vs. tagline" note.
    """
    from generate_post import base_card, quad_bezier, gray_light, font, BOLD, MONO_BOLD

    img, d = base_card()
    rec = FrameRecorder(img, d, out_dir)

    # ---- stage 1 (0-3s / 60 frames): brand icon draws in ----
    # Local coordinate space matches draw_icon() in generate_post.py
    # exactly (brackets (38,16)-(130,84), head circle at (75,38) r=13,
    # body arc centered (75,78) r=17), scaled up ISCALE=4x and centered
    # in the upper half of the 1080x1080 canvas for a video-sized mark.
    ISCALE = 4.0
    OFFX, OFFY = 540 - 75 * ISCALE, 300 - 55.5 * ISCALE

    def xf(pt):
        return (OFFX + pt[0] * ISCALE, OFFY + pt[1] * ISCALE)

    left_bracket = quad_bezier(xf((38, 16)), xf((20, 50)), xf((38, 84)), steps=60)
    wobbly_animated(rec, left_bracket, cream3, 10, 1.2, seed=301, num_frames=14)

    right_bracket = quad_bezier(xf((112, 16)), xf((130, 50)), xf((112, 84)), steps=60)
    wobbly_animated(rec, right_bracket, cream3, 10, 1.2, seed=302, num_frames=14)

    head_cx, head_cy = xf((75, 38))
    head_r = 13 * ISCALE
    grow_circle(rec, head_cx, head_cy, max_r=head_r, color=orange3, num_frames=10)

    body_arc = [xf((75 + 17 * math.cos(math.radians(a)), 78 + 17 * math.sin(math.radians(a))))
                for a in range(180, 361, 4)]
    wobbly_animated(rec, body_arc, orange3, 7, 1.0, seed=303, num_frames=12)

    rec.hold_last_frame(10)  # 50 + 10 = 60 frames, exactly 3.0s

    # ---- stage 2 (3-5s / 40 frames): wordmark fades in ----
    wordmark_font = font(BOLD, 88)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=500, num_frames=30)
    rec.hold_last_frame(10)  # 30 + 10 = 40 frames, exactly 2.0s

    # ---- stage 3 (5-8s / 60 frames): motto types out ----
    motto_font = font(MONO_BOLD, 32)
    motto_text = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    motto_full = ''.join(s for s, _ in motto_text)
    motto_w = ImageDraw.Draw(rec.img).textlength(motto_full, font=motto_font)
    motto_x = (1080 - motto_w) / 2
    type_text_animated(rec, motto_text, motto_font, x=motto_x, y=630, num_frames=45)
    rec.hold_last_frame(15)  # 45 + 15 = 60 frames, exactly 3.0s

    # ---- stage 4 (8-13s / 100 frames): full tagline fades in, then holds ----
    tagline_font = font(MONO_BOLD, 30)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=700, num_frames=40)
    rec.hold_last_frame(60)  # 40 + 60 = 100 frames, exactly 5.0s

    # ---- stage 5 (13-15s / 40 frames): full lockup holds ----
    rec.hold_last_frame(40)  # exactly 2.0s

    total_frames = rec.index - 1
    assemble_video(out_dir, video_path, fps=fps)
    return total_frames


def animate_brand_intro_hook(out_dir, video_path, fps=20):
    """Alternate cut of animate_brand_intro() with a scroll-stopping cold
    open instead of leading with the logo. Same final lockup (icon,
    wordmark, motto, tagline), same 15s/20fps/300-frame target -- the
    difference is the first 3 seconds, which mimic the site's own real
    boot-sequence trust check (initBootSequence in site.js: "0 trackers,
    0 ad scripts, 0 cookies found" on every page load) instead of just
    drawing the icon. This is a genuine hook rather than a borrowed
    trope -- it's literally what the site already does, just brought to
    the front of the video instead of buried in a page-load animation.

    Frame budget at 20fps/15s = 300 frames total, split:
      0.0-0.5s (10f): blinking cursor, no branding yet
      0.5-2.5s (40f): scan lines type out ("scanning this account...",
                       trackers/ads/data-sold found: 0, 0, 0 in green)
      2.5-3.0s (10f): flash cut, canvas resets clean
      3.0-5.5s (50f): icon draws in
      5.5-7.5s (40f): wordmark fades in
      7.5-10.5s (60f): motto types out
      10.5-13.5s (60f): tagline fades in, then holds
      13.5-15.0s (30f): full lockup holds
    """
    from generate_post import base_card, quad_bezier, gray_light, green, font, BOLD, MONO_BOLD, MONO_REG

    img, d = base_card()
    rec = FrameRecorder(img, d, out_dir)

    # ---- stage 1 (0-0.5s / 10 frames): blinking cursor, cold open ----
    cursor_x, cursor_y, bar_w, bar_h = 140, 400, 16, 40
    blink_pattern = [True, True, True, False, False, False, True, True, True, True]
    base = rec.img.copy()
    for visible in blink_pattern:
        frame = base.copy()
        if visible:
            ImageDraw.Draw(frame).rectangle(
                [cursor_x, cursor_y, cursor_x + bar_w, cursor_y + bar_h], fill=orange3)
        frame.save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
        rec.index += 1
    rec.img, rec.draw = base, ImageDraw.Draw(base)  # cursor never persists -- purely a blink

    # ---- stage 2 (0.5-2.5s / 40 frames): fake live scan types out ----
    scan_font = font(MONO_REG, 34)
    line1 = [("$ scanning this account...", gray_light)]
    type_text_animated(rec, line1, scan_font, x=cursor_x, y=380, num_frames=14)

    line2 = [("trackers found: ", cream3), ("0", green)]
    type_text_animated(rec, line2, scan_font, x=cursor_x, y=460, num_frames=8)

    line3 = [("ads found: ", cream3), ("0", green)]
    type_text_animated(rec, line3, scan_font, x=cursor_x, y=540, num_frames=8)

    line4 = [("your data sold: ", cream3), ("0", green)]
    type_text_animated(rec, line4, scan_font, x=cursor_x, y=620, num_frames=8)

    rec.hold_last_frame(2)  # 14+8+8+8 + 2 = 40 frames, exactly 2.0s

    # ---- stage 3 (2.5-3.0s / 10 frames): flash cut, canvas resets clean ----
    rec.hold_last_frame(2)
    flash = Image.new("RGB", rec.img.size, orange3)
    rec.img = flash
    for _ in range(3):
        rec.snapshot()
    fresh_img, fresh_d = base_card()
    rec.img, rec.draw = fresh_img, fresh_d
    for _ in range(5):
        rec.snapshot()
    # 2 (hold) + 3 (flash) + 5 (fresh) = 10 frames, exactly 0.5s

    # ---- stage 4 (3.0-5.5s / 50 frames): brand icon draws in ----
    # Same local-coordinate construction as draw_icon()/animate_brand_intro().
    ISCALE = 4.0
    OFFX, OFFY = 540 - 75 * ISCALE, 300 - 55.5 * ISCALE

    def xf(pt):
        return (OFFX + pt[0] * ISCALE, OFFY + pt[1] * ISCALE)

    left_bracket = quad_bezier(xf((38, 16)), xf((20, 50)), xf((38, 84)), steps=60)
    wobbly_animated(rec, left_bracket, cream3, 10, 1.2, seed=301, num_frames=12)

    right_bracket = quad_bezier(xf((112, 16)), xf((130, 50)), xf((112, 84)), steps=60)
    wobbly_animated(rec, right_bracket, cream3, 10, 1.2, seed=302, num_frames=12)

    head_cx, head_cy = xf((75, 38))
    head_r = 13 * ISCALE
    grow_circle(rec, head_cx, head_cy, max_r=head_r, color=orange3, num_frames=8)

    body_arc = [xf((75 + 17 * math.cos(math.radians(a)), 78 + 17 * math.sin(math.radians(a))))
                for a in range(180, 361, 4)]
    wobbly_animated(rec, body_arc, orange3, 7, 1.0, seed=303, num_frames=10)

    rec.hold_last_frame(8)  # 12+12+8+10 + 8 = 50 frames, exactly 2.5s

    # ---- stage 5 (5.5-7.5s / 40 frames): wordmark fades in ----
    wordmark_font = font(BOLD, 88)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=500, num_frames=30)
    rec.hold_last_frame(10)  # 30 + 10 = 40 frames, exactly 2.0s

    # ---- stage 6 (7.5-10.5s / 60 frames): motto types out ----
    motto_font = font(MONO_BOLD, 32)
    motto_text = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    motto_full = ''.join(s for s, _ in motto_text)
    motto_w = ImageDraw.Draw(rec.img).textlength(motto_full, font=motto_font)
    motto_x = (1080 - motto_w) / 2
    type_text_animated(rec, motto_text, motto_font, x=motto_x, y=630, num_frames=45)
    rec.hold_last_frame(15)  # 45 + 15 = 60 frames, exactly 3.0s

    # ---- stage 7 (10.5-13.5s / 60 frames): full tagline fades in, then holds ----
    tagline_font = font(MONO_BOLD, 30)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=700, num_frames=40)
    rec.hold_last_frame(20)  # 40 + 20 = 60 frames, exactly 3.0s

    # ---- stage 8 (13.5-15s / 30 frames): full lockup holds ----
    rec.hold_last_frame(30)  # exactly 1.5s

    total_frames = rec.index - 1
    assemble_video(out_dir, video_path, fps=fps)
    return total_frames


def animate_brand_story(out_dir, video_path, fps=20):
    """Brand story, restructured a fifth time around real terminal
    scrollback instead of hard screen-clears -- the previous version's
    clear_screen() typed each new command BEFORE wiping the old output
    away, so for one visible stretch the new command was drawn directly
    on top of the still-onscreen previous line (a real bug, caught by
    scanning dense frame samples across a full render rather than just
    the handful of spot-checks used before: "not philosophy.md"-style
    garbling was visible for several frames at every act transition).
    This version fixes that at the root by never wiping at all -- each
    act's finished content dims to ~50% brightness and scrolls upward
    (scroll_content()/dim_region()) before the next act's command starts
    typing at the same fixed position, so old and new content are never
    on screen, unstyled, at the same time. Scrollback also fixes the
    "big blank canvas under two lines of text" look every earlier
    version had: history visibly accumulates as the video progresses
    instead of vanishing.

      Act 0 (~5s, chrome, ACTIVE_Y fixed): `$ whoami` types in, cursor
        blinks, then the response types in via a decrypt/scramble
        effect (type_decrypt() -- reserved for `>` response lines only,
        never the `$` commands, so it stays a purposeful accent instead
        of overused everywhere): "not a company. not a bot. just one
        person, explaining this properly."
      Act 1 (~7s): previous content dims+scrolls up first. `$ cat
        philosophy.md`, blink, decrypt-reveals: "plain language over
        jargon. no fear-mongering. one real person, not a company."
      Act 2 (~7s): dims+scrolls. `$ ls ./pillars`, blink, a brief fake
        scan bar (`[████░░░░░░] scanning pillars...`) for anticipation,
        then all 9 real content pillars appear one at a time like real
        `ls` directory output (reveal_line() -- instant per-entry, not
        typed, ~2.5/second), each colored to its real site accent (see
        the 9-pillar table in CLAUDE.md).
      Act 3 (~6s): dims+scrolls. `$ ls ./site`, blink, scan bar, then
        real site filenames revealed the same way -- posts/, news/,
        toolkit.html, tools.html, you_check.quiz, glossary.md,
        on(my).mind/ -- directories in blue, files in cream.
      (typing stops; fade to black -- a bigger mode change than the
      scroll transitions, since this leaves the terminal look entirely
      -- then a deliberately silent hold before the reveal)
      Act 4 (~7s): the one calm non-typed moment -- the brand icon draws
        in with a subtler, less-wobbly stroke than the site's usual
        doodle jitter, wordmark fades in, motto types out character by
        character, tagline fades in.
      Act 5 (~4s, terminal chrome returns fresh, no scroll -- ends on
        both lines visible together as the closing screen): `$ follow
        ./stayhumansec`, cursor blinks, then a decrypt-revealed "one new
        file, every day."

    Every character typed anywhere (Acts 0/1/5's commands, Act 4's
    motto) logs to rec.click_frames and gets a real keystroke sound
    extracted from a recording (instagram/assets/sfx/keyboard_typing.mp3
    -- _extract_keyboard_clicks()); decrypt-revealed response lines log
    a sparser click every 3rd scramble frame (a "static" texture, not a
    per-character keystroke); each Act 2/3 directory-entry reveal logs
    one click. Cursor-blink pauses and the scan-bar fill log to
    rec.blink_frames for a soft synthesized ambient tick
    (_synth_blink_tick_samples()). Both are mixed by
    synthesize_sound_track() and muxed onto the silent video
    (mux_audio()) automatically before this function returns. The hold
    right before Act 4's icon reveal logs neither, for genuine silence.

    Total runtime is roughly 34-38s -- longer again than the previous
    cut, since scan bars and the decrypt effect's staggered reveal both
    add time on top of the already-realistic typing/reading pacing --
    exact total frame count is returned by the function and should be
    read from there / verified via ffprobe, not assumed.
    """
    from generate_post import (base_card, gray_light, blue, green, gold, pink, violet, quad_bezier,
                                font, BOLD, MONO_BOLD, MONO_REG)

    CORAL = (255, 138, 106)  # story-time's one-off accent, not a CSS custom property

    img, d = base_card()
    rec = FrameRecorder(img, d, out_dir)

    CPS = 24  # characters/second -- realistic typing speed, upper-mid of the 15-25 range asked for
    LEFT_X = 70
    LINE_H = 62
    ACTIVE_Y = 120  # fixed y where every act's content starts typing -- history scrolls above it
    CONTENT_TOP = 96  # just below the chrome bar -- scroll_content()'s clip boundary
    PROMPT_FONT = font(MONO_BOLD, 34)
    OUTPUT_FONT = font(MONO_REG, 34)

    def type_chars(char_count):
        return max(8, round(char_count / CPS * fps))

    def type_line(segments, y, font_obj=OUTPUT_FONT, x=LEFT_X):
        full_text = ''.join(s for s, _ in segments)
        type_text_animated(rec, segments, font_obj, x=x, y=y, num_frames=type_chars(len(full_text)))

    def type_output(text, y, max_w=940):
        """Types a "> " output line via the decrypt/scramble effect
        (type_decrypt()) -- word-wrapped onto as many lines as it needs
        to stay within max_w, since a single long sentence at this font
        size can easily be wider than the 1080px canvas (a real bug
        caught and fixed here: two lines were previously running off
        the right edge with no wrapping at all). The "> " marker itself
        is drawn instantly, un-scrambled -- only the response text gets
        the decrypt effect, keeping it purposeful rather than applied to
        every character on screen. Returns (next_free_y,
        full_text_length) so the caller can size the reading hold off
        the original sentence and scroll by the actual space used."""
        prefix = "> "
        prefix_w = ImageDraw.Draw(rec.img).textlength(prefix, font=OUTPUT_FONT)
        avail_w = max_w - prefix_w
        words = text.split(' ')
        lines, cur = [], ''
        probe = ImageDraw.Draw(rec.img)
        for w in words:
            trial = (cur + ' ' + w).strip()
            if probe.textlength(trial, font=OUTPUT_FONT) <= avail_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        cy = y
        for i, ln in enumerate(lines):
            if i == 0:
                rec.draw.text((LEFT_X, cy), prefix, font=OUTPUT_FONT, fill=gray_light)
                rec.snapshot()
                type_decrypt(rec, [(ln, cream3)], OUTPUT_FONT, LEFT_X + prefix_w, cy, type_chars(len(ln)))
            else:
                type_decrypt(rec, [(ln, cream3)], OUTPUT_FONT, LEFT_X + prefix_w, cy, type_chars(len(ln)))
            cy += LINE_H
        return cy, len(text)

    def reading_hold(text_len):
        rec.hold_last_frame(max(14, round((0.3 + text_len * 0.018) * fps)))

    def cursor_blink_pause(x, y, blinks=2, on_frames=4, off_frames=4, color=None):
        """A held beat with the cursor blinking on/off -- the "suspense"
        moment after a command types in. Each blink-on logs to
        rec.blink_frames for a soft ambient tick; the off phases are
        genuinely silent. Leaves rec.img/draw exactly as they were
        before this call (the blink never persists)."""
        color = color or orange3
        base = rec.img.copy()
        bar_w, bar_h = 14, 30
        for _ in range(blinks):
            on_frame = base.copy()
            ImageDraw.Draw(on_frame).rectangle([x, y, x + bar_w, y + bar_h], fill=color)
            for i in range(on_frames):
                on_frame.save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
                if i == 0:
                    rec.blink_frames.append(rec.index)
                rec.index += 1
            for _ in range(off_frames):
                base.save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
                rec.index += 1
        rec.img, rec.draw = base, ImageDraw.Draw(base)

    def reveal_line(text, color, y, appear_frames=8):
        """Draws one line instantly (no char-by-char typing, no decrypt
        effect) and holds it -- how `ls` actually prints entries, one
        after another. Still logs one real keystroke click so the
        directory-listing acts stay sonically consistent."""
        rec.draw.text((LEFT_X, y), text, font=OUTPUT_FONT, fill=color)
        rec.snapshot()
        rec.click_frames.append(rec.index - 1)
        rec.hold_last_frame(appear_frames - 1)

    def scan_bar(label, y, num_frames=12, bar_width=10):
        """A brief fake progress bar (`[████░░░░░░] label`) that fills
        in then holds on the completed bar for a moment, purely for
        anticipation before a directory listing -- then erases itself
        (rec.img reverts to what it was before this call) so the
        listing starts on a clean line at the same y. Every 3rd fill
        step logs a soft ambient tick, matching the "something's
        working" feel without competing with real keystroke clicks."""
        base = rec.img.copy()
        fill_frames = max(1, num_frames - 4)
        for step in range(1, fill_frames + 1):
            filled = min(bar_width, round(bar_width * step / fill_frames))
            bar_text = f"[{'█' * filled}{'░' * (bar_width - filled)}] {label}"
            frame = base.copy()
            ImageDraw.Draw(frame).text((LEFT_X, y), bar_text, font=OUTPUT_FONT, fill=gray_light)
            frame.save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
            if step % 3 == 0:
                rec.blink_frames.append(rec.index)
            rec.index += 1
        rec.hold_last_frame(4)
        rec.img, rec.draw = base, ImageDraw.Draw(base)

    def scroll_to_active(prev_content_height, num_frames=10):
        """Dims the previous act's just-finished content (currently
        drawn at full brightness in [ACTIVE_Y, ACTIVE_Y+prev_content_
        height)) to history-level opacity, then scrolls the whole
        content band upward by exactly that height so it settles just
        above ACTIVE_Y and the next act's content can start typing at
        ACTIVE_Y again -- the "scrollback" transition that replaces the
        old hard clear_screen() wipe (and the overlap bug that came with
        typing a new command before the wipe removed the old one)."""
        if prev_content_height <= 0:
            return
        dim_region(rec.img, ACTIVE_Y, ACTIVE_Y + prev_content_height, factor=0.45)
        scroll_content(rec, chrome_base, prev_content_height, content_top=CONTENT_TOP, num_frames=num_frames)

    # ================= Act 0: $ whoami =================
    draw_terminal_chrome(rec)
    chrome_base = rec.img.copy()

    type_line([("$ ", orange3), ("whoami", gray_light)], ACTIVE_Y, PROMPT_FONT)
    cmd0_end_x = LEFT_X + ImageDraw.Draw(rec.img).textlength("$ whoami", font=PROMPT_FONT)
    cursor_blink_pause(cmd0_end_x + 6, ACTIVE_Y + 2)

    line0 = "not a company. not a bot. just one person, explaining this properly."
    cy0, n0 = type_output(line0, ACTIVE_Y + LINE_H)
    reading_hold(n0)
    act0_height = cy0 - ACTIVE_Y

    # ================= Act 1: $ cat philosophy.md =================
    scroll_to_active(act0_height)
    type_line([("$ ", orange3), ("cat philosophy.md", gray_light)], ACTIVE_Y, PROMPT_FONT)
    cmd1_end_x = LEFT_X + ImageDraw.Draw(rec.img).textlength("$ cat philosophy.md", font=PROMPT_FONT)
    cursor_blink_pause(cmd1_end_x + 6, ACTIVE_Y + 2)

    line1 = "plain language over jargon. no fear-mongering. one real person, not a company."
    cy1, n1 = type_output(line1, ACTIVE_Y + LINE_H)
    reading_hold(n1)
    act1_height = cy1 - ACTIVE_Y

    # ================= Act 2: $ ls ./pillars =================
    scroll_to_active(act1_height)
    type_line([("$ ", orange3), ("ls ./pillars", gray_light)], ACTIVE_Y, PROMPT_FONT)
    cmd2_end_x = LEFT_X + ImageDraw.Draw(rec.img).textlength("$ ls ./pillars", font=PROMPT_FONT)
    cursor_blink_pause(cmd2_end_x + 6, ACTIVE_Y + 2)
    scan_bar("scanning pillars...", ACTIVE_Y + LINE_H)

    pillars = [
        ("cyber-news/", blue), ("stay-safe/", orange3), ("cyber-basics/", green),
        ("ai-watch/", violet), ("ai-news/", violet), ("myth-busting/", gold),
        ("case-file/", pink), ("deep-dive/", green), ("story-time/", CORAL),
    ]
    py = ACTIVE_Y + LINE_H
    for name, color in pillars:
        reveal_line(name, color, py, appear_frames=8)
        py += LINE_H - 6
    rec.hold_last_frame(20)
    act2_height = py - ACTIVE_Y

    # ================= Act 3: $ ls ./site =================
    scroll_to_active(act2_height)
    type_line([("$ ", orange3), ("ls ./site", gray_light)], ACTIVE_Y, PROMPT_FONT)
    cmd3_end_x = LEFT_X + ImageDraw.Draw(rec.img).textlength("$ ls ./site", font=PROMPT_FONT)
    cursor_blink_pause(cmd3_end_x + 6, ACTIVE_Y + 2)
    scan_bar("scanning site...", ACTIVE_Y + LINE_H)

    features = [
        ("posts/", blue), ("news/", blue), ("toolkit.html", cream3), ("tools.html", cream3),
        ("you_check.quiz", cream3), ("glossary.md", cream3), ("on(my).mind/", blue),
    ]
    fy = ACTIVE_Y + LINE_H
    for name, color in features:
        reveal_line(name, color, fy, appear_frames=8)
        fy += LINE_H - 6
    rec.hold_last_frame(20)

    # ---- handoff: typing stops, a fade to black (a bigger mode change
    # than the scroll transitions above), then a genuinely silent hold
    # (no clicks, no ticks) right before the brand icon reveals -- real
    # silence is what makes that moment land ----
    black = Image.new("RGB", rec.img.size, (0, 0, 0))
    start_img = rec.img.convert('RGBA')
    end_img = black.convert('RGBA')
    for step in range(1, 9):
        frame = Image.blend(start_img, end_img, step / 8)
        frame.convert('RGB').save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
        rec.index += 1
    fresh_img, fresh_d = base_card()
    rec.img, rec.draw = fresh_img, fresh_d
    rec.hold_last_frame(14)

    # ================= Act 4: brand lockup -- the one calm, non-typed
    # moment. The icon draws in with a subtler, less-wobbly stroke than
    # the site's usual doodle jitter (jitter_amt 0.4-0.45 here vs. the
    # usual 1.0-1.2), the only illustration in the whole video. =================
    ISCALE = 4.0
    OFFX, OFFY = 540 - 75 * ISCALE, 300 - 55.5 * ISCALE

    def xf(pt):
        return (OFFX + pt[0] * ISCALE, OFFY + pt[1] * ISCALE)

    left_bracket = quad_bezier(xf((38, 16)), xf((20, 50)), xf((38, 84)), steps=60)
    wobbly_animated(rec, left_bracket, cream3, 8, 0.45, seed=301, num_frames=10)
    right_bracket = quad_bezier(xf((112, 16)), xf((130, 50)), xf((112, 84)), steps=60)
    wobbly_animated(rec, right_bracket, cream3, 8, 0.45, seed=302, num_frames=10)
    head_cx, head_cy = xf((75, 38))
    grow_circle(rec, head_cx, head_cy, max_r=13 * ISCALE, color=orange3, num_frames=8)
    body_arc = [xf((75 + 17 * math.cos(math.radians(a)), 78 + 17 * math.sin(math.radians(a))))
                for a in range(180, 361, 4)]
    wobbly_animated(rec, body_arc, orange3, 6, 0.4, seed=303, num_frames=10)
    rec.hold_last_frame(6)

    wordmark_font = font(BOLD, 88)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=500, num_frames=16)
    rec.hold_last_frame(5)

    motto_font = font(MONO_BOLD, 32)
    motto_text = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    motto_full = ''.join(s for s, _ in motto_text)
    motto_w = ImageDraw.Draw(rec.img).textlength(motto_full, font=motto_font)
    type_text_animated(rec, motto_text, motto_font, x=(1080 - motto_w) / 2, y=630, num_frames=type_chars(len(motto_full)))
    rec.hold_last_frame(4)

    tagline_font = font(MONO_BOLD, 30)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=700, num_frames=18)
    rec.hold_last_frame(8)

    # ================= Act 5: terminal chrome returns fresh -- ends on
    # both lines visible together, no clear this time (the closing
    # screen). =================
    img2, d2 = base_card()
    rec.img, rec.draw = img2, d2
    draw_terminal_chrome(rec)

    y5 = ACTIVE_Y
    cmd5 = "follow ./stayhumansec"
    type_line([("$ ", orange3), (cmd5, gray_light)], y5, PROMPT_FONT)
    cmd5_end_x = LEFT_X + ImageDraw.Draw(rec.img).textlength(f"$ {cmd5}", font=PROMPT_FONT)
    cursor_blink_pause(cmd5_end_x + 6, y5 + 2)

    line_final = "one new file, every day."
    type_output(line_final, y5 + LINE_H)
    rec.hold_last_frame(28)

    total_frames = rec.index - 1

    silent_path = video_path + ".silent.mp4"
    assemble_video(out_dir, silent_path, fps=fps)

    keyboard_audio_path = os.path.join(os.path.dirname(__file__), "assets", "sfx", "keyboard_typing.mp3")
    audio_path = os.path.join(out_dir, "_typing_clicks.wav")
    synthesize_sound_track(keyboard_audio_path, rec.click_frames, rec.blink_frames, fps, total_frames, audio_path)
    mux_audio(silent_path, audio_path, video_path)
    os.remove(silent_path)
    os.remove(audio_path)

    return total_frames


def animate_silhouette_story(out_dir, video_path, fps=20):
    """Full 6-act debut brand video, built on the silhouette mechanism's
    core idea (continuous per-frame parametric interpolation instead of
    stroke accumulation or character typing) and extended across the
    whole story -- pillars, philosophy, site, lockup, CTA. No fixed
    time budget: every beat runs as long as it needs to read clearly,
    not compressed to hit a duration target, since this is the first
    video post and is meant to feel complete rather than fast.

    Two specific fixes to Act 1's earlier "clumsy" feel, both about
    varying the motion instead of applying one uniform easing curve to
    everything:
      - Asymmetric timing: the head-lower/phone-reveal motion now uses
        _ease_out_cubic() (fast start, slow arrival) instead of
        _smoothstep()'s symmetric ease, and the shoulder-tension rise
        (and its mirrored relax) uses _ease_out_back() with a small
        overshoot -- tensing slightly past its final position before
        easing back, instead of arriving directly. Different motions now
        read as physically distinct instead of one formula stamped on
        every parameter.
      - A more convincing phone: narrower width:height ratio (76:178,
        was 92:168), a thinner outline (2px) distinct from the
        silhouette's own outline (5px, orange), and the brand-icon
        reflection is now inset specifically within the screen rect
        (computed from the phone's own geometry, not just placed near
        it) with a soft Gaussian-blur bloom composited underneath the
        sharp icon, so it reads as the icon emitting light onto the
        screen rather than a flat sticker.

      Act 1: silhouette fades in -> head lowers/compresses toward a
        phone fading in below it (asymmetric ease) -> shoulders tense
        (ease-out-back overshoot) while the phone's glow cools cream to
        cold blue-gray (smoothstep -- only the shoulder motion gets the
        overshoot, per brief), held long with a slow controlled pulse
        -> the brand icon fades in on the phone screen as an inset,
        bloomed reflection -> shoulders relax and the glow warms back,
        mirroring the tense-up with the same ease-out-back curve.
      Act 2: crossfades from the resolved silhouette into a 3x3 grid of
        all 9 real content pillars -- each icon pops in (scale + alpha,
        ease-out-back) then its label fades in beside it, color-coded to
        that pillar's real accent (see the 9-pillar table in CLAUDE.md),
        one at a time with room to actually land before the next starts.
      Act 3: crossfades to clean Poppins typography (not typed/terminal)
        -- "Not a company. Not a bot. Just one person, explaining this
        properly." -- each line fading in below the last, held long
        enough to read comfortably.
      Act 4: crossfades to a clean list of what the site offers (Posts,
        News, Toolkit, You Check., Glossary, on(my).mind), same calm
        typography as Act 3, each line fading in with a colored marker.
      Act 5: crossfades to the brand lockup -- icon fades in (pure alpha,
        no stroke draw), then wordmark, motto, tagline, calm and steady,
        matching Act 1's resolved tone.
      Act 6: "Like. Share. Follow. Comment." fades in beneath the still-
        visible lockup, then a warm, personal closer fades in under
        that -- "Trust me, it's worth it." -- written as a genuine aside
        from the person behind the account, not a corporate CTA line.

    Sound: added deliberately, not everywhere. A continuous low ambient
    drone (_synth_drone_segment()) rises in under Act 1's tension ramp,
    sustains through the held tense moment (through the icon reveal,
    since the posture hasn't resolved yet) with a slow pitch wobble, and
    fades out as the shoulders relax -- this is the one beat in the
    video where sound genuinely reinforces an emotional read, so it gets
    one. A soft chime marks the icon-reflection reveal. A soft ambient
    tick marks each Act 2 pillar icon landing. Acts 3-6 get no sound at
    all on purpose: those are reading beats, and audio there would
    compete with reading time rather than add anything --
    synthesize_silhouette_audio() keeps this mix deliberately sparse
    rather than scoring every single moment.

    Every act transition is a crossfade to a blank card
    (_fade_to_clean_base()), never a hard cut. Total runtime is
    substantial (a first-post debut video, not a quick hook) -- exact
    total frame count is returned by the function and should be read
    from there / verified via ffprobe, not assumed.
    """
    from generate_post import (base_card, gray_light, blue, green, gold, pink, violet,
                                font, BOLD, REG, MONO_BOLD, draw_icon as draw_brand_icon)

    CORAL = (255, 138, 106)

    base_img, base_draw = base_card()
    rec = FrameRecorder(base_img, base_draw, out_dir)

    drone_events = []
    chime_frames = []
    tick_frames = []

    HEAD_CX = 540
    HEAD_RX = 66
    HEAD_RY_UP, HEAD_RY_DOWN = 66, 58
    HEAD_CY_UP, HEAD_CY_DOWN = 360, 400
    SHOULDER_TOP_RELAXED, SHOULDER_TOP_TENSE = 470, 452
    SHOULDER_BOTTOM = 660
    SHOULDER_HALF_TOP, SHOULDER_HALF_BOTTOM = 65, 145
    OUTLINE_W = 5
    SIL_FILL = (0, 0, 0)

    PHONE_W, PHONE_H = 76, 178
    PHONE_CX, PHONE_CY = 540, 560
    PHONE_CORNER = 20
    PHONE_OUTLINE_W = 2
    SCREEN_INSET = 9
    SCREEN_RECT = (PHONE_CX - PHONE_W / 2 + SCREEN_INSET, PHONE_CY - PHONE_H / 2 + SCREEN_INSET,
                    PHONE_CX + PHONE_W / 2 - SCREEN_INSET, PHONE_CY + PHONE_H / 2 - SCREEN_INSET)

    GLOW_WARM = cream3
    GLOW_COLD = (120, 150, 210)

    def lerp(a, b, t):
        return a + (b - a) * t

    def lerp_color(c1, c2, t):
        return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))

    def silhouette_overlay(size, head_cy, head_ry, shoulder_top, alpha):
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        top_l = (HEAD_CX - SHOULDER_HALF_TOP, shoulder_top)
        top_r = (HEAD_CX + SHOULDER_HALF_TOP, shoulder_top)
        bot_r = (HEAD_CX + SHOULDER_HALF_BOTTOM, SHOULDER_BOTTOM)
        bot_l = (HEAD_CX - SHOULDER_HALF_BOTTOM, SHOULDER_BOTTOM)
        od.polygon([top_l, top_r, bot_r, bot_l], fill=SIL_FILL + (255,))
        head_box = [HEAD_CX - HEAD_RX, head_cy - head_ry, HEAD_CX + HEAD_RX, head_cy + head_ry]
        od.ellipse(head_box, fill=SIL_FILL + (255,))
        od.polygon([top_l, top_r, bot_r, bot_l], outline=orange3 + (255,), width=OUTLINE_W)
        od.ellipse(head_box, outline=orange3 + (255,), width=OUTLINE_W)
        if alpha < 1.0:
            overlay.putalpha(overlay.split()[3].point(lambda a, m=alpha: int(a * m)))
        return overlay

    def phone_overlay(size, glow_color, alpha):
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        x0, y0 = PHONE_CX - PHONE_W / 2, PHONE_CY - PHONE_H / 2
        x1, y1 = PHONE_CX + PHONE_W / 2, PHONE_CY + PHONE_H / 2
        od.rounded_rectangle([x0, y0, x1, y1], radius=PHONE_CORNER, fill=(10, 10, 10, 255),
                              outline=gray_light + (255,), width=PHONE_OUTLINE_W)
        sx0, sy0, sx1, sy1 = SCREEN_RECT
        od.rounded_rectangle([sx0, sy0, sx1, sy1], radius=max(1, PHONE_CORNER - 8), fill=glow_color + (235,))
        if alpha < 1.0:
            overlay.putalpha(overlay.split()[3].point(lambda a, m=alpha: int(a * m)))
        return overlay

    def icon_reflection_overlay(size, alpha):
        """The brand icon inset within the phone's screen rect, with a
        soft Gaussian-blur bloom composited underneath the sharp icon --
        reads as the icon emitting light onto the screen, not a flat
        sticker placed on top of it."""
        sx0, sy0, sx1, sy1 = SCREEN_RECT
        screen_w, screen_h = sx1 - sx0, sy1 - sy0
        scale = min(screen_w * 0.62 / 110, screen_h * 0.62 / 80)
        offx = sx0 + (screen_w - 110 * scale) / 2 - 20 * scale
        offy = sy0 + (screen_h - 80 * scale) / 2 - 16 * scale
        icon_layer = Image.new('RGBA', size, (0, 0, 0, 0))
        od = ImageDraw.Draw(icon_layer)
        draw_brand_icon(od, offx, offy, scale, cream3 + (255,), orange3 + (255,))
        bloom = icon_layer.filter(ImageFilter.GaussianBlur(6))
        bloom.putalpha(bloom.split()[3].point(lambda a: int(a * 0.55)))
        combined = Image.alpha_composite(bloom, icon_layer)
        if alpha < 1.0:
            combined.putalpha(combined.split()[3].point(lambda a, m=alpha: int(a * m)))
        return combined

    def render(head_cy, head_ry, shoulder_top, figure_alpha, phone_alpha, glow_color, glow_pulse, icon_alpha):
        frame = base_img.copy().convert('RGBA')
        frame = Image.alpha_composite(frame, silhouette_overlay(frame.size, head_cy, head_ry, shoulder_top, figure_alpha))
        if phone_alpha > 0:
            pulsed = tuple(min(255, max(0, int(c * glow_pulse))) for c in glow_color)
            frame = Image.alpha_composite(frame, phone_overlay(frame.size, pulsed, phone_alpha))
        if icon_alpha > 0:
            frame = Image.alpha_composite(frame, icon_reflection_overlay(frame.size, icon_alpha))
        final = frame.convert('RGB')
        final.save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
        rec.index += 1
        rec.img = final
        return final

    # ================= Act 1: silhouette hook =================
    n1 = 26
    for step in range(n1):
        t = _smoothstep(step / (n1 - 1))
        render(HEAD_CY_UP, HEAD_RY_UP, SHOULDER_TOP_RELAXED, t, 0.0, GLOW_WARM, 1.0, 0.0)
    rec.hold_last_frame(12)

    # head lowers/compresses (asymmetric ease-out-cubic -- fast start,
    # slow arrival), phone fades in staggered a few frames behind it
    n2 = 30
    for step in range(n2):
        t = _ease_out_cubic(step / (n2 - 1))
        head_cy = lerp(HEAD_CY_UP, HEAD_CY_DOWN, t)
        head_ry = lerp(HEAD_RY_UP, HEAD_RY_DOWN, t)
        phone_t = _ease_out_cubic(max(0.0, (step - 7) / (n2 - 1 - 7)))
        render(head_cy, head_ry, SHOULDER_TOP_RELAXED, 1.0, phone_t, GLOW_WARM, 1.0, 0.0)
    rec.hold_last_frame(12)

    # tension rises with a slight overshoot-and-settle (ease-out-back),
    # glow cools smoothly (smoothstep -- overshoot is a body-language
    # cue, not appropriate for a color ramp)
    tension_start_frame = rec.index
    n3_ramp = 24
    for step in range(n3_ramp):
        t_shoulder = _ease_out_back(step / (n3_ramp - 1), overshoot=0.6)
        t_glow = _smoothstep(step / (n3_ramp - 1))
        shoulder_top = lerp(SHOULDER_TOP_RELAXED, SHOULDER_TOP_TENSE, t_shoulder)
        glow = lerp_color(GLOW_WARM, GLOW_COLD, t_glow)
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, shoulder_top, 1.0, 1.0, glow, 1.0, 0.0)

    # held tense/cold with a slow controlled pulse, long enough to
    # actually register -- spans through the icon reveal below, since
    # the posture hasn't resolved yet at that point in the story
    n3_hold = 46
    for step in range(n3_hold):
        pulse = 1.0 + 0.12 * math.sin(step * 0.35)
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, SHOULDER_TOP_TENSE, 1.0, 1.0, GLOW_COLD, pulse, 0.0)

    # brand icon fades in as an inset, bloomed reflection -- pure alpha
    # compositing, no stroke draw at all
    n4 = 28
    for step in range(n4):
        t = _smoothstep(step / (n4 - 1))
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, SHOULDER_TOP_TENSE, 1.0, 1.0, GLOW_COLD, 1.0, t)
    chime_frames.append(rec.index - 1)
    rec.hold_last_frame(14)

    # shoulders relax with the same ease-out-back curve as the tense-up
    # (a matching, mirrored overshoot reads as one consistent body,
    # not two different animation styles), glow warms back smoothly
    n5 = 30
    for step in range(n5):
        t_shoulder = _ease_out_back(step / (n5 - 1), overshoot=0.6)
        t_glow = _smoothstep(step / (n5 - 1))
        shoulder_top = lerp(SHOULDER_TOP_TENSE, SHOULDER_TOP_RELAXED, t_shoulder)
        glow = lerp_color(GLOW_COLD, GLOW_WARM, t_glow)
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, shoulder_top, 1.0, 1.0, glow, 1.0, 1.0)
    rec.hold_last_frame(16)

    drone_events.append({
        "start_frame": tension_start_frame,
        "ramp_frames": n3_ramp,
        "hold_frames": n3_hold + n4 + 14,
        "relax_frames": n5,
    })

    # ================= Act 2: pillars =================
    _fade_to_clean_base(rec, num_frames=26)

    def icon_pop_in(kind, cx, cy, target_scale, color, num_frames=16, overshoot=0.65):
        base = rec.img.convert('RGBA')
        for step in range(1, num_frames + 1):
            t = step / num_frames
            eased = _ease_out_back(t, overshoot=overshoot)
            cur_scale = target_scale * max(0.05, eased)
            alpha = min(1.0, t / 0.55)
            overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            draw_clean_icon(od, kind, cx, cy, cur_scale, color, width=4)
            overlay.putalpha(overlay.split()[3].point(lambda a, m=alpha: int(a * m)))
            frame = Image.alpha_composite(base, overlay)
            frame.convert('RGB').save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
            rec.index += 1
        final_overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(final_overlay)
        draw_clean_icon(od, kind, cx, cy, target_scale, color, width=4)
        rec.img = Image.alpha_composite(base, final_overlay).convert('RGB')
        rec.draw = ImageDraw.Draw(rec.img)

    pillar_defs = [
        ('document', blue, "Cyber News"), ('shield', orange3, "Stay Safe"), ('lightbulb', green, "Cyber Basics"),
        ('chip', violet, "AI Watch"), ('broadcast', violet, "AI News"), ('magnifier', gold, "Myth Busting"),
        ('folder', pink, "Case File"), ('chevron', green, "Deep Dive"), ('book', CORAL, "Story Time"),
    ]
    cols = [300, 540, 780]
    rows_y = [300, 540, 780]
    label_font = font(BOLD, 24)
    for i, (kind, color, label) in enumerate(pillar_defs):
        cx, cy = cols[i % 3], rows_y[i // 3]
        icon_pop_in(kind, cx, cy, 1.0, color, num_frames=16)
        tick_frames.append(rec.index - 1)
        lw = ImageDraw.Draw(rec.img).textlength(label, font=label_font)
        fade_in_segments(rec, [(label, color)], label_font, x=cx - lw / 2, y=cy + 55, num_frames=12)
        rec.hold_last_frame(12)
    rec.hold_last_frame(60)

    # ================= Act 3: philosophy =================
    _fade_to_clean_base(rec, num_frames=26)

    philosophy_lines = ["Not a company.", "Not a bot.", "Just one person, explaining this properly."]
    py = 420
    for line in philosophy_lines:
        size = 44
        f = font(BOLD, size)
        lw = ImageDraw.Draw(rec.img).textlength(line, font=f)
        while lw > 920 and size > 26:
            size -= 2
            f = font(BOLD, size)
            lw = ImageDraw.Draw(rec.img).textlength(line, font=f)
        fade_in_segments(rec, [(line, cream3)], f, x=(1080 - lw) / 2, y=py, num_frames=22)
        py += 84
        rec.hold_last_frame(18)
    rec.hold_last_frame(60)

    # ================= Act 4: what's on the site =================
    _fade_to_clean_base(rec, num_frames=26)

    def fade_in_dot_line(color, text, y, dot_r=9, gap=16, num_frames=16):
        """Fades in a colored dot + label as one unit -- a real drawn
        ellipse for the marker, not a "●" text glyph (Poppins doesn't
        include that character; an earlier version rendered it as a
        visible tofu/missing-glyph box, caught during frame review)."""
        f = feature_font
        ascent, descent = f.getmetrics()
        text_h = ascent + descent
        text_w = ImageDraw.Draw(rec.img).textlength(text, font=f)
        total_w = dot_r * 2 + gap + text_w
        x0 = (1080 - total_w) / 2
        dot_cx = x0 + dot_r
        dot_cy = y + text_h / 2
        base = rec.img.convert('RGBA')
        overlay = Image.new('RGBA', base.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=color + (255,))
        od.text((x0 + dot_r * 2 + gap, y), text, font=f, fill=cream3 + (255,))
        for step in range(1, num_frames + 1):
            t = _smoothstep(step / num_frames)
            layer = overlay.copy()
            layer.putalpha(layer.split()[3].point(lambda a, m=t: int(a * m)))
            frame = Image.alpha_composite(base, layer)
            frame.convert('RGB').save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
            rec.index += 1
        rec.img = Image.alpha_composite(base, overlay).convert('RGB')
        rec.draw = ImageDraw.Draw(rec.img)

    features = [
        (blue, "Posts"), (blue, "News"), (orange3, "Toolkit"),
        (pink, "You, Check."), (green, "Glossary"), (violet, "on(my).mind"),
    ]
    feature_font = font(REG, 36)
    fy = 340
    for color, text in features:
        fade_in_dot_line(color, text, fy, num_frames=16)
        fy += 76
        rec.hold_last_frame(12)
    rec.hold_last_frame(60)

    # ================= Act 5: brand lockup =================
    _fade_to_clean_base(rec, num_frames=26)

    ISCALE = 3.2
    OFFX, OFFY = 540 - 75 * ISCALE, 340 - 55.5 * ISCALE
    icon_base = rec.img.convert('RGBA')
    icon_layer = Image.new('RGBA', icon_base.size, (0, 0, 0, 0))
    lockup_icon_od = ImageDraw.Draw(icon_layer)
    draw_brand_icon(lockup_icon_od, OFFX, OFFY, ISCALE, cream3 + (255,), orange3 + (255,))
    n_icon = 22
    for step in range(1, n_icon + 1):
        t = _smoothstep(step / n_icon)
        layer = icon_layer.copy()
        layer.putalpha(layer.split()[3].point(lambda a, m=t: int(a * m)))
        frame = Image.alpha_composite(icon_base, layer)
        frame.convert('RGB').save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
        rec.index += 1
    rec.img = Image.alpha_composite(icon_base, icon_layer).convert('RGB')
    rec.draw = ImageDraw.Draw(rec.img)
    rec.hold_last_frame(12)

    wordmark_font = font(BOLD, 80)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=560, num_frames=20)
    rec.hold_last_frame(12)

    motto_font = font(MONO_BOLD, 28)
    motto_segments = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    fade_in_segments(rec, motto_segments, motto_font, x='center', y=670, num_frames=16)
    rec.hold_last_frame(12)

    tagline_font = font(MONO_BOLD, 26)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=718, num_frames=16)
    rec.hold_last_frame(20)

    # ================= Act 6: CTA =================
    cta_font = font(BOLD, 34)
    cta_segments = [
        ("Like", orange3), (". ", gray_light), ("Share", orange3), (". ", gray_light),
        ("Follow", orange3), (". ", gray_light), ("Comment", orange3), (".", gray_light),
    ]
    cta_w = ImageDraw.Draw(rec.img).textlength(''.join(s for s, _ in cta_segments), font=cta_font)
    fade_in_segments(rec, cta_segments, cta_font, x=(1080 - cta_w) / 2, y=810, num_frames=18)
    rec.hold_last_frame(24)

    closer_font = font(REG, 28)
    closer_text = "Trust me, it's worth it."
    closer_w = ImageDraw.Draw(rec.img).textlength(closer_text, font=closer_font)
    fade_in_segments(rec, [(closer_text, cream3)], closer_font, x=(1080 - closer_w) / 2, y=862, num_frames=18)
    rec.hold_last_frame(60)

    total_frames = rec.index - 1

    silent_path = video_path + ".silent.mp4"
    assemble_video(out_dir, silent_path, fps=fps)

    audio_path = os.path.join(out_dir, "_silhouette_audio.wav")
    synthesize_silhouette_audio(fps, total_frames, audio_path, drone_events=drone_events,
                                 chime_frames=chime_frames, tick_frames=tick_frames)
    mux_audio(silent_path, audio_path, video_path)
    os.remove(silent_path)
    os.remove(audio_path)

    return total_frames


if __name__ == "__main__":
    print("This is a library, not a script to run directly.")
    print("Import it: from animate import FrameRecorder, wobbly_animated, assemble_video")
    print("See animate_clean_smiley() for a full worked example.")
