"""Fetch recent LLM / Agent interview questions from public sources (compliance-safe)."""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

DEFAULT_UA = "CompassBot/0.2 (+personal study; LLM/Agent interview curation)"

# Public raw markdown sources (GitHub / docs) — no login walls
SOURCES = [
    {
        "id": "prompt_eng_faq",
        "url": "https://raw.githubusercontent.com/f/awesome-chatgpt-prompts/main/README.md",
        "topic": "llm",
        "note": "awesome-chatgpt-prompts README (prompt patterns → interview angles)",
    },
    {
        "id": "langchain_concepts",
        "url": "https://raw.githubusercontent.com/langchain-ai/langchain/master/README.md",
        "topic": "agent",
        "note": "LangChain README concepts",
    },
]


# High-signal curated LLM/Agent stems (always merged; crawl enriches)
SEED_LLM_AGENT = [
    ("Explain the difference between RAG and fine-tuning. When choose which?", ["rag", "finetune"], "llm", "mid"),
    ("How do you evaluate an LLM app beyond BLEU/ROUGE?", ["eval", "llm"], "llm", "mid"),
    ("What is prompt injection? Give mitigations for a tool-using agent.", ["security", "agent"], "agent", "mid"),
    ("Design a ReAct agent loop: plan, act, observe, stop conditions.", ["react", "agent"], "agent", "mid"),
    ("How does function calling / tool use work in modern LLM APIs?", ["tools", "agent"], "agent", "junior"),
    ("Explain context window limits and strategies (summarize, map-reduce, memory).", ["context", "memory"], "llm", "mid"),
    ("What is hallucination and how do you ground answers with citations?", ["hallucination", "rag"], "llm", "junior"),
    ("Compare vector DB ANN indexes (HNSW, IVF) for RAG retrieval.", ["vector", "rag"], "llm", "senior"),
    ("How do you build multi-agent collaboration without infinite loops?", ["multi-agent"], "agent", "senior"),
    ("Explain LoRA / QLoRA trade-offs vs full fine-tune.", ["lora", "finetune"], "llm", "mid"),
    ("Design an Agent memory: short-term scratchpad vs long-term store.", ["memory", "agent"], "agent", "mid"),
    ("How do you rate-limit and cost-control LLM chains in production?", ["cost", "ops"], "llm", "mid"),
    ("What is MCP and how does it relate to tool ecosystems?", ["mcp", "tools"], "agent", "mid"),
    ("Explain chunking strategies for RAG over code vs docs.", ["rag", "chunking"], "llm", "mid"),
    ("How do you guardrail an agent that can run shell commands?", ["security", "agent"], "agent", "senior"),
    ("Describe hybrid search (BM25 + dense) and reranking.", ["retrieval", "rag"], "llm", "mid"),
    ("What is speculative decoding / KV cache — why latency matters?", ["latency", "infra"], "llm", "senior"),
    ("Design evaluation for an Agent: task success, tool errors, human escalation.", ["eval", "agent"], "agent", "senior"),
    ("Explain structured output (JSON schema) reliability tricks.", ["structured", "llm"], "llm", "mid"),
    ("How do you debug a failing Agent trajectory from traces?", ["observability", "agent"], "agent", "mid"),
    ("Compare OpenAI Assistants / LangGraph / Autogen style orchestration.", ["orchestration", "agent"], "agent", "senior"),
    ("What is DPO / RLHF at a high level?", ["alignment"], "llm", "mid"),
    ("How do you prevent PII leakage through prompts and logs?", ["privacy", "security"], "llm", "mid"),
    ("Design a coding Agent that edits a repo safely (tests, diffs, rollback).", ["coding-agent"], "agent", "senior"),
    ("Explain embedding model choice and domain adaptation.", ["embedding", "rag"], "llm", "mid"),
    ("What is an Agent scratchpad vs chain-of-thought leakage risk?", ["cot", "security"], "agent", "mid"),
    ("How do you A/B test prompt or model changes in production?", ["eval", "ops"], "llm", "mid"),
    ("Describe planner-executor agent architecture.", ["planner", "agent"], "agent", "mid"),
    ("How does quantization (GPTQ/AWQ/GGUF) affect quality?", ["quantization"], "llm", "mid"),
    ("Interview: walk through building a research Agent with web tools.", ["research-agent"], "agent", "senior"),
]


