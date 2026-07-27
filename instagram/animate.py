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

from PIL import Image, ImageDraw

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
        self.click_frames = []    # frame indices where a keystroke sound should land
        self.scratch_frames = []  # frame indices where a pencil/pen "drawing" sound should land

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


def _pillar_icon_strokes(kind, color):
    """Returns a small set of (local_points, color, width) stroke specs --
    centered on (0, 0), roughly ±30px before scaling -- for a minimal
    line-art icon, in the same hand-drawn style as the brand mark itself
    (a couple of geometry primitives, not a detailed illustration).
    `kind` selects which icon: 'shield' (Stay Safe), 'lightbulb' (Cyber
    Basics), 'folder' (Case File), 'magnifier' (Myth Busting), 'document'
    (Cyber News), 'chip' (AI Watch -- body only, pairs with a grown
    center circle for the "watching" pupil), 'building' and 'bot' (the
    two things stay(human).sec explicitly is NOT, used in the philosophy
    beat). Kept as data (point lists) rather than inline per-call code so
    draw_animated_icon() can animate any of them the same way."""
    from generate_post import quad_bezier, circle_pts, rounded_rect_points

    if kind == 'shield':
        top_left, top_right, right_mid, left_mid = (-26, -30), (26, -30), (26, 6), (-26, 6)
        curve = quad_bezier(right_mid, (0, 40), left_mid, steps=14)
        pts = [top_left, top_right, right_mid] + curve[1:] + [top_left]
        return [(pts, color, 6)]
    if kind == 'lightbulb':
        bulb = circle_pts(0, -8, 16)
        base = [(-6, 10), (6, 10), (6, 20), (-6, 20), (-6, 10)]
        return [(bulb, color, 5), (base, color, 5)]
    if kind == 'folder':
        body = rounded_rect_points(-26, -10, 26, 22, 5)
        tab = [(-26, -10), (-16, -10), (-12, -18), (6, -18), (10, -10)]
        return [(body, color, 5), (tab, color, 5)]
    if kind == 'magnifier':
        lens = circle_pts(-4, -4, 15)
        handle = quad_bezier((8, 8), (18, 18), (27, 27), steps=6)
        return [(lens, color, 5), (handle, color, 6)]
    if kind == 'document':
        body = rounded_rect_points(-18, -24, 18, 24, 4)
        line1 = [(-10, -10), (10, -10)]
        line2 = [(-10, 0), (10, 0)]
        line3 = [(-10, 10), (6, 10)]
        return [(body, color, 4), (line1, color, 3), (line2, color, 3), (line3, color, 3)]
    if kind == 'chip':
        body = rounded_rect_points(-20, -20, 20, 20, 6)
        return [(body, color, 5)]
    if kind == 'building':
        body = rounded_rect_points(-20, -6, 20, 26, 3)
        roof = [(-24, -6), (0, -26), (24, -6)]
        return [(body, color, 5), (roof, color, 5)]
    if kind == 'bot':
        head = rounded_rect_points(-18, -18, 18, 14, 5)
        antenna = [(0, -18), (0, -28)]
        return [(head, color, 5), (antenna, color, 4)]
    raise ValueError(f"unknown icon kind: {kind!r}")


def draw_animated_icon(recorder, kind, cx, cy, scale, color, seed_base=900, stroke_frames=5):
    """Draws one of _pillar_icon_strokes()'s minimal line-art icons at
    (cx, cy) scaled up from its local ±30px coordinate space, one stroke
    at a time via wobbly_animated (same hand-drawn jitter as everything
    else in this pipeline). Every drawn frame gets logged to
    recorder.scratch_frames (see synthesize_sound_track()) so the icon
    draw-in gets the same soft pencil-scratch sound Act 3's logo already
    uses -- these are small illustrations "sketching in", not typed text,
    so they get the drawing sound, not a keystroke sound."""
    strokes = _pillar_icon_strokes(kind, color)
    for i, (pts, stroke_color, width) in enumerate(strokes):
        xf_pts = [(cx + px * scale, cy + py * scale) for (px, py) in pts]
        start = recorder.index
        wobbly_animated(recorder, xf_pts, stroke_color, width, 0.8, seed=seed_base + i, num_frames=stroke_frames)
        for fi in range(start, recorder.index, 2):
            recorder.scratch_frames.append(fi)


