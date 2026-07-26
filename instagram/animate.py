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

import os
import random
import shutil
import subprocess

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


def assemble_video(frame_dir, output_path, fps=20, pattern="frame_%04d.png"):
    """Stitches numbered frame PNGs in frame_dir into an MP4 via ffmpeg.

    fps is the readability control the brief asked for — roughly 15-25 fps
    is the sweet spot for a hand-drawn reveal: fast enough not to drag,
    slow enough to actually follow the stroke landing. Pass a lower value
    (e.g. 10) to linger longer, or higher (e.g. 30) for a snappier reveal.
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
        "-vf", "scale=1080:1080",
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


if __name__ == "__main__":
    print("This is a library, not a script to run directly.")
    print("Import it: from animate import FrameRecorder, wobbly_animated, assemble_video")
    print("See animate_clean_smiley() for a full worked example.")
