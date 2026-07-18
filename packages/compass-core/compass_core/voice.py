"""TTS / ASR helpers for oral interview mode.

TTS: edge-tts (no cloud key)
ASR: faster-whisper if installed; else returns empty + warning
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


def synthesize_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural", out_path: str | Path | None = None) -> dict:
    """Generate mp3/wav via edge-tts. Returns {path, warning}."""
    text = (text or "").strip()
    if not text:
        return {"path": None, "warning": "empty text"}
    out = Path(out_path) if out_path else Path(tempfile.mkstemp(suffix=".mp3")[1])
    try:
        import edge_tts

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(out))

        asyncio.run(_run())
        return {"path": str(out), "warning": ""}
    except ImportError:
        return {"path": None, "warning": "edge-tts not installed: pip install edge-tts"}
    except Exception as e:
        return {"path": None, "warning": f"TTS failed: {e}"}


def transcribe_audio(audio_path: str | Path, language: str | None = "zh") -> dict:
    """ASR with faster-whisper. Returns {text, warning}."""
    path = Path(audio_path) if audio_path else None
    if not path or not path.is_file():
        return {"text": "", "warning": "no audio file"}
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(str(path), language=language)
        text = " ".join(s.text.strip() for s in segments).strip()
        return {"text": text, "warning": "" if text else "empty transcription"}
    except ImportError:
        return {
            "text": "",
            "warning": "faster-whisper not installed; type your answer or pip install faster-whisper",
        }
    except Exception as e:
        return {"text": "", "warning": f"ASR failed: {e}"}


# Friendly voice presets
VOICES = {
    "zh-female": "zh-CN-XiaoxiaoNeural",
    "zh-male": "zh-CN-YunxiNeural",
    "en-female": "en-US-JennyNeural",
    "en-male": "en-US-GuyNeural",
}