def draw_animated_fill(recorder, cx, cy, r, color, num_frames=6):
    """Grows a small filled circle in place (see grow_circle) and logs
    its frames to recorder.scratch_frames, same drawing-sound treatment
    as draw_animated_icon() -- used for the AI Watch chip's center
    "pupil" and the bot icon's eyes, filled shapes that don't have an
    outline path to draw stroke-by-stroke."""
    start = recorder.index
    grow_circle(recorder, cx, cy, r, color, num_frames=num_frames)
    for fi in range(start, recorder.index, 2):
        recorder.scratch_frames.append(fi)


def draw_strike_through(recorder, cx, cy, half_size, color, seed=950, num_frames=6):
    """Draws one diagonal wobbly stroke across (cx, cy) -- the "this is
    NOT what we are" gesture used on the building/bot icons in the
    philosophy beat, a real visual contrast instead of a spoken/typed
    negation."""
    from generate_post import quad_bezier

    pts = quad_bezier((cx - half_size, cy - half_size), (cx, cy), (cx + half_size, cy + half_size), steps=20)
    start = recorder.index
    wobbly_animated(recorder, pts, color, 7, 1.0, seed=seed, num_frames=num_frames)
    for fi in range(start, recorder.index, 2):
        recorder.scratch_frames.append(fi)


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
    feel like a metronome."""
    return t * t * (3 - 2 * t)


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


def _synth_scratch_samples(sample_rate):
    """Generates one synthesized pencil/pen "drawing" scratch as a list of
    floats in [-1, 1] -- white noise passed through a simple one-pole
    low-pass filter (exponential moving average) so it reads as a soft
    scribble/scratch rather than static, under a moderate decay envelope.
    Used under Act 3's icon draw-in, distinct from the sharper keystroke
    ticks used for typed text elsewhere in the video. Pure stdlib
    (random/math) -- no audio libraries or external sound assets."""
    total_duration = 0.03
    n = max(1, int(sample_rate * total_duration))
    alpha = 0.35  # low-pass smoothing -- lower = softer/duller scratch
    samples = []
    prev = 0.0
    for i in range(n):
        t = i / sample_rate
        raw = random.uniform(-1, 1)
        prev = prev + alpha * (raw - prev)
        env = math.exp(-t / 0.012)
        samples.append(prev * env * 0.6)
    return samples


def synthesize_sound_track(keyboard_audio_path, click_frames, scratch_frames, fps, total_frames,
                            out_wav, sample_rate=44100):
    """Renders a WAV mixing two sound sources onto one track:

      1. Real keystroke clicks, extracted from a real recording
         (`keyboard_audio_path` -- see instagram/assets/sfx/
         keyboard_typing.mp3) via _extract_keyboard_clicks(), one placed
         at every entry in `click_frames` (frame indices recorded by
         type_text_animated()/type_and_erase_line() every time a
         character was added or removed) -- i.e. one real click per
         keystroke, synced to the exact frame that keystroke lands on,
         the same placement mechanism three earlier from-scratch
         synthesis attempts used. An earlier version of this function
         instead played the whole recording once as a continuous
         background loop under the typing acts -- that's a fixed
         unrelated rhythm playing alongside the typing, not synced to
         it, which is why it read as disconnected from what was on
         screen; per-keystroke placement of the real recording's own
         individual click sounds is what actually keeps sound and
         visual in sync.
      2. A softer synthesized pencil-scratch sound (_synth_scratch_samples)
         for every entry in `scratch_frames` (frame indices recorded
         during Act 3's icon draw-in), placed at that frame's exact
         timestamp -- this one stays synthesized since it's illustrating
         a hand-drawn stroke, not a keyboard.

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

    for sf in scratch_frames:
        start = int((sf / fps) * sample_rate)
        scratch = _synth_scratch_samples(sample_rate)
        for i, v in enumerate(scratch):
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
    """Brand + site story, rebuilt around small hand-drawn icons instead
    of long stretches of typed sentences -- an earlier version leaned on
    type_and_erase_line() for nearly the entire runtime (six question/
    answer beats plus three philosophy sentences, all pure text on an
    empty grid) and read as generic/confusing precisely because there
    was nothing to actually look at, just words appearing and
    disappearing. This version gives every beat something to watch:

      Act 0 (terminal chrome visible, ~5.5s): the philosophy shown, not
        just typed -- a generic building icon draws in and gets struck
        through ("not a company"), a bot-face icon draws in and gets
        struck through ("not a bot"), then the real brand icon draws in
        clean with "Just one person." fading in beneath it. The
        contrast (drawn, crossed out, drawn again clean) carries the
        point instead of three sentences in a row.
      Act 1 (terminal chrome visible, ~11s): a tour of six site pillars,
        each as icon + label instead of a typed question/answer pair --
        a small line-art icon (shield / lightbulb / folder / magnifier /
        document / chip) draws in, then the real pillar name fades in
        underneath in that pillar's own accent color (Stay Safe /
        Cyber Basics / Case File / Myth Busting / Cyber News / AI Watch
        -- see the 9-pillar table in CLAUDE.md), holds briefly, then
        clears for the next.
      (chrome fades out here, handing off to the plain brand-lockup look)
      Act 2 (~6.5s, trimmed from an earlier 9s cut): the same brand
        lockup as animate_brand_intro -- icon draws in, wordmark fades
        in, motto types out, tagline fades in -- so it still ends on one
        screenshot-recognizable frame. The icon draw-in logs to
        rec.scratch_frames for a soft pencil/pen sound.
      Act 3 (~1.5s, trimmed from an earlier 3s cut): a like/share/follow
        line fades in beneath the still-visible lockup (the lockup
        itself is never disturbed) -- "LIKE. SHARE. FOLLOW FOR ONE NEW
        FILE, EVERY DAY.", matching the real closer pattern already used
        across the Instagram captions.

    Every icon draw-in logs to rec.scratch_frames for a synthesized
    pencil-scratch sound; the motto (the only remaining typed text) logs
    to rec.click_frames and gets real keyboard clicks extracted from a
    recording (instagram/assets/sfx/keyboard_typing.mp3 --
    _extract_keyboard_clicks()). Both are mixed by
    synthesize_sound_track() and muxed onto the silent video
    (mux_audio()) automatically before this function returns.

    Total runtime is roughly 20-25s (icon/hold/clear timings are fixed
    frame counts here, not derived from text length the way the earlier
    typed version was) -- exact total frame count is returned by the
    function and should be read from there / verified via ffprobe, not
    assumed.
    """
    from generate_post import (base_card, quad_bezier, gray_light, blue, green, gold, pink, violet,
                                font, BOLD, MONO_BOLD)

    img, d = base_card()
    rec = FrameRecorder(img, d, out_dir)
    draw_terminal_chrome(rec)
    chrome_base = rec.img.copy()

    def clear_beat(num_frames=6):
        """Cross-dissolves back to the chrome-only base (not a fully
        blank base_card() -- that's _fade_to_clean_base()'s job, used
        once at the Act 1 -> Act 2 handoff) so each icon beat clears
        cleanly without losing the terminal-window frame underneath it."""
        start = rec.img.convert('RGBA')
        end = chrome_base.convert('RGBA')
        for step in range(1, num_frames + 1):
            t = step / num_frames
            frame = Image.blend(start, end, t)
            frame.convert('RGB').save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
            rec.index += 1
        rec.img = chrome_base.copy()
        rec.draw = ImageDraw.Draw(rec.img)

    CX, CY = 540, 420
    ICON_SCALE = 1.7

    # ---- Act 0: philosophy, shown rather than just typed ----
    draw_animated_icon(rec, 'building', CX, CY, ICON_SCALE, gray_light, seed_base=910, stroke_frames=6)
    draw_strike_through(rec, CX, CY, 34 * ICON_SCALE, pink, seed=951, num_frames=6)
    rec.hold_last_frame(8)
    clear_beat()

    draw_animated_icon(rec, 'bot', CX, CY, ICON_SCALE, gray_light, seed_base=920, stroke_frames=6)
    draw_animated_fill(rec, CX - 8 * ICON_SCALE, CY - 4 * ICON_SCALE, 3 * ICON_SCALE, gray_light, num_frames=4)
    draw_animated_fill(rec, CX + 8 * ICON_SCALE, CY - 4 * ICON_SCALE, 3 * ICON_SCALE, gray_light, num_frames=4)
    draw_strike_through(rec, CX, CY, 34 * ICON_SCALE, pink, seed=952, num_frames=6)
    rec.hold_last_frame(8)
    clear_beat()

    BRAND_ISCALE = 1.4
    BOFFX, BOFFY = CX - 75 * BRAND_ISCALE, CY - 60 - 55.5 * BRAND_ISCALE

    def bxf(pt):
        return (BOFFX + pt[0] * BRAND_ISCALE, BOFFY + pt[1] * BRAND_ISCALE)

    b_start = rec.index
    left_bracket = quad_bezier(bxf((38, 16)), bxf((20, 50)), bxf((38, 84)), steps=40)
    wobbly_animated(rec, left_bracket, cream3, 6, 0.9, seed=930, num_frames=6)
    right_bracket = quad_bezier(bxf((112, 16)), bxf((130, 50)), bxf((112, 84)), steps=40)
    wobbly_animated(rec, right_bracket, cream3, 6, 0.9, seed=931, num_frames=6)
    head_cx, head_cy = bxf((75, 38))
    grow_circle(rec, head_cx, head_cy, max_r=13 * BRAND_ISCALE, color=orange3, num_frames=5)
    body_arc = [bxf((75 + 17 * math.cos(math.radians(a)), 78 + 17 * math.sin(math.radians(a))))
                for a in range(180, 361, 4)]
    wobbly_animated(rec, body_arc, orange3, 4, 0.8, seed=932, num_frames=6)
    for fi in range(b_start, rec.index, 2):
        rec.scratch_frames.append(fi)

    label_font = font(MONO_BOLD, 40)
    fade_in_segments(rec, [("Just one person.", cream3)], label_font, x='center', y=CY + 90, num_frames=10)
    rec.hold_last_frame(10)
    clear_beat()

    # ---- Act 1: a tour of six site pillars as icon + label ----
    def pillar_beat(kind, color, label, seed_base, stroke_frames=5, fill=False):
        draw_animated_icon(rec, kind, CX, CY, ICON_SCALE, color, seed_base=seed_base, stroke_frames=stroke_frames)
        if fill:
            draw_animated_fill(rec, CX, CY, 7 * ICON_SCALE * 0.5, color, num_frames=5)
        label_f = font(MONO_BOLD, 40)
        fade_in_segments(rec, [(label, color)], label_f, x='center', y=CY + 70, num_frames=8)
        rec.hold_last_frame(12)
        clear_beat()

    pillar_beat('shield', orange3, "Stay Safe.", seed_base=940)
    pillar_beat('lightbulb', green, "Cyber Basics.", seed_base=942)
    pillar_beat('folder', pink, "Case File.", seed_base=944)
    pillar_beat('magnifier', gold, "Myth Busting.", seed_base=946)
    pillar_beat('document', blue, "Cyber News.", seed_base=948, stroke_frames=4)
    pillar_beat('chip', violet, "AI Watch.", seed_base=950, fill=True)

    # ---- handoff: fade the terminal chrome out before the brand lockup,
    # which uses the plain grid-card look, not the terminal-window frame.
    _fade_to_clean_base(rec, num_frames=10)

    # ---- Act 2: brand lockup (trimmed pacing vs. animate_brand_intro) ----
    ISCALE = 4.0
    OFFX, OFFY = 540 - 75 * ISCALE, 300 - 55.5 * ISCALE

    def xf(pt):
        return (OFFX + pt[0] * ISCALE, OFFY + pt[1] * ISCALE)

    s = rec.index
    left_bracket = quad_bezier(xf((38, 16)), xf((20, 50)), xf((38, 84)), steps=60)
    wobbly_animated(rec, left_bracket, cream3, 10, 1.2, seed=301, num_frames=10)
    right_bracket = quad_bezier(xf((112, 16)), xf((130, 50)), xf((112, 84)), steps=60)
    wobbly_animated(rec, right_bracket, cream3, 10, 1.2, seed=302, num_frames=10)
    head_cx, head_cy = xf((75, 38))
    grow_circle(rec, head_cx, head_cy, max_r=13 * ISCALE, color=orange3, num_frames=8)
    body_arc = [xf((75 + 17 * math.cos(math.radians(a)), 78 + 17 * math.sin(math.radians(a))))
                for a in range(180, 361, 4)]
    wobbly_animated(rec, body_arc, orange3, 7, 1.0, seed=303, num_frames=10)
    for fi in range(s, rec.index, 2):
        rec.scratch_frames.append(fi)
    rec.hold_last_frame(8)

    wordmark_font = font(BOLD, 88)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=500, num_frames=20)
    rec.hold_last_frame(8)

    motto_font = font(MONO_BOLD, 32)
    motto_text = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    motto_full = ''.join(s for s, _ in motto_text)
    motto_w = ImageDraw.Draw(rec.img).textlength(motto_full, font=motto_font)
    type_text_animated(rec, motto_text, motto_font, x=(1080 - motto_w) / 2, y=630, num_frames=18)
    rec.hold_last_frame(4)

    tagline_font = font(MONO_BOLD, 30)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=700, num_frames=22)
    rec.hold_last_frame(14)

    # ---- Act 3: like/share/follow, added beneath the still-visible
    # lockup -- the lockup itself is never disturbed ----
    cta_font = font(MONO_BOLD, 24)
    cta_segments = [
        ("LIKE", orange3), (". ", gray_light), ("SHARE", orange3), (". ", gray_light),
        ("FOLLOW", orange3), (" FOR ONE NEW FILE, EVERY DAY.", gray_light),
    ]
    fade_in_segments(rec, cta_segments, cta_font, x='center', y=800, num_frames=16)
    rec.hold_last_frame(14)

    total_frames = rec.index - 1

    silent_path = video_path + ".silent.mp4"
    assemble_video(out_dir, silent_path, fps=fps)

    keyboard_audio_path = os.path.join(os.path.dirname(__file__), "assets", "sfx", "keyboard_typing.mp3")
    audio_path = os.path.join(out_dir, "_typing_clicks.wav")
    synthesize_sound_track(keyboard_audio_path, rec.click_frames, rec.scratch_frames, fps, total_frames, audio_path)
    mux_audio(silent_path, audio_path, video_path)
    os.remove(silent_path)
    os.remove(audio_path)

    return total_frames


if __name__ == "__main__":
    print("This is a library, not a script to run directly.")
    print("Import it: from animate import FrameRecorder, wobbly_animated, assemble_video")
    print("See animate_clean_smiley() for a full worked example.")
