"""Compass promo narration: fluent Edge TTS (SSML) + ffmpeg mux."""
from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys
import wave
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "shots"
OUT = ROOT / "out"
SRT = OUT / "narration.zh.srt"
ORDER = [
    "01-home.png",
    "02-discover.png",
    "03-match.png",
    "04-resume-analysis.png",
    "05-resume-patch.png",
    "06-interview.png",
    "07-diagnose.png",
    "08-resume-final.png",
    "09-endcard.png",
]

# Xiaoxiao + slight speed-up: natural demo cadence without drag
EDGE_VOICE = "zh-CN-XiaoxiaoNeural"
EDGE_RATE = "+12%"
EDGE_PITCH = "+0Hz"
# Soft pause between sections (ms) — short enough to feel continuous
SECTION_BREAK_MS = 180
BREATH_SEC = 0.08


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text.strip())
    cues: list[tuple[float, float, str]] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        if re.fullmatch(r"\d+", lines[0]):
            lines = lines[1:]
        if "-->" not in lines[0]:
            continue
        a, b = [x.strip() for x in lines[0].split("-->")]
        cues.append((_ts(a), _ts(b), " ".join(lines[1:])))
    return cues


def _ts(s: str) -> float:
    s = s.replace(",", ".")
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def soften_for_tts(text: str) -> str:
    """Only rewrite tokens that make Edge TTS stumble (hyphenated EN / jargon).

    Keep short product words like Java / Compass — Xiaoyi handles them fine when
    the surrounding sentence is clean Mandarin.
    """
    soft = [
        ("skill-gap", "技能缺口"),
        ("resume-patch", "简历改写"),
        ("scorecard", "评分卡"),
        ("requirement matrix", "需求对照表"),
        ("discover multi", "多源岗位发现"),
        ("evidence_id", "证据编号"),
        ("QinHsiu", "秦休"),
        ("P99", "峰值延迟"),
        ("STAR", "情境任务行动结果"),
    ]
    out = text
    for a, b in soft:
        out = out.replace(a, b)
    return out


def build_ssml(paragraphs: list[str], voice: str) -> str:
    """One SSML document with short breaks — continuous prosody, no hard cuts."""
    parts: list[str] = []
    for i, p in enumerate(paragraphs):
        t = soften_for_tts(p).strip()
        if not t.endswith(("。", "！", "？", ".", "!", "?")):
            t += "。"
        parts.append(escape(t))
        if i < len(paragraphs) - 1:
            parts.append(f'<break time="{SECTION_BREAK_MS}ms"/>')
    body = "\n".join(parts)
    # No mstts:express-as — styles often add robotic pauses on some voices
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
  <voice name="{voice}">
    <prosody rate="{EDGE_RATE}" pitch="{EDGE_PITCH}">
      {body}
    </prosody>
  </voice>
