"""Assemble silent slideshow MP4/GIF from docs/promo/shots."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "shots"
OUT = ROOT / "out"
OUT.mkdir(parents=True, exist_ok=True)

ORDER = [
    ("01-home.png", 4.0),
    ("02-discover.png", 5.0),
    ("03-match.png", 5.5),
    ("04-resume-analysis.png", 4.5),
    ("05-resume-patch.png", 5.0),
    ("06-interview.png", 5.5),
    ("07-diagnose.png", 5.0),
    ("08-resume-final.png", 6.0),
    ("09-endcard.png", 4.0),
]


def main() -> int:
    try:
        from PIL import Image
        import imageio.v2 as imageio
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pillow", "imageio", "imageio-ffmpeg", "-q"]
        )
        from PIL import Image
        import imageio.v2 as imageio

    target = (1280, 720)
    frames = []
    for name, sec in ORDER:
        p = SHOTS / name
        if not p.exists():
            print(f"missing {name}", file=sys.stderr)
            continue
        im = Image.open(p).convert("RGB")
        im.thumbnail(target, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", target, (18, 28, 40))
        canvas.paste(im, ((target[0] - im.size[0]) // 2, (target[1] - im.size[1]) // 2))
        n = max(1, int(sec * 2))
        for _ in range(n):
            frames.append(canvas.copy())

    mp4 = OUT / "compass-backend-demo-silent.mp4"
    imageio.mimsave(mp4, frames, fps=2, codec="libx264", quality=8)
    gif = OUT / "compass-backend-demo.gif"
    imageio.mimsave(gif, frames[::3], fps=1, loop=0)
    print(f"wrote {mp4} ({len(frames)} frames)")
    print(f"wrote {gif}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
