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
    t = max(0.0, min(1.0, t))
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
    """Silhouette micro-story brand video -- completely different
    mechanism from every typing/icon-montage version before it, and
    built specifically for smoothness: every other animate_* function in
    this file accumulates hand-drawn strokes frame by frame (wobbly_
    animated()) or reveals characters one at a time, which is exactly
    right for a "sketched" look but is NOT continuous interpolation --
    there's no previous silhouette reference anywhere in this codebase
    (only draw_icon()'s small bracket-person mark and the phone-eye
    explainer's phone illustration), so this is built fresh, and built
    around parametric redraw instead: every frame fully re-renders the
    scene from a handful of continuous parameters (head position/size,
    shoulder height, glow color, alpha layers), each interpolated with
    _smoothstep() easing across as many frames as the beat needs. That
    guarantees every transition is smooth by construction -- there's no
    step where a "next pose" replaces a "previous pose" abruptly, only
    ever a continuously-moving parameter.

      Beat 1 (~1.4s): the silhouette (an orange rim-light outline around
        a near-black fill -- head ellipse + shoulder trapezoid, filled
        black to occlude the grid, outlined in orange3, simple/iconic
        rather than detailed) fades in from alpha 0 to 1.
      Beat 2 (~1.7s): the head lowers and compresses slightly (a 2D
        foreshortening trick for "tilting down", not a true 3D
        rotation) while a phone -- rounded rect body, warm cream glow
        inset -- fades in below it, staggered a few frames behind the
        head so the tilt reads as leading the phone's appearance, not
        simultaneous.
      Beat 3 (~3s): shoulders raise slightly (tension) while the phone's
        glow ramps from warm cream to a cold blue-gray, both eased over
        ~1s, then HOLDS for ~2s with a slow sine-wave brightness pulse
        on the glow (a controlled, gentle pulse -- not random jitter --
        the one deliberate "flicker" in the piece, everything else stays
        strictly stutter-free) so the unease beat actually registers
        before moving on.
      Beat 4 (~1.7s): the brand icon fades in on the phone screen (pure
        alpha compositing, not a stroke draw -- the smoothest possible
        reveal, no jitter risk at all) as if it's the person's own
        reflection.
      Beat 5 (~1.7s): shoulders lower back to relaxed and the glow warms
        back to cream, both eased, mirroring beat 3's ramp in reverse.
      Beat 6 (~4.5s): wordmark, motto, and tagline fade in below the
        (still fully visible) figure via fade_in_segments() -- the same
        plain alpha-fade mechanism used across every other brand video,
        calm and steady, no typing effect.

    No sound track -- nothing in this brief asked for audio, and there's
    no typing/drawing/hard-cut event here that any of this file's
    existing sound design would attach to, so this returns a silent
    MP4. Total runtime is roughly 14-15s (longer than the "~10-12s"
    target because beat 3 is deliberately held long enough to actually
    read as unease, not rushed past, per the brief's own framing of that
    as a floor to adjust around, not a hard ceiling) -- exact total
    frame count is returned by the function and should be read from
    there / verified via ffprobe, not assumed.
    """
    from generate_post import base_card, gray_light, font, BOLD, MONO_BOLD, draw_icon as draw_brand_icon

    base_img, base_draw = base_card()
    rec = FrameRecorder(base_img, base_draw, out_dir)

    HEAD_CX = 540
    HEAD_RX = 66
    HEAD_RY_UP, HEAD_RY_DOWN = 66, 58
    HEAD_CY_UP, HEAD_CY_DOWN = 360, 400
    SHOULDER_TOP_RELAXED, SHOULDER_TOP_TENSE = 470, 452
    SHOULDER_BOTTOM = 660
    SHOULDER_HALF_TOP, SHOULDER_HALF_BOTTOM = 65, 145
    OUTLINE_W = 5
    SIL_FILL = (0, 0, 0)

    PHONE_W, PHONE_H = 92, 168
    PHONE_CX, PHONE_CY = 540, 560
    PHONE_CORNER = 16

    GLOW_WARM = cream3
    GLOW_COLD = (120, 150, 210)

    def ease(t):
        return _smoothstep(max(0.0, min(1.0, t)))

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
        od.rounded_rectangle([x0, y0, x1, y1], radius=PHONE_CORNER, fill=(6, 6, 6, 255),
                              outline=gray_light + (255,), width=3)
        inset = 8
        od.rounded_rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset],
                              radius=max(1, PHONE_CORNER - 6), fill=glow_color + (230,))
        if alpha < 1.0:
            overlay.putalpha(overlay.split()[3].point(lambda a, m=alpha: int(a * m)))
        return overlay

    def icon_overlay(size, alpha, scale=1.7):
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        offx, offy = PHONE_CX - 75 * scale, PHONE_CY - 55.5 * scale
        draw_brand_icon(od, offx, offy, scale, cream3 + (255,), orange3 + (255,))
        if alpha < 1.0:
            overlay.putalpha(overlay.split()[3].point(lambda a, m=alpha: int(a * m)))
        return overlay

    def render(head_cy, head_ry, shoulder_top, figure_alpha, phone_alpha, glow_color, glow_pulse, icon_alpha):
        frame = base_img.copy().convert('RGBA')
        frame = Image.alpha_composite(frame, silhouette_overlay(frame.size, head_cy, head_ry, shoulder_top, figure_alpha))
        if phone_alpha > 0:
            pulsed = tuple(min(255, max(0, int(c * glow_pulse))) for c in glow_color)
            frame = Image.alpha_composite(frame, phone_overlay(frame.size, pulsed, phone_alpha))
        if icon_alpha > 0:
            frame = Image.alpha_composite(frame, icon_overlay(frame.size, icon_alpha))
        final = frame.convert('RGB')
        final.save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
        rec.index += 1
        rec.img = final
        return final

    # ---- Beat 1: the silhouette fades in (~1.4s) ----
    n1 = 24
    for step in range(n1):
        t = ease(step / (n1 - 1))
        render(HEAD_CY_UP, HEAD_RY_UP, SHOULDER_TOP_RELAXED, t, 0.0, GLOW_WARM, 1.0, 0.0)
    rec.hold_last_frame(10)

    # ---- Beat 2: head lowers/compresses, phone fades in staggered
    # behind it (~1.7s) ----
    n2 = 24
    for step in range(n2):
        t = ease(step / (n2 - 1))
        head_cy = lerp(HEAD_CY_UP, HEAD_CY_DOWN, t)
        head_ry = lerp(HEAD_RY_UP, HEAD_RY_DOWN, t)
        phone_t = ease(max(0.0, (step - 6) / (n2 - 1 - 6)))
        render(head_cy, head_ry, SHOULDER_TOP_RELAXED, 1.0, phone_t, GLOW_WARM, 1.0, 0.0)
    rec.hold_last_frame(10)

    # ---- Beat 3: tension rises, glow cools -- ramp (~1s) then a long
    # hold (~2s) with a slow, controlled sine pulse on the glow so the
    # unease beat actually registers (~3s total) ----
    n3_ramp = 20
    for step in range(n3_ramp):
        t = ease(step / (n3_ramp - 1))
        shoulder_top = lerp(SHOULDER_TOP_RELAXED, SHOULDER_TOP_TENSE, t)
        glow = lerp_color(GLOW_WARM, GLOW_COLD, t)
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, shoulder_top, 1.0, 1.0, glow, 1.0, 0.0)
    n3_hold = 40
    for step in range(n3_hold):
        pulse = 1.0 + 0.12 * math.sin(step * 0.35)
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, SHOULDER_TOP_TENSE, 1.0, 1.0, GLOW_COLD, pulse, 0.0)

    # ---- Beat 4: the brand icon fades in on the phone screen -- pure
    # alpha compositing, no stroke draw, for the smoothest possible
    # reveal (~1.7s) ----
    n4 = 24
    for step in range(n4):
        t = ease(step / (n4 - 1))
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, SHOULDER_TOP_TENSE, 1.0, 1.0, GLOW_COLD, 1.0, t)
    rec.hold_last_frame(10)

    # ---- Beat 5: posture eases, glow warms back -- mirrors beat 3's
    # ramp in reverse (~1.7s) ----
    n5 = 24
    for step in range(n5):
        t = ease(step / (n5 - 1))
        shoulder_top = lerp(SHOULDER_TOP_TENSE, SHOULDER_TOP_RELAXED, t)
        glow = lerp_color(GLOW_COLD, GLOW_WARM, t)
        render(HEAD_CY_DOWN, HEAD_RY_DOWN, shoulder_top, 1.0, 1.0, glow, 1.0, 1.0)
    rec.hold_last_frame(10)

    # ---- Beat 6: wordmark / motto / tagline fade in below the still-
    # visible figure, calm and steady (~4.5s) ----
    wordmark_font = font(BOLD, 70)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=790, num_frames=18)
    rec.hold_last_frame(8)

    motto_font = font(MONO_BOLD, 26)
    motto_segments = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    fade_in_segments(rec, motto_segments, motto_font, x='center', y=878, num_frames=14)
    rec.hold_last_frame(8)

    tagline_font = font(MONO_BOLD, 24)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=922, num_frames=14)
    rec.hold_last_frame(24)

    total_frames = rec.index - 1
    assemble_video(out_dir, video_path, fps=fps)
    return total_frames


