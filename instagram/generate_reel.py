"""
generate_reel.py — Reels production library for stay(human).sec

Fifth platform package alongside the Instagram carousel / Facebook / LinkedIn
/ X packaging already built by generate_post.py (see AUTOMATED-WORKFLOW.md's
"Platform-specific packaging" section) — same underlying fact/fix, a
different format. This is a rendering/production LIBRARY, not a script:
import and call its functions the same way generate_post.py is used.

Pipeline:

    script text (hand-written, see AUTOMATED-WORKFLOW.md step 2)
        -> Piper TTS voiceover (free, local, no API key)
        -> word-level timing (faster-whisper, transcribing our own audio)
        -> karaoke-style burned captions (.ass, brand fonts/colors)
        -> brand-styled hook overlay (first ~2s, mirrors carousel Slide 1)
        -> ffmpeg composite over background footage
        -> 1080x1920 reel.mp4

Usage pattern for a new day's Reel:

    from generate_reel import *

    script_text = open("reel_script.txt", encoding="utf-8").read().strip()
    build_reel_from_script(
        script_text=script_text,
        background_path="bg_footage.mp4",
        hook_text="Incognito mode doesn't hide you from your ISP",
        hook_tag="MYTH BUSTED",
        hook_tag_color=pink,
        out_path="instagram/posts/day_NN_topic-slug/reel.mp4",
    )
    verify_reel("instagram/posts/day_NN_topic-slug/reel.mp4")

IMPORTANT — verify before considering the Reel done, same discipline
verify_slide() already enforces for carousel images:

    verify_reel(path) checks resolution (1080x1920), confirms the file
    isn't zero-length/corrupt, and confirms an audio track exists whose
    duration roughly matches the video. Never ship an unverified Reel.

COST: Piper TTS is the default and only supported path for voiceover —
free, open-source, runs locally on CPU, no API key, no monthly quota. This
is a hard constraint (the account has no budget for paid APIs right now),
not a style preference. synthesize_voiceover_elevenlabs() exists below as
an OPTIONAL upgrade path, clearly not the default — only reach for it once
the account has revenue to justify a paid tier.
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Reuse the exact same brand palette generate_post.py already defines —
# single source of truth for both libraries, see CLAUDE.md's Brand system
# table for what these map to on the live site (--cream, --orange, etc.).
from generate_post import cream3, orange3, blue, green, violet, gold, pink, gray, gray_light

CANVAS_W, CANVAS_H = 1080, 1920

# ============================================================
# FONTS
#
# The live site swapped from Poppins/JetBrains Mono to Sora (prose/
# headings) + IBM Plex Mono (anything meant to read as terminal/technical
# text) -- see the Typography rule in CLAUDE.md. generate_post.py's
# carousel slides still use the pre-swap Poppins bundle (a separate,
# already-shipped system; out of scope to change here), but this Reel
# pipeline is new, so it uses the *current* brand fonts, not the old ones.
#
# PIL and ffmpeg's libass both need real .ttf/.otf files -- the site only
# ships .woff2 (web format) in /fonts, so these five weights were
# converted once via fonttools (`TTFont(src); font.flavor = None;
# font.save(dst)`) from the site's own woff2 files and bundled here the
# same way generate_post.py bundles Poppins (relative path, not a system
# font — not guaranteed installed in every environment this runs in).
# Same SIL Open Font License as documented at /fonts/LICENSE.txt for both
# Sora and IBM Plex Mono; nothing new to license since these are the same
# font files the site already ships, just re-flavored to .ttf.
# ============================================================
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
SORA_REGULAR = os.path.join(_FONT_DIR, "Sora-Regular.ttf")
SORA_BOLD = os.path.join(_FONT_DIR, "Sora-Bold.ttf")
SORA_EXTRABOLD = os.path.join(_FONT_DIR, "Sora-ExtraBold.ttf")
MONO_REGULAR = os.path.join(_FONT_DIR, "IBMPlexMono-Regular.ttf")
MONO_BOLD = os.path.join(_FONT_DIR, "IBMPlexMono-Bold.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


def _rgb_to_ass(rgb, alpha=0x00):
    """ASS/SSA color format is &HAABBGGRR (alpha, then BGR, reversed byte
    order from the RGB tuples generate_post.py's palette uses) -- convert
    once here rather than hand-transcribing hex per color like the
    reference implementation did (that's how it drifted from the real
    brand palette in the first place)."""
    r, g, b = rgb
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


# ============================================================
# 1. Voiceover generation — Piper TTS (free, local, no API key, no quota).
#    This is the default and only supported path right now; see module
#    docstring's COST note.
# ============================================================
def synthesize_voiceover_piper(text, out_path, piper_model="en_US-lessac-medium",
                                piper_voices_dir=None):
    """Generates a voiceover with Piper TTS -- open-source, CPU-only, no API
    key, no per-character cost, no attribution requirement, no monthly cap.

    One-time setup:
        pip install piper-tts
        python -m piper.download_voices en_US-lessac-medium

    Browse voices at https://rhasspy.github.io/piper-samples/ and pick one
    that fits the brand voice -- keep it consistent across every Reel once
    chosen, don't switch voice per post."""
    out_path = Path(out_path)
    piper_voices_dir = Path(piper_voices_dir) if piper_voices_dir else Path("piper_voices")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    model_path = piper_voices_dir / f"{piper_model}.onnx"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Piper voice model not found at {model_path}. Run:\n"
            f"  python -m piper.download_voices {piper_model}"
        )

    wav_path = out_path.with_suffix(".wav")
    proc = subprocess.run(
        ["piper", "--model", str(model_path), "--output_file", str(wav_path)],
        input=text, text=True, capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Piper TTS failed: {proc.stderr}")

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame",
         "-qscale:a", "2", str(out_path)],
        check=True, capture_output=True,
    )
    wav_path.unlink(missing_ok=True)
    return out_path


