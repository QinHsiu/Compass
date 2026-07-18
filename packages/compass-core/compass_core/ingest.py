"""Extract text from PDF / images / plain docs for resume ingest."""

from __future__ import annotations

from pathlib import Path


def extract_text(path: str | Path) -> dict:
    """
    Return {text, format, warnings[]}.
    Supports: .pdf .png .jpg .jpeg .webp .txt .md .docx(optional)
    """
    path = Path(path)
    if not path.is_file():
        return {"text": "", "format": "missing", "warnings": [f"file not found: {path}"]}

    suffix = path.suffix.lower()
    warnings: list[str] = []

    if suffix in (".txt", ".md", ".markdown"):
        return {"text": path.read_text(encoding="utf-8", errors="replace"), "format": suffix, "warnings": []}

    if suffix == ".pdf":
        text = _pdf_text(path, warnings)
        return {"text": text, "format": "pdf", "warnings": warnings}

    if suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"):
        text = _image_ocr(path, warnings)
        return {"text": text, "format": "image", "warnings": warnings}

    if suffix == ".docx":
        text = _docx_text(path, warnings)
        return {"text": text, "format": "docx", "warnings": warnings}

    # fallback: try utf-8
    try:
        return {
            "text": path.read_text(encoding="utf-8", errors="replace"),
            "format": "raw",
            "warnings": [f"unknown suffix {suffix}, read as text"],
        }
    except Exception as e:
        return {"text": "", "format": "error", "warnings": [str(e)]}


def _pdf_text(path: Path, warnings: list[str]) -> str:
    try:
        import fitz  # pymupdf

        doc = fitz.open(path)
        parts = [page.get_text("text") for page in doc]
        doc.close()
        text = "\n".join(parts).strip()
        if text:
            return text
        warnings.append("PDF had no extractable text; try OCR on rasterized pages")
    except ImportError:
        warnings.append("pymupdf not installed; pip install pymupdf")
    except Exception as e:
        warnings.append(f"pymupdf failed: {e}")

    try:
        from pdfminer.high_level import extract_text as pdfminer_extract

        text = (pdfminer_extract(str(path)) or "").strip()
        if text:
            return text
    except ImportError:
        warnings.append("pdfminer.six not installed")
    except Exception as e:
        warnings.append(f"pdfminer failed: {e}")
    return ""


def _image_ocr(path: Path, warnings: list[str]) -> str:
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+chi_sim")
        return (text or "").strip()
    except ImportError:
        warnings.append(
            "OCR needs pillow+pytesseract and system Tesseract. "
            "Fallback: paste resume text manually."
        )
    except Exception as e:
        warnings.append(f"OCR failed: {e}")
    return ""


def _docx_text(path: Path, warnings: list[str]) -> str:
    try:
        import docx

        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs if p.text.strip())
    except ImportError:
        warnings.append("python-docx not installed")
    except Exception as e:
        warnings.append(f"docx failed: {e}")
    return ""


def split_resume_to_evidence_drafts(text: str, max_items: int = 12) -> list[dict]:
    """Heuristic split of resume text into evidence draft dicts (user confirms)."""
    blocks: list[str] = []
    buf: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            if buf:
                blocks.append("\n".join(buf))
                buf = []
            continue
        # section headers often short + uppercase/chinese titles
        if buf and (s.startswith("•") or s.startswith("-") or s.startswith("*")):
            buf.append(s)
            continue
        if len(s) < 40 and buf and len(buf) > 2:
            blocks.append("\n".join(buf))
            buf = [s]
        else:
            buf.append(s)
    if buf:
        blocks.append("\n".join(buf))

    drafts = []
    for i, b in enumerate(blocks[:max_items], 1):
        title = b.splitlines()[0][:80]
        drafts.append(
            {
                "id": f"ev_upload_{i:03d}",
                "title": title,
                "body": b,
                "skills": [],
                "tags": ["upload"],
            }
        )
    if not drafts and text.strip():
        drafts.append(
            {
                "id": "ev_upload_001",
                "title": "Uploaded resume",
                "body": text[:4000],
                "skills": [],
                "tags": ["upload"],
            }
        )
    return drafts
