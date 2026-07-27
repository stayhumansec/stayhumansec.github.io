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
import subprocess

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

    for step in range(1, num_frames + 1):
        chars_shown = max(1, round(total_chars * step / num_frames))
        frame = base.copy()
        draw_prefix(frame, chars_shown, cursor and chars_shown < total_chars)
        frame.save(os.path.join(recorder.out_dir, f"frame_{recorder.index:04d}.png"))
        recorder.index += 1

    final = base.copy()
    draw_prefix(final, total_chars, False)
    recorder.img = final
    recorder.draw = ImageDraw.Draw(recorder.img)


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
    """30-second brand + site story, built for someone who has never heard
    of stay(human).sec and isn't a security person -- no terminal-scan
    gimmick, no jargon, just the site's own real philosophy and section
    copy, crossfading smoothly beat to beat (crossfade_text_beats(),
    eased via _smoothstep -- never a hard cut). Three acts:

      Act 1 (0-6s / 120f): the philosophy, verbatim from index.html's
        "What we are" section -- "Not a company." / "Not a bot." / "Just
        one person -- explaining this properly."
      Act 2 (6-21s / 300f): a tour of what's actually on the site, six
        beats pulled from the homepage's own router-card copy and each
        page's own real header line (You Check / Glossary / Posts /
        Toolkit / News / on(my).mind), color-dotted to match each
        section's real accent color.
      Act 3 (21-30s / 180f): the same brand lockup as animate_brand_intro
        -- icon draws in, wordmark fades in, motto types out, tagline
        fades in -- so it still ends on one screenshot-recognizable frame.
      Act 4 (30-33s / 60f): a like/share/follow line fades in beneath the
        still-visible lockup (the lockup itself is never disturbed, so
        the screenshot-recognizable frame from Act 3 still holds) --
        "LIKE. SHARE. FOLLOW FOR ONE NEW FILE, EVERY DAY.", matching the
        real closer pattern already used across the Instagram captions
        (AUTOMATED-WORKFLOW.md's slide-4 Like/Comment/Follow prompt, and
        the site footer's "new file added every day").

    Frame budget at 20fps/33s = 660 frames total, split 120/300/180/60.
    """
    from generate_post import (base_card, quad_bezier, gray_light, blue, green, gold, pink, violet,
                                font, BOLD, REG, MONO_BOLD)

    img, d = base_card()
    rec = FrameRecorder(img, d, out_dir)

    headline_font = font(BOLD, 56)
    sub_font = font(REG, 26)

    # ---- Act 1+2 (0-21s / 420 frames): philosophy, then a tour of what's
    # actually here -- ONE crossfade_text_beats() call spanning both, so
    # the crossfade-from-previous-beat state carries across the act
    # boundary too (see crossfade_text_beats' docstring: splitting a
    # sequence across multiple calls degrades the first beat of the next
    # call into a fade-in over whatever's already baked into the frozen
    # base -- i.e. the previous act's last beat would linger, unfaded,
    # underneath the new one instead of actually crossfading out).
    def beat(dot_color, headline, sub_line=None):
        lines = [([(headline, cream3)], headline_font, 490 if sub_line else 510)]
        if sub_line:
            lines.append(([(sub_line, gray_light)], sub_font, 570))
        return {"dot": dot_color, "lines": lines}

    # Real copy throughout: index.html's "What we are" section for the
    # philosophy beats, router-card lines plus news.html's/notes.html's
    # own header lines for the tour beats -- nothing invented.
    story_beats = [
        {"dot": None, "lines": [([("Not a company.", cream3)], headline_font, 510)]},
        {"dot": None, "lines": [([("Not a bot.", cream3)], headline_font, 510)]},
        {"dot": None, "lines": [
            ([("Just one person —", cream3)], headline_font, 470),
            ([("explaining this properly.", cream3)], headline_font, 540),
        ]},
        beat(pink, "Am I safe right now?", "Answer a few honest questions, get the exact posts that close your gaps."),
        beat(blue, "Teach me a term.", "Every piece of jargon on this site, explained like a friend would."),
        beat(green, "Show me the files.", "Browse every post, filterable by how often it drops."),
        beat(gold, "What should I install?", "The password managers, VPNs, and apps actually worth using."),
        beat(blue, "Real stories, sourced.", "Cyber News and AI News, straight from the source — never invented."),
        beat(violet, "on(my).mind", "Unpolished, on purpose — the thinking behind why this exists."),
        None,  # fades the last beat out to a clean base before Act 3's icon starts drawing
    ]
    crossfade_text_beats(rec, story_beats, transition_frames=15,
                          hold_frames=[15, 15, 45, 35, 35, 35, 35, 35, 20, 0])
    # 10 beats x 15f transition + sum(holds) = 150 + 270 = 420 frames, exactly 21.0s

    # ---- Act 3 (21-30s / 180 frames): brand lockup ----
    ISCALE = 4.0
    OFFX, OFFY = 540 - 75 * ISCALE, 300 - 55.5 * ISCALE

    def xf(pt):
        return (OFFX + pt[0] * ISCALE, OFFY + pt[1] * ISCALE)

    left_bracket = quad_bezier(xf((38, 16)), xf((20, 50)), xf((38, 84)), steps=60)
    wobbly_animated(rec, left_bracket, cream3, 10, 1.2, seed=301, num_frames=14)
    right_bracket = quad_bezier(xf((112, 16)), xf((130, 50)), xf((112, 84)), steps=60)
    wobbly_animated(rec, right_bracket, cream3, 10, 1.2, seed=302, num_frames=14)
    head_cx, head_cy = xf((75, 38))
    grow_circle(rec, head_cx, head_cy, max_r=13 * ISCALE, color=orange3, num_frames=10)
    body_arc = [xf((75 + 17 * math.cos(math.radians(a)), 78 + 17 * math.sin(math.radians(a))))
                for a in range(180, 361, 4)]
    wobbly_animated(rec, body_arc, orange3, 7, 1.0, seed=303, num_frames=12)
    rec.hold_last_frame(10)  # 50 + 10 = 60 frames, 3.0s

    wordmark_font = font(BOLD, 88)
    wordmark_segments = [("stay", cream3), ("(human)", orange3), (".sec", cream3)]
    fade_in_segments(rec, wordmark_segments, wordmark_font, x='center', y=500, num_frames=30)
    rec.hold_last_frame(10)  # 40 frames, 2.0s

    motto_font = font(MONO_BOLD, 32)
    motto_text = [("FOR ", gray_light), ("HUMAN", orange3), (". FOR ", gray_light), ("PRIVACY", orange3), (".", gray_light)]
    motto_full = ''.join(s for s, _ in motto_text)
    motto_w = ImageDraw.Draw(rec.img).textlength(motto_full, font=motto_font)
    type_text_animated(rec, motto_text, motto_font, x=(1080 - motto_w) / 2, y=630, num_frames=25)
    rec.hold_last_frame(5)  # 30 frames, 1.5s

    tagline_font = font(MONO_BOLD, 30)
    tagline_segments = [
        ("USE ", cream3), ("AI", orange3), (". REMAIN ", cream3), ("HUMAN", orange3),
        (". ", cream3), ("PRIVACY", orange3), (" MATTERS.", cream3),
    ]
    fade_in_segments(rec, tagline_segments, tagline_font, x='center', y=700, num_frames=30)
    rec.hold_last_frame(20)  # 50 frames, 2.5s
    # 60 + 40 + 30 + 50 = 180 frames, exactly 9.0s

    # ---- Act 4 (30-33s / 60 frames): like/share/follow, added beneath
    # the still-visible lockup -- the lockup itself is never disturbed,
    # so Act 3's screenshot-recognizable frame still holds throughout ----
    cta_font = font(MONO_BOLD, 24)
    cta_segments = [
        ("LIKE", orange3), (". ", gray_light), ("SHARE", orange3), (". ", gray_light),
        ("FOLLOW", orange3), (" FOR ONE NEW FILE, EVERY DAY.", gray_light),
    ]
    fade_in_segments(rec, cta_segments, cta_font, x='center', y=800, num_frames=25)
    rec.hold_last_frame(35)  # 25 + 35 = 60 frames, exactly 3.0s

    total_frames = rec.index - 1
    assemble_video(out_dir, video_path, fps=fps)
    return total_frames


if __name__ == "__main__":
    print("This is a library, not a script to run directly.")
    print("Import it: from animate import FrameRecorder, wobbly_animated, assemble_video")
    print("See animate_clean_smiley() for a full worked example.")