</speak>"""


def build_plain_script(paragraphs: list[str]) -> str:
    """Single spoken essay — preferred when SSML pacing feels sticky."""
    chunks = []
    for p in paragraphs:
        t = soften_for_tts(p).strip()
        if not t.endswith(("。", "！", "？", ".", "!", "?")):
            t += "。"
        chunks.append(t)
    # Thin space pause via Chinese comma between sections (TTS breathes naturally)
    return "".join(chunks)


def to_wav(src: Path, dst: Path, rate: int = 24000) -> None:
    ff = ffmpeg_exe()
    r = subprocess.run(
        [ff, "-y", "-i", str(src), "-ac", "1", "-ar", str(rate), "-sample_fmt", "s16", str(dst)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1500:])


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def write_silence_wav(path: Path, seconds: float, rate: int = 24000) -> None:
    n = max(0, int(seconds * rate))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * n)


def concat_wavs(parts: list[Path], out: Path) -> float:
    frames = []
    rate = None
    params = None
    for p in parts:
        with wave.open(str(p), "rb") as w:
            if rate is None:
                rate = w.getframerate()
                params = w.getparams()
            frames.append(w.readframes(w.getnframes()))
    assert rate is not None and params is not None
    with wave.open(str(out), "wb") as w:
        w.setparams(params)
        for fr in frames:
            w.writeframes(fr)
    return wav_duration(out)


def polish_audio(src_wav: Path, dst_mp3: Path) -> None:
    """Normalize + gentle highpass; slight tempo lift if draggy."""
    ff = ffmpeg_exe()
    # loudnorm + mild highpass; atempo 1.04 keeps energy without sounding rushed
    af = "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11,atempo=1.06"
    r = subprocess.run(
        [
            ff, "-y", "-i", str(src_wav),
            "-af", af,
            "-codec:a", "libmp3lame", "-q:a", "2",
            str(dst_mp3),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        # fallback without filters
        subprocess.run(
            [ff, "-y", "-i", str(src_wav), "-codec:a", "libmp3lame", "-q:a", "2", str(dst_mp3)],
            check=True,
            capture_output=True,
        )


async def edge_ssml_mp3(ssml: str, out: Path, voice: str) -> None:
    import edge_tts

    # When SSML includes <voice>, edge-tts still wants a voice arg (same name)
    await edge_tts.Communicate(ssml, voice).save(str(out))


async def edge_plain_mp3(text: str, out: Path, voice: str) -> None:
    import edge_tts

    await edge_tts.Communicate(
        soften_for_tts(text),
        voice,
        rate=EDGE_RATE,
        pitch=EDGE_PITCH,
    ).save(str(out))


async def synth_edge(cues: list[tuple[float, float, str]], work: Path, voice: str) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    paragraphs = [t for _, _, t in cues]
    plain = build_plain_script(paragraphs)
    (work / "narration.txt").write_text(plain, encoding="utf-8")
    mp3 = work / "full.mp3"
    wav = work / "full.wav"
    print(f"edge plain continuous ({len(plain)} chars, voice={voice}, rate={EDGE_RATE})…")
    try:
        # Prefer plain continuous Mandarin — smoother than SSML on Edge neural
        await edge_plain_mp3(plain, mp3, voice)
        to_wav(mp3, wav)
        narr_wav = wav
    except Exception as e:
        print(f"plain pass failed ({e}); trying SSML…")
        ssml = build_ssml(paragraphs, voice)
        (work / "narration.ssml").write_text(ssml, encoding="utf-8")
        try:
            await edge_ssml_mp3(ssml, mp3, voice)
            to_wav(mp3, wav)
            narr_wav = wav
        except Exception as e2:
            print(f"SSML failed ({e2}); soft-stitch cues…")
            parts: list[Path] = []
            breath = work / "breath.wav"
            write_silence_wav(breath, BREATH_SEC)
            for i, (_s, _e, text) in enumerate(cues):
                c_mp3 = work / f"cue_{i:02d}.mp3"
                c_wav = work / f"cue_{i:02d}.wav"
                await edge_plain_mp3(text, c_mp3, voice)
                to_wav(c_mp3, c_wav)
                parts.append(c_wav)
                if i < len(cues) - 1:
                    parts.append(breath)
            narr_wav = work / "narration.wav"
            concat_wavs(parts, narr_wav)

    narr_mp3 = OUT / "narration.zh.mp3"
    polish_audio(narr_wav, narr_mp3)
    print(f"narration -> {narr_mp3} ({audio_duration_ff(narr_mp3):.1f}s)")
    return narr_mp3


def audio_duration_ff(path: Path) -> float:
    ff = ffmpeg_exe()
    r = subprocess.run([ff, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", r.stderr or "")
    if not m:
        return 90.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def build_silent_video(duration: float, out_path: Path) -> Path:
    from PIL import Image
    import imageio.v2 as imageio

    fps = 2
    target = (1280, 720)
    n = max(fps, int(round(duration * fps)))
    paths = [SHOTS / name for name in ORDER if (SHOTS / name).exists()]
    frames = []
    # Weight later slides slightly longer (resume/end)
    weights = [1.0, 1.1, 1.15, 1.0, 1.15, 1.2, 1.05, 1.35, 1.0]
    weights = weights[: len(paths)]
    total_w = sum(weights)
    allocated = [max(1, int(round(n * w / total_w))) for w in weights]
    drift = n - sum(allocated)
    allocated[-1] = max(1, allocated[-1] + drift)
    for path, count in zip(paths, allocated):
        im = Image.open(path).convert("RGB")
        im.thumbnail(target, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", target, (18, 28, 40))
        canvas.paste(im, ((target[0] - im.size[0]) // 2, (target[1] - im.size[1]) // 2))
        frames.extend([canvas.copy()] * count)
    imageio.mimsave(out_path, frames, fps=fps, codec="libx264", quality=8)
    return out_path


def mux(video: Path, audio: Path, out: Path) -> None:
    ff = ffmpeg_exe()
    cmd = [
        ff, "-y", "-i", str(video), "-i", str(audio),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:], file=sys.stderr)
        raise SystemExit(r.returncode)


async def amain() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=EDGE_VOICE)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts", "imageio-ffmpeg", "-q"])

    cues = parse_srt(SRT)
    work = OUT / "_tts_work"
    narr = await synth_edge(cues, work, args.voice)
    dur = audio_duration_ff(narr)
    print(f"audio ≈ {dur:.1f}s")
    silent = OUT / "_silent.mp4"
    build_silent_video(dur + 0.4, silent)
    tmp = OUT / "_with_audio.mp4"
    mux(silent, narr, tmp)
    silent.unlink(missing_ok=True)
    final = OUT / "compass-backend-demo.mp4"
    if final.exists():
        final.unlink()
    tmp.rename(final)
    print(f"done -> {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(amain()))