def _fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _questions_from_markdown(md: str, topic: str, source_id: str, url: str) -> list[dict]:
    """Pull heading-like / bullet question lines from markdown."""
    out = []
    for ln in md.splitlines():
        s = ln.strip()
        if not s or len(s) < 20 or len(s) > 220:
            continue
        s = re.sub(r"^#+\s*", "", s)
        s = re.sub(r"^[-*•\d.]+\\s*", "", s)
        s = re.sub(r"^[-*•\d.]+\s*", "", s)
        if "?" in s or "？" in s or s.lower().startswith(("how ", "what ", "why ", "explain ", "design ")):
            tags = ["llm", "agent"] if topic == "agent" else ["llm"]
            # keyword boosts
            low = s.lower()
            for k in ("agent", "rag", "llm", "prompt", "tool", "embedding", "langchain", "memory"):
                if k in low and k not in tags:
                    tags.append(k)
            out.append(
                {
                    "id": f"qb_crawl_{source_id}_{len(out)+1:03d}",
                    "topic": topic,
                    "tags": tags,
                    "q": s[:240],
                    "difficulty": "mid",
                    "source": f"crawl:{source_id}",
                    "source_url": url,
                    "crawled_at": date.today().isoformat(),
                }
            )
        if len(out) >= 40:
            break
    return out


def seed_records() -> list[dict]:
    rows = []
    for i, (q, tags, topic, diff) in enumerate(SEED_LLM_AGENT, 1):
        rows.append(
            {
                "id": f"qb_llm_agent_{i:03d}",
                "topic": topic,
                "tags": tags + [topic, "llm", "agent"],
                "q": q,
                "difficulty": diff,
                "source": "Compass curated LLM/Agent 2026",
                "source_url": "",
                "crawled_at": date.today().isoformat(),
            }
        )
    return rows


def crawl_llm_agent_questions(limit_per_source: int = 40) -> list[dict]:
    rows = seed_records()
    for src in SOURCES:
        try:
            time.sleep(0.4)
            md = _fetch(src["url"])
            got = _questions_from_markdown(md, src["topic"], src["id"], src["url"])[:limit_per_source]
            rows.extend(got)
        except Exception as e:
            rows.append(
                {
                    "id": f"qb_crawl_err_{src['id']}",
                    "topic": "meta",
                    "tags": ["crawl-error"],
                    "q": f"[crawl skipped] {src['id']}: {e}",
                    "difficulty": "junior",
                    "source": "crawl-error",
                    "source_url": src["url"],
                    "crawled_at": date.today().isoformat(),
                }
            )
    # dedupe by question text
    seen = set()
    uniq = []
    for r in rows:
        key = re.sub(r"\s+", " ", (r.get("q") or "").lower())
        if key.startswith("[crawl skipped]"):
            continue
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def save_bank(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return path


def refresh_llm_agent_bank(assets_dir: Path | None = None) -> dict:
    """Write llm_agent.jsonl next to bank.jsonl and return stats."""
    base = assets_dir or Path(__file__).resolve().parent / "assets" / "questions"
    rows = crawl_llm_agent_questions()
    out = save_bank(rows, base / "llm_agent.jsonl")
    # also merge into a dated snapshot under collectors/
    snap = Path(__file__).resolve().parents[3] / "collectors" / "snapshots" / f"llm_agent_{date.today().isoformat()}.jsonl"
    try:
        save_bank(rows, snap)
    except Exception:
        pass
    return {"count": len(rows), "path": str(out), "topics": sorted({r["topic"] for r in rows})}