def synthesize_voiceover_elevenlabs(text, out_path, voice_id, api_key=None,
                                     model_id="eleven_multilingual_v2"):
    """OPTIONAL upgrade path, NOT the default -- see module docstring's COST
    note. ElevenLabs' free tier caps at ~10 min of audio/month and requires
    attribution unless on a paid plan (~$5-6/mo and up). Revisit once the
    account has revenue, not before. Requires `pip install elevenlabs`."""
    from elevenlabs.client import ElevenLabs

    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("Set ELEVENLABS_API_KEY or pass api_key=")

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=model_id,
        text=text,
        voice_settings={"stability": 0.45, "similarity_boost": 0.85, "style": 0.2},
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return out_path


# ============================================================
# 2. Word-level timing (for caption chunking) — transcribe our OWN
#    generated audio, not raw mic input, so accuracy is high and fast
#    even on CPU.
# ============================================================
@dataclass
class Word:
    text: str
    start: float
    end: float


def transcribe_words(audio_path, model_size="small"):
    """Uses faster-whisper to get word-level timestamps from the voiceover.
    Requires `pip install faster-whisper`."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio_path), word_timestamps=True)

    words = []
    for seg in segments:
        for w in seg.words:
            words.append(Word(text=w.word.strip(), start=w.start, end=w.end))
    return words


# ============================================================
# 3. Chunk words into short caption groups + write the .ass subtitle file,
#    styled with the site's actual brand fonts/colors (not the old
#    Poppins/generic palette the reference implementation used).
# ============================================================
def chunk_words(words, max_words=3):
    """Groups words into 2-3 word bursts -- the 'karaoke caption' style:
    fast reading pace, no subtitle wall. Skips empty groups (e.g. from
    leading/trailing whitespace words faster-whisper sometimes emits)."""
    chunks = []
    for i in range(0, len(words), max_words):
        group = [w for w in words[i:i + max_words] if w.text]
        if not group:
            continue
        text = " ".join(w.text for w in group)
        chunks.append((text, group[0].start, group[-1].end))
    return chunks


def write_ass_captions(chunks, out_path, font_path=MONO_BOLD, size=90,
                        primary=cream3, outline=(0, 0, 0), pos_y_pct=0.72):
    """Writes a styled .ass subtitle file for the karaoke-burst captions.
    Uses IBM Plex Mono (brand's 'technical/terminal' voice, per CLAUDE.md's
    Typography rule) rather than a prose font, since short punchy caption
    bursts read closer to on-screen stat callouts than body copy.
    pos_y_pct = vertical position as a fraction of canvas height (0.72 ~=
    lower-third, clear of on-screen annotations/hook overlay)."""
    out_path = Path(out_path)
    margin_v = int(CANVAS_H * (1 - pos_y_pct))
    # font family name embedded in the .ass style must match what libass's
    # fontconfig lookup resolves -- since these weights are bundled next to
    # this file rather than installed system-wide, callers running ffmpeg
    # must pass fontsdir (see build_reel()'s `ass=...:fontsdir=...` filter)
    # rather than relying on a system font-name match.
    font_family = "IBM Plex Mono"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {CANVAS_W}
PlayResY: {CANVAS_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Caption,{font_family},{size},{_rgb_to_ass(primary)},{_rgb_to_ass(outline)},&H00000000,1,1,6,0,2,60,60,{margin_v}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h:d}:{m:02d}:{s:05.2f}"

    lines = [header]
    for text, start, end in chunks:
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Caption,,0,0,0,,{text.upper()}\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(lines), encoding="utf-8")
    return out_path


# ============================================================
# 4. Hook overlay (first ~2 seconds) -- reads as the same voice/pacing as
#    the carousel's Slide 1 hook (tag_pill() + one short attention-grabbing
#    line, see AUTOMATED-WORKFLOW.md's "Standard workflow" 4-slide spec),
#    not a separate visual style invented for video.
# ============================================================
def make_hook_overlay_png(hook_text, out_path, tag_text=None, tag_color=orange3,
                           w=CANVAS_W, h=CANVAS_H):
    """Generates a transparent PNG: an optional rotated tag_pill()-style
    sticker (same category label a Slide 1 would carry -- 'MYTH BUSTED',
    'STAY SAFE', etc.) plus the hook line in bold Sora, over a
    semi-transparent band for legibility on any background. Overlaid on
    the first `hook_duration` seconds of the Reel by build_reel()."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    band_top, band_bottom = int(h * 0.30), int(h * 0.46)
    draw.rectangle([0, band_top, w, band_bottom], fill=(0, 0, 0, 160))

    hook_font = font(SORA_EXTRABOLD, 62)
    max_w = w - 140

    words, lines, cur = hook_text.split(), [], ""
    for word in words:
        test = f"{cur} {word}".strip()
        if draw.textlength(test, font=hook_font) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = test
    lines.append(cur)

    line_h = 80
    total_h = len(lines) * line_h
    tag_h = 56 if tag_text else 0
    content_h = total_h + (tag_h + 16 if tag_text else 0)
    y = band_top + ((band_bottom - band_top) - content_h) // 2

    if tag_text:
        _draw_tag_pill(img, w // 2, y, tag_text, tag_color)
        y += tag_h + 16

    for line in lines:
        tw = draw.textlength(line, font=hook_font)
        draw.text(((w - tw) / 2, y), line, font=hook_font, fill=cream3 + (255,))
        y += line_h

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def _draw_tag_pill(base_img, center_x, y, text, bg, fg=(255, 255, 255), angle=-3.4, font_size=26):
    """Rotated rounded 'sticker' tag pill matching generate_post.py's
    tag_pill(), centered horizontally at center_x rather than placed by a
    fixed x -- the Reel's hook overlay is centered, unlike a carousel
    slide's left-aligned chrome."""
    f = font(SORA_BOLD, font_size)
    tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    tw = td.textlength(text, font=f)
    pad = 22
    pw, ph = int(tw + pad * 2), 52
    margin = 60
    pill = Image.new("RGBA", (pw + margin * 2, ph + margin * 2), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle([margin, margin, margin + pw, margin + ph], radius=ph // 2, fill=bg + (255,))
    pd.text((margin + pad, margin + 14), text, font=f, fill=fg + (255,))
    rotated = pill.rotate(angle, resample=Image.BICUBIC, expand=True)
    x = center_x - rotated.width / 2
    base_img.paste(rotated, (int(x), int(y - margin)), rotated)


# ============================================================
# 5. Final ffmpeg composite
# ============================================================
def build_reel(background, audio, ass_path, hook_png, out_path, hook_duration=2.0):
    """Composites: background video (cropped/scaled to 1080x1920) + hook
    overlay for the first `hook_duration` seconds + burned-in karaoke
    captions (.ass, brand fonts via fontsdir) + voiceover audio."""
    background, audio = Path(background), Path(audio)
    ass_path, hook_png, out_path = Path(ass_path), Path(hook_png), Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # fontsdir points libass at this project's bundled Sora/IBM Plex Mono
    # weights (not a system font) -- without it, ffmpeg would silently
    # fall back to whatever default font is on the box running this,
    # exactly the kind of drift the reference implementation warned about.
    ass_filter = f"ass={ass_path.as_posix()}:fontsdir={_FONT_DIR}"
    filter_complex = (
        f"[0:v]scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=increase,"
        f"crop={CANVAS_W}:{CANVAS_H},setsar=1[bg];"
        f"[bg][1:v]overlay=0:0:enable='between(t,0,{hook_duration})'[hooked];"
        f"[hooked]{ass_filter}[captioned]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(background),
        "-i", str(hook_png),
        "-i", str(audio),
        "-filter_complex", filter_complex,
        "-map", "[captioned]", "-map", "2:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


# ============================================================
# End-to-end convenience wrapper -- runs stages 1-5 through a temp dir so
# a caller only needs to supply the script text, background clip, and hook.
# ============================================================
def build_reel_from_script(script_text, background_path, hook_text, out_path,
                            hook_tag=None, hook_tag_color=orange3,
                            piper_model="en_US-lessac-medium",
                            piper_voices_dir=None, whisper_model="small",
                            max_caption_words=3, hook_duration=2.0):
    """Runs the full pipeline: Piper voiceover -> word timing -> karaoke
    captions -> hook overlay -> ffmpeg composite. `script_text` is the
    already-written voiceover script (see AUTOMATED-WORKFLOW.md step 2 --
    this function consumes it, never generates it itself)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        audio_path = tmp / "voiceover.mp3"
        ass_path = tmp / "captions.ass"
        hook_png = tmp / "hook.png"

        synthesize_voiceover_piper(script_text, audio_path, piper_model=piper_model,
                                    piper_voices_dir=piper_voices_dir)
        words = transcribe_words(audio_path, model_size=whisper_model)
        chunks = chunk_words(words, max_words=max_caption_words)
        write_ass_captions(chunks, ass_path)
        make_hook_overlay_png(hook_text, hook_png, tag_text=hook_tag, tag_color=hook_tag_color)
        build_reel(background_path, audio_path, ass_path, hook_png, out_path,
                   hook_duration=hook_duration)

    return Path(out_path)


# ============================================================
# 6. Verification -- same "never ship unverified visual output" discipline
#    verify_slide()/verify_pdf_carousel() already enforce in
#    generate_post.py, not a weaker check just because this is a new
#    format.
# ============================================================
def verify_reel(path, expected_size=(CANVAS_W, CANVAS_H), max_duration_diff=1.5):
    """Call this after build_reel()/build_reel_from_script(). Uses ffprobe
    (bundled with ffmpeg, no extra dependency) to check:
      - the file exists and is non-zero-length
      - the video stream is exactly `expected_size` (1080x1920)
      - an audio stream exists
      - video and audio durations are within `max_duration_diff` seconds of
        each other (catches a silently-truncated or mismatched composite)
    Raises AssertionError with a specific reason on failure -- mirrors
    verify_slide()'s "blank image" assertion, just for video."""
    path = Path(path)
    assert path.exists() and path.stat().st_size > 0, f"{path}: missing or zero-length"

    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
         "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(proc.stdout)
    streams = info.get("streams", [])

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    assert video_streams, f"{path}: no video stream found"
    assert audio_streams, f"{path}: no audio stream found"

    v = video_streams[0]
    actual_size = (int(v["width"]), int(v["height"]))
    assert actual_size == tuple(expected_size), f"{path}: wrong size {actual_size}"

    video_duration = float(v.get("duration") or info["format"]["duration"])
    audio_duration = float(audio_streams[0].get("duration") or info["format"]["duration"])
    diff = abs(video_duration - audio_duration)
    assert diff <= max_duration_diff, (
        f"{path}: video/audio duration mismatch ({video_duration:.2f}s vs "
        f"{audio_duration:.2f}s, diff {diff:.2f}s > {max_duration_diff}s)"
    )

    print(f"✓ {path} — {actual_size}, {video_duration:.1f}s video / {audio_duration:.1f}s audio")
    return True


if __name__ == "__main__":
    print("This is a library, not a script to run directly.")
    print("Import it: from generate_reel import *")
    print("See the module docstring at the top of this file for usage.")
