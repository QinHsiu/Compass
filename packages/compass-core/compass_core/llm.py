"""OpenAI-compatible multi-provider LLM client with offline fallback."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


PROVIDERS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "ollama": "http://127.0.0.1:11434/v1",
}


@dataclass
class LLMConfig:
    provider: str
    base_url: str
    api_key: str
    model: str

    @property
    def available(self) -> bool:
        if self.provider == "ollama":
            return True
        return bool(self.api_key)


def load_config(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> LLMConfig:
    prov = (provider or os.environ.get("COMPASS_LLM_PROVIDER") or "openai").lower()
    default_base = PROVIDERS.get(prov, PROVIDERS["openai"])
    base = base_url or os.environ.get("OPENAI_BASE_URL") or default_base
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("COMPASS_API_KEY") or ""
    default_model = {
        "openai": "gpt-4o-mini",
        "deepseek": "deepseek-chat",
        "ollama": "llama3.2",
    }.get(prov, "gpt-4o-mini")
    mdl = model or os.environ.get("COMPASS_MODEL") or default_model
    return LLMConfig(provider=prov, base_url=base.rstrip("/"), api_key=key, model=mdl)


def chat(
    messages: list[dict],
    *,
    config: LLMConfig | None = None,
    temperature: float = 0.4,
    timeout: int = 60,
) -> dict:
    """
    Return {text, used_llm, provider, model, error}.
    Falls back to empty text + error when unavailable.
    """
    cfg = config or load_config()
    if not cfg.available and cfg.provider != "ollama":
        return {
            "text": "",
            "used_llm": False,
            "provider": cfg.provider,
            "model": cfg.model,
            "error": "no API key; set OPENAI_API_KEY or use COMPASS_LLM_PROVIDER=ollama",
        }

    url = f"{cfg.base_url}/chat/completions"
    payload = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        return {
            "text": text,
            "used_llm": True,
            "provider": cfg.provider,
            "model": cfg.model,
            "error": "",
        }
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        return {
            "text": "",
            "used_llm": False,
            "provider": cfg.provider,
            "model": cfg.model,
            "error": f"HTTP {e.code}: {detail}",
        }
    except Exception as e:
        return {
            "text": "",
            "used_llm": False,
            "provider": cfg.provider,
            "model": cfg.model,
            "error": str(e),
        }


def describe_config(config: LLMConfig | None = None) -> dict:
    cfg = config or load_config()
    return {
        "provider": cfg.provider,
        "base_url": cfg.base_url,
        "model": cfg.model,
        "has_key": bool(cfg.api_key),
        "available": cfg.available or cfg.provider == "ollama",
    }