def animate_debut_video(out_dir, video_path, fps=60):
    """Full five-act debut brand video, built directly on top of the
    already-approved animate_silhouette_story(). Act 1 below is that
    exact same beat sequence (same geometry, same easing, same simple
    phone with no bloom/inset, no audio) reproduced verbatim rather than
    imported, since animate_silhouette_story() assembles and returns its
    own standalone video and this function needs to keep recording into
    one continuous FrameRecorder afterward instead of stitching two
    separately-assembled clips together.

      Act 1 (silhouette hook, unchanged): figure fades in -> head lowers
        toward a phone fading in below it -> shoulders tense while the
        phone's glow cools cream-to-cold, held with a slow controlled
        pulse -> the brand icon fades in on the phone screen as a
        reflection -> shoulders relax, glow warms back -> wordmark,
        motto, and tagline fade in calmly below.
      Act 2 (more about us): three first-person lines about who's
        actually behind the account, crossfaded one at a time via
        crossfade_text_beats() (fade+drift, not a hard cut), each held
        long enough to read comfortably rather than rushed.
      Act 3 (website showcase): a browser-window mockup, styled in the
        site's own dark/cream/orange terminal language (the exact same
        base_card() grid+border, the same window-control glyph style as
        draw_terminal_chrome(), a terminal-style "$ open
        stayhumansec.github.io" prompt) fast-crossfades through six real
        screens (see the crossfade loop below) -- the homepage
        hero (wordmark/motto/tagline plus the boot
        sequence's real "0 trackers / 0 ad scripts / 0 cookies" checkup
        line), the 9-pillar grid (exact labels/colors from CLAUDE.md's
        pillar table), the Utilities list (its real eyebrow/heading from
        tools.html, and its real four tools: Password Coach, Recovery Kit
        Builder, Breach Exposure Check, Search the Archive), an article
        page (tag pill, title, stat line, body lines, checklist box --
        the real post.html anatomy), the News feed (dated, sourced
        headline rows), and the Toolkit (its real categories: Password
        Managers, VPNs, Authenticator Apps, Browsers) -- each screen
        holds with a short caption underneath,
        dissolving smoothly into the next rather than cutting.
      Act 4 (brand lockup, reprised): the same calm wordmark/motto/
        tagline treatment as Act 1's close, standing alone this time as
        the video's second and final anchor point -- reinforcing the
        identity after actually showing what it built.
      Act 5 (CTA): "Like. Share. Follow. Comment." fades in and holds,
        then gives way to a warmer, personal closing line -- "Trust me,
        it's worth it." -- like a genuine aside from the person behind
        the account, not a company sign-off. The video's last beat is
        the actual site link ("$ open stayhumansec.github.io"), the same
        "$ " terminal-prompt convention used throughout Act 3, so the
        one thing worth remembering is legible on its own final frame.

    Rendered at whatever fps is passed in (60fps by default, matching
    the already-approved silhouette's own re-render). Act 1's frame
    counts were all originally authored assuming 20fps, so fr() below
    scales them by fps/20 to keep Act 1's real-world timing untouched
    regardless of fps -- see the identical helper in
    animate_silhouette_story() for the full rationale. Acts 2-5 are new
    content with no prior duration to preserve, so their frame counts
    come directly from a target seconds duration via sec_frames()
    instead -- every beat runs as long as it genuinely needs to read
    comfortably, not compressed toward a fixed total.

    No audio track: nothing in this brief asked for sound design beyond
    what Act 1 already doesn't have, so this returns a silent MP4, same
    as the approved silhouette.
    """
    from generate_post import (base_card, gray_light, blue, green, gold, pink, violet,
                                font, BOLD, REG, MONO_BOLD, MONO_REG,
                                draw_icon as draw_brand_icon, wrap_text)

    CORAL = (255, 138, 106)
    CARD_BG = (13, 12, 10)     # matches --card
    LINE_COLOR = (58, 53, 44)  # matches --line

    base_img, base_draw = base_card()
    rec = FrameRecorder(base_img, base_draw, out_dir)

    FPS_SCALE = fps / 20.0

    def fr(n):
        """Scales an Act-1 frame count written assuming 20fps up (or
        down) to whatever fps this call actually renders at, so Act 1's
        real-world duration stays exactly what was already approved."""
        return max(1, round(n * FPS_SCALE))

    def sec_frames(s):
        """Frame count for a new (Act 2-5) beat given a target duration
        in seconds -- no legacy 20fps assumption to preserve here."""
        return max(1, round(s * fps))

    def lerp(a, b, t):
        return a + (b - a) * t

    def lerp_color(c1, c2, t):
        return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))

    def ease(t):
        return _smoothstep(max(0.0, min(1.0, t)))

    # ================= Act 1: silhouette hook (unchanged) =================
    HEAD_CX = 540
    HEAD_RX = 66
    HEAD_RY_UP, HEAD_RY_DOWN = 66, 58
    HEAD_CY_UP, HEAD_CY_DOWN = 360, 400
    SHOULDER_TOP_RELAXED, SHOULDER_TOP_TENSE = 470, 452
    SHOULDER_BOTTOM = 660
    SHOULDER_HALF_TOP, SHOULDER_HALF_BOTTOM = 65, 145
    OUTLINE_W = 5
    SIL_FILL = (0, 0, 0)

    PHONE_W, PHONE_H = 92, 168
    PHONE_CX, PHONE_CY = 540, 560
    PHONE_CORNER = 16

    GLOW_WARM = cream3
    GLOW_COLD = (120, 150, 210)

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
        od.rounded_rectangle([x0, y0, x1, y1], radius=PHONE_CORNER, fill=(6, 6, 6, 255),
                              outline=gray_light + (255,), width=3)
        inset = 8
        od.rounded_rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset],
                              radius=max(1, PHONE_CORNER - 6), fill=glow_color + (230,))
        if alpha < 1.0:
            overlay.putalpha(overlay.split()[3].point(lambda a, m=alpha: int(a * m)))
        return overlay

    def icon_overlay(size, alpha, scale=1.7):
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        offx, offy = PHONE_CX - 75 * scale, PHONE_CY - 55.5 * scale
        draw_brand_icon(od, offx, offy, scale, cream3 + (255,), orange3 + (255,))
        if alpha < 1.0:
            overlay.putalpha(overlay.split()[3].point(lambda a, m=alpha: int(a * m)))
        return overlay

    def render_act1(head_cy, head_ry, shoulder_top, figure_alpha, phone_alpha, glow_color, glow_pulse, icon_alpha):
        frame = base_img.copy().convert('RGBA')
        frame = Image.alpha_composite(frame, silhouette_overlay(frame.size, head_cy, head_ry, shoulder_top, figure_alpha))
        if phone_alpha > 0:
            pulsed = tuple(min(255, max(0, int(c * glow_pulse))) for c in glow_color)
            frame = Image.alpha_composite(frame, phone_overlay(frame.size, pulsed, phone_alpha))
        if icon_alpha > 0:
            frame = Image.alpha_composite(frame, icon_overlay(frame.size, icon_alpha))
        final = frame.convert('RGB')
        final.save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
        rec.index += 1
        rec.img = final
        return final

    n1 = fr(24)
    for step in range(n1):
        t = ease(step / (n1 - 1))
        render_act1(HEAD_CY_UP, HEAD_RY_UP, SHOULDER_TOP_RELAXED, t, 0.0, GLOW_WARM, 1.0, 0.0)
    rec.hold_last_frame(fr(10))

    n2 = fr(24)
    stagger = fr(6)
    for step in range(n2):
        t = ease(step / (n2 - 1))
        head_cy = lerp(HEAD_CY_UP, HEAD_CY_DOWN, t)
        head_ry = lerp(HEAD_RY_UP, HEAD_RY_DOWN, t)
        phone_t = ease(max(0.0, (step - stagger) / (n2 - 1 - stagger)))
        render_act1(head_cy, head_ry, SHOULDER_TOP_RELAXED, 1.0, phone_t, GLOW_WARM, 1.0, 0.0)
    rec.hold_last_frame(fr(10))

    n3_ramp = fr(20)
    for step in range(n3_ramp):
        t = ease(step / (n3_ramp - 1))
        shoulder_top = lerp(SHOULDER_TOP_RELAXED, SHOULDER_TOP_TENSE, t)
        glow = lerp_color(GLOW_WARM, GLOW_COLD, t)
        render_act1(HEAD_CY_DOWN, HEAD_RY_DOWN, shoulder_top, 1.0, 1.0, glow, 1.0, 0.0)
    n3_hold = fr(40)
    for step in range(n3_hold):
        pulse = 1.0 + 0.12 * math.sin(step * (0.35 / FPS_SCALE))
        render_act1(HEAD_CY_DOWN, HEAD_RY_DOWN, SHOULDER_TOP_TENSE, 1.0, 1.0, GLOW_COLD, pulse, 0.0)

    n4 = fr(24)
    for step in range(n4):
        t = ease(step / (n4 - 1))
        render_act1(HEAD_CY_DOWN, HEAD_RY_DOWN, SHOULDER_TOP_TENSE, 1.0, 1.0, GLOW_COLD, 1.0, t)
    rec.hold_last_frame(fr(10))

    n5 = fr(24)
    for step in range(n5):
        t = ease(step / (n5 - 1))
        shoulder_top = lerp(SHOULDER_TOP_TENSE, SHOULDER_TOP_RELAXED, t)
        glow = lerp_color(GLOW_COLD, GLOW_WARM, t)
        render_act1(HEAD_CY_DOWN, HEAD_RY_DOWN, shoulder_top, 1.0, 1.0, glow, 1.0, 1.0)
    rec.hold_last_frame(fr(10))

    wordmark_font = font(BOLD, 70)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=790, num_frames=fr(18))
    rec.hold_last_frame(fr(8))

    motto_font = font(MONO_BOLD, 26)
    motto_segments = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    fade_in_segments(rec, motto_segments, motto_font, x='center', y=878, num_frames=fr(14))
    rec.hold_last_frame(fr(8))

    tagline_font = font(MONO_BOLD, 24)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=922, num_frames=fr(14))
    rec.hold_last_frame(fr(30))

    # ================= Act 2: more about us =================
    _fade_to_clean_base(rec, sec_frames(1.2))

    about_head_font = font(BOLD, 42)
    about_body_font = font(REG, 36)
    HEAD_LINE_H = 54
    BODY_LINE_H = 50

    def text_beat(lines, font_obj, line_h, center_y=520):
        total_h = line_h * (len(lines) - 1)
        y = center_y - total_h / 2
        beat_lines = []
        for ln in lines:
            beat_lines.append(([(ln, cream3)], font_obj, y))
            y += line_h
        return {"dot": None, "lines": beat_lines}

    wrapped_line2 = wrap_text(
        rec.draw,
        "No team. No company. Just someone who got tired of security "
        "advice that's either too technical, or too scary to actually act on.",
        about_body_font, 860,
    )

    about_beats = [
        text_beat(["Hi. I'm the person writing all of this."], about_head_font, HEAD_LINE_H),
        text_beat(wrapped_line2, about_body_font, BODY_LINE_H),
        text_beat(["So I started writing the version I wish existed."], about_head_font, HEAD_LINE_H),
    ]
    crossfade_text_beats(
        rec, about_beats,
        transition_frames=sec_frames(1.1),
        hold_frames=[sec_frames(3.2), sec_frames(4.4), sec_frames(3.4)],
    )

    # ================= Act 3: website showcase =================
    _fade_to_clean_base(rec, sec_frames(1.2))

    BW_X0, BW_Y0, BW_X1, BW_Y1 = 110, 130, 970, 830
    CHROME_H = 50
    CX0, CY0, CX1, CY1 = BW_X0 + 3, BW_Y0 + CHROME_H, BW_X1 - 3, BW_Y1 - 3

    CHROME_FILL = (36, 32, 26)  # visibly lighter than CARD_BG/black so the
                                  # title bar actually reads as a bar, not a
                                  # blank strip indistinguishable from the
                                  # background behind it

    def render_window_chrome():
        """Transparent full-canvas layer holding just the window border/
        chrome bar/blank content fill -- identical across every screen,
        so it's built once and reused. Compositing a screen's own content
        overlay on top of this makes up that screen's complete 'window'
        image, used as a single fade unit by the crossfade loop below --
        unlike the grid+card border behind it, this needs to be its own
        transparent layer so it can fade independently without dragging
        the static background along with it."""
        img = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([BW_X0, BW_Y0, BW_X1, BW_Y1], radius=18, outline=cream3, width=3)
        d.rounded_rectangle([BW_X0, BW_Y0, BW_X1, BW_Y0 + CHROME_H], radius=18, fill=CHROME_FILL)
        d.rectangle([BW_X0, BW_Y0 + CHROME_H - 18, BW_X1, BW_Y0 + CHROME_H], fill=CHROME_FILL)
        d.line([BW_X0, BW_Y0 + CHROME_H, BW_X1, BW_Y0 + CHROME_H], fill=LINE_COLOR, width=2)

        # terminal-style "$ " prompt on the left, the same convention used
        # everywhere else on the site/brand, instead of a browser address
        # bar -- this is meant to read as a terminal window, not a literal
        # web browser chrome.
        prompt_font = font(MONO_REG, 21)
        py = BW_Y0 + (CHROME_H - 21) / 2 - 2
        px = BW_X0 + 26
        d.text((px, py), "$ ", font=prompt_font, fill=orange3)
        px += d.textlength("$ ", font=prompt_font)
        d.text((px, py), "open stayhumansec.github.io", font=prompt_font, fill=gray_light)

        # window control glyphs on the right, matching draw_terminal_
        # chrome()'s own layout convention elsewhere in this file
        icon_y = BW_Y0 + CHROME_H / 2
        mx3 = BW_X1 - 44
        d.line([mx3, icon_y - 7, mx3 + 14, icon_y + 7], fill=gray_light, width=2)
        d.line([mx3, icon_y + 7, mx3 + 14, icon_y - 7], fill=gray_light, width=2)
        mx2 = mx3 - 34
        d.rounded_rectangle([mx2, icon_y - 7, mx2 + 14, icon_y + 7], radius=2, outline=gray_light, width=2)
        mx = mx2 - 34
        d.line([mx, icon_y, mx + 16, icon_y], fill=gray_light, width=2)

        # Bottom corners rounded to match the outer window border (radius
        # 18, minus the 3px inset) -- a square-cornered fill here would
        # poke a jagged notch out past the rounded border underneath it.
        # Top corners stay square since they sit flush against the
        # chrome bar's already-squared bottom edge.
        d.rounded_rectangle([BW_X0 + 3, BW_Y0 + CHROME_H, BW_X1 - 3, BW_Y1 - 3], radius=15,
                             fill=CARD_BG, corners=(False, False, True, True))
        return img

    def caption_below(d, text):
        cap_font = font(REG, 30)
        cw = d.textlength(text, font=cap_font)
        d.text(((1080 - cw) / 2, BW_Y1 + 34), text, font=cap_font, fill=gray_light)

    def new_overlay():
        """A transparent full-canvas layer for one screen's unique content
        (everything except the window border/chrome/CARD_BG fill, which
        are identical across every screen and drawn once into
        chrome_base). Keeping per-screen content on its own layer is what
        lets screens pan past each other instead of cross-dissolving --
        two different screens' text alpha-blended on top of each other
        read as garbled, half-formed lettering; sliding one out while the
        next slides in from clear canvas never puts two glyphs in the
        same place at the same time."""
        img = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    def screen_hero():
        img, d = new_overlay()
        cy = CY0 + 170
        motto_f = font(MONO_BOLD, 18)
        motto_segs = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
        full = ''.join(s for s, _ in motto_segs)
        mx = (1080 - d.textlength(full, font=motto_f)) / 2
        for txt, col in motto_segs:
            d.text((mx, cy), txt, font=motto_f, fill=col)
            mx += d.textlength(txt, font=motto_f)
        cy += 46
        wm_f = font(BOLD, 62)
        wm_segs = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
        wfull = ''.join(s for s, _ in wm_segs)
        wx = (1080 - d.textlength(wfull, font=wm_f)) / 2
        for txt, col in wm_segs:
            d.text((wx, cy), txt, font=wm_f, fill=col)
            wx += d.textlength(txt, font=wm_f)
        cy += 96
        tl_f = font(MONO_BOLD, 20)
        tl_segs = [("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
                   (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3)]
        tfull = ''.join(s for s, _ in tl_segs)
        tx = (1080 - d.textlength(tfull, font=tl_f)) / 2
        for txt, col in tl_segs:
            d.text((tx, cy), txt, font=tl_f, fill=col)
            tx += d.textlength(txt, font=tl_f)
        cy += 70
        chk_f = font(MONO_BOLD, 20)
        chk_text = "0 TRACKERS   0 AD SCRIPTS   0 COOKIES"
        chw = d.textlength(chk_text, font=chk_f)
        d.text(((1080 - chw) / 2, cy), chk_text, font=chk_f, fill=green)
        caption_below(d, "no trackers, no ads, no cookies -- genuinely")
        return img

    def screen_pillars():
        img, d = new_overlay()
        pillars = [
            ("CYBER NEWS", blue), ("AI NEWS", violet), ("STAY SAFE", orange3),
            ("CYBER BASICS", green), ("AI WATCH", violet), ("MYTH BUSTING", gold),
            ("CASE FILE", pink), ("DEEP DIVE", green), ("STORY TIME", CORAL),
        ]
        cols, rows = 3, 3
        pad = 26
        cell_w = (CX1 - CX0 - pad * (cols + 1)) / cols
        cell_h = (CY1 - CY0 - pad * (rows + 1)) / rows
        label_f = font(MONO_BOLD, 17)
        for i, (label, color) in enumerate(pillars):
            r, c = divmod(i, cols)
            x0 = CX0 + pad + c * (cell_w + pad)
            y0 = CY0 + pad + r * (cell_h + pad)
            x1, y1 = x0 + cell_w, y0 + cell_h
            d.rounded_rectangle([x0, y0, x1, y1], radius=12, outline=LINE_COLOR, width=2)
            dot_r = 12
            dcx, dcy = (x0 + x1) / 2, y0 + cell_h * 0.4
            d.ellipse([dcx - dot_r, dcy - dot_r, dcx + dot_r, dcy + dot_r], fill=color)
            lw = d.textlength(label, font=label_f)
            d.text(((x0 + x1) / 2 - lw / 2, y0 + cell_h * 0.68), label, font=label_f, fill=gray_light)
        caption_below(d, "nine pillars -- cybersecurity, AI, and privacy, in equal measure")
        return img

    def screen_utilities():
        img, d = new_overlay()
        eyebrow_f = font(MONO_BOLD, 20)
        d.text((CX0 + 50, CY0 + 40), "// UTILITIES", font=eyebrow_f, fill=orange3)
        head_f = font(BOLD, 32)
        d.text((CX0 + 50, CY0 + 84), "Small, focused, actually useful.", font=head_f, fill=cream3)
        utilities = [
            ("PASSWORD COACH", orange3, "teaches the passphrase method"),
            ("RECOVERY KIT BUILDER", blue, "your 2FA \"lost phone\" plan"),
            ("BREACH EXPOSURE CHECK", pink, "real k-anonymity breach lookup"),
            ("SEARCH THE ARCHIVE", green, "local search across every post"),
        ]
        cols = 2
        pad = 26
        cell_w = (CX1 - CX0 - pad * (cols + 1)) / cols
        cell_h = 190
        label_f = font(MONO_BOLD, 16)
        tag_f = font(REG, 16)
        for i, (label, color, tag) in enumerate(utilities):
            r, c = divmod(i, cols)
            x0 = CX0 + pad + c * (cell_w + pad)
            y0 = CY0 + 160 + r * (cell_h + pad)
            x1 = x0 + cell_w
            d.rounded_rectangle([x0, y0, x1, y0 + cell_h], radius=14, outline=LINE_COLOR, width=2)
            d.rounded_rectangle([x0 + 24, y0 + 24, x0 + 64, y0 + 64], radius=10, fill=color)
            d.text((x0 + 24, y0 + 90), label, font=label_f, fill=cream3)
            ty = y0 + 122
            for line in wrap_text(d, tag, tag_f, cell_w - 48)[:2]:
                d.text((x0 + 24, ty), line, font=tag_f, fill=gray_light)
                ty += 22
        caption_below(d, "free tools that teach the method, not just hand you an answer")
        return img

    def screen_article():
        img, d = new_overlay()
        tag_f = font(BOLD, 20)
        tag_text = "STAY SAFE"
        tw = d.textlength(tag_text, font=tag_f)
        d.rounded_rectangle([CX0 + 50, CY0 + 40, CX0 + 50 + tw + 32, CY0 + 78], radius=17, fill=orange3)
        d.text((CX0 + 66, CY0 + 49), tag_text, font=tag_f, fill=(0, 0, 0))
        title_f = font(BOLD, 40)
        d.text((CX0 + 50, CY0 + 96), "Turn On Two-Factor,", font=title_f, fill=cream3)
        d.text((CX0 + 50, CY0 + 144), "the Right Way", font=title_f, fill=orange3)
        stat_f = font(MONO_REG, 20)
        d.text((CX0 + 50, CY0 + 202), "$ context -- 5 min read", font=stat_f, fill=gray_light)
        body_widths = [0.86, 0.78, 0.9, 0.7, 0.82]
        by = CY0 + 254
        for wfrac in body_widths:
            bw = (CX1 - CX0 - 100) * wfrac
            d.rounded_rectangle([CX0 + 50, by, CX0 + 50 + bw, by + 14], radius=7, fill=(60, 55, 46))
            by += 30
        cl_y0 = by + 30
        d.rounded_rectangle([CX0 + 50, cl_y0, CX1 - 50, cl_y0 + 150], radius=14, outline=LINE_COLOR, width=2)
        item_f = font(REG, 22)
        items = ["Turn on 2FA on email first", "Use an authenticator app, not SMS", "Save backup codes somewhere safe"]
        iy = cl_y0 + 22
        for item in items:
            d.line([CX0 + 74, iy + 14, CX0 + 82, iy + 22], fill=green, width=3)
            d.line([CX0 + 82, iy + 22, CX0 + 98, iy + 4], fill=green, width=3)
            d.text((CX0 + 116, iy), item, font=item_f, fill=cream3)
            iy += 40
        caption_below(d, "step-by-step, plain language, every term explained")
        return img

    def screen_news():
        img, d = new_overlay()
        items = [
            (blue, "Major password manager breach exposes metadata", "BleepingComputer . 2h ago"),
            (violet, "New AI browser extension quietly reads your pages", "The Verge . 5h ago"),
            (blue, "Ransomware gang leaks data after refusing to pay", "Krebs on Security . 1d ago"),
            (violet, "Popular chatbot app changes its chat training policy", "Ars Technica . 1d ago"),
        ]
        headline_f = font(BOLD, 25)
        sub_f = font(MONO_REG, 18)
        iy = CY0 + 50
        for color, headline, sub in items:
            d.ellipse([CX0 + 48, iy + 10, CX0 + 64, iy + 26], fill=color)
            d.text((CX0 + 86, iy), headline, font=headline_f, fill=cream3)
            d.text((CX0 + 86, iy + 36), sub, font=sub_f, fill=gray_light)
            iy += 100
        caption_below(d, "cyber news and AI news -- every day, sourced and dated")
        return img

    def screen_toolkit():
        img, d = new_overlay()
        cats = [
            ("PASSWORD MANAGERS", orange3), ("VPNS", blue),
            ("AUTHENTICATOR APPS", green), ("BROWSERS", violet),
        ]
        cols = 2
        pad = 30
        cell_w = (CX1 - CX0 - pad * (cols + 1)) / cols
        cell_h = 160
        label_f = font(MONO_BOLD, 19)
        for i, (label, color) in enumerate(cats):
            r, c = divmod(i, cols)
            x0 = CX0 + pad + c * (cell_w + pad)
            y0 = CY0 + 90 + r * (cell_h + pad)
            x1 = x0 + cell_w
            d.rounded_rectangle([x0, y0, x1, y0 + cell_h], radius=14, outline=LINE_COLOR, width=2)
            d.rounded_rectangle([x0 + 24, y0 + 24, x0 + 64, y0 + 64], radius=10, fill=color)
            lw = d.textlength(label, font=label_f)
            lx = min(x0 + 24, x1 - 20 - lw)
            d.text((lx, y0 + 90), label, font=label_f, fill=cream3)
        caption_below(d, "real tools, picked for what they actually protect -- never sponsored")
        return img

    overlays = [screen_hero(), screen_pillars(), screen_utilities(), screen_article(), screen_news(), screen_toolkit()]

    # Each screen's complete "window" (chrome + that screen's own content,
    # composited once) plain-crossfades into the next -- no drift, and
    # fast (0.45s) specifically to keep the moment where both screens are
    # partially visible as brief as possible, since two busy screens'
    # text does visibly double-expose for an instant on a slower fade.
    # static_bg (grid + card border) never changes and sits underneath
    # every frame.
    window_chrome = render_window_chrome()
    windows = [Image.alpha_composite(window_chrome, ov) for ov in overlays]
    static_bg = rec.img.convert('RGBA')

    def compose(*layers):
        frame = static_bg.copy()
        for layer in layers:
            frame = Image.alpha_composite(frame, layer)
        return frame

    def save_frame(frame):
        frame.convert('RGB').save(os.path.join(rec.out_dir, f"frame_{rec.index:04d}.png"))
        rec.index += 1

    def fade_alpha(layer, mult):
        faded = layer.copy()
        faded.putalpha(faded.split()[3].point(lambda a, m=mult: int(a * m)))
        return faded

    prev_win = None
    for win in windows:
        n_trans = sec_frames(0.45)
        for step in range(1, n_trans + 1):
            t = ease(step / n_trans)
            layers = []
            if prev_win is not None:
                layers.append(fade_alpha(prev_win, 1 - t))
            layers.append(fade_alpha(win, t))
            save_frame(compose(*layers))
        rec.img = compose(win).convert('RGB')
        rec.draw = ImageDraw.Draw(rec.img)
        rec.hold_last_frame(sec_frames(3.0))
        prev_win = win

    # ================= Act 4: brand lockup, reprised =================
    _fade_to_clean_base(rec, sec_frames(1.3))

    wordmark_font2 = font(BOLD, 76)
    wordmark_segments2 = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments2, wordmark_font2, x='center', y=430, num_frames=sec_frames(1.3))
    rec.hold_last_frame(sec_frames(0.6))

    motto_font2 = font(MONO_BOLD, 28)
    motto_segments2 = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    fade_in_segments(rec, motto_segments2, motto_font2, x='center', y=530, num_frames=sec_frames(1.0))
    rec.hold_last_frame(sec_frames(0.6))

    tagline_font2 = font(MONO_BOLD, 26)
    tagline_segments2 = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments2, tagline_font2, x='center', y=580, num_frames=sec_frames(1.0))
    rec.hold_last_frame(sec_frames(2.4))

    # ================= Act 5: CTA =================
    _fade_to_clean_base(rec, sec_frames(1.2))

    cta_font = font(BOLD, 54)
    cta_segments = [("Like", orange3), (". ", cream3), ("Share", orange3), (". ", cream3),
                     ("Follow", orange3), (". ", cream3), ("Comment", orange3), (".", cream3)]
    fade_in_segments(rec, cta_segments, cta_font, x='center', y=470, num_frames=sec_frames(1.3))
    rec.hold_last_frame(sec_frames(2.2))

    _fade_to_clean_base(rec, sec_frames(1.0))

    closer_font = font(BOLD, 50)
    closer_segments = [("Trust me, it's worth it.", orange3)]
    fade_in_segments(rec, closer_segments, closer_font, x='center', y=500, num_frames=sec_frames(1.4))
    rec.hold_last_frame(sec_frames(2.2))

    # ---- final beat: the actual site link, plain and legible, the same
    # "$ " terminal-prompt convention used throughout Act 3 ----
    _fade_to_clean_base(rec, sec_frames(1.0))

    link_label_font = font(MONO_BOLD, 24)
    link_label_segments = [("$ open ", gray_light)]
    fade_in_segments(rec, link_label_segments, link_label_font, x='center', y=478, num_frames=sec_frames(0.7))

    link_url_font = font(MONO_BOLD, 42)
    link_url_segments = [("stayhumansec.github.io", orange3)]
    fade_in_segments(rec, link_url_segments, link_url_font, x='center', y=524, num_frames=sec_frames(0.9))
    rec.hold_last_frame(sec_frames(3.2))

    total_frames = rec.index - 1
    assemble_video(out_dir, video_path, fps=fps)
    return total_frames


if __name__ == "__main__":
    print("This is a library, not a script to run directly.")
    print("Import it: from animate import FrameRecorder, wobbly_animated, assemble_video")
    print("See animate_clean_smiley() for a full worked example.")
