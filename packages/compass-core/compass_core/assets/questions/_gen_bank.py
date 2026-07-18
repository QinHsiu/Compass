"""Generate curated question bank once."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bank.jsonl"

H5BP = "https://github.com/h5bp/Front-end-Developer-Interview-Questions"
TIH = "https://github.com/yangshun/tech-interview-handbook"
AW = "https://github.com/DopplerHQ/awesome-interview-questions"

rows: list[dict] = []


def add(qid: str, topic: str, tags: list[str], q: str, difficulty: str, source: str, url: str = "") -> None:
    rows.append(
        {
            "id": qid,
            "topic": topic,
            "tags": tags,
            "q": q,
            "difficulty": difficulty,
            "source": source,
            "source_url": url,
        }
    )


def bulk(prefix: str, topic: str, items: list[tuple[str, list[str], str]], source: str, url: str) -> None:
    for i, (q, tags, d) in enumerate(items, 1):
        add(f"{prefix}_{i:03d}", topic, tags + [topic], q, d, source, url)


bulk(
    "qb_py",
    "python",
    [
        ("What is the GIL and how does it affect CPU-bound threads?", ["gil", "concurrency"], "mid"),
        ("Explain list vs tuple vs set use-cases and complexity.", ["data-structures"], "junior"),
        ("How do you profile a slow Python service in production?", ["profiling", "performance"], "mid"),
        ("Difference between multiprocessing, threading, and asyncio?", ["asyncio", "concurrency"], "mid"),
        ("How does Python's garbage collector work (ref count + generational)?", ["gc", "memory"], "senior"),
        ("Explain decorators and a real production use case.", ["decorators"], "mid"),
        ("How do you manage virtualenvs and dependency pinning for deploy?", ["packaging"], "junior"),
        ("What are context managers and why use them for resources?", ["contextmanager"], "junior"),
        ("Explain duck typing vs static typing with type hints.", ["typing"], "mid"),
        ("How would you design retries/backoff for flaky HTTP clients?", ["reliability", "http"], "mid"),
        ("Describe CPython vs PyPy trade-offs.", ["runtime"], "senior"),
        ("How do you serialize large objects efficiently (pickle vs msgpack vs json)?", ["serialization"], "mid"),
        ("Explain MRO and diamond inheritance pitfalls.", ["oop"], "senior"),
        ("How do you catch and structure exceptions in APIs?", ["errors"], "junior"),
        ("What is a generator and when does it beat lists for memory?", ["generators"], "mid"),
        ("Explain __slots__ and memory impact.", ["memory"], "senior"),
        ("How do you test async code?", ["testing", "asyncio"], "mid"),
        ("Describe packaging a CLI with entry points.", ["packaging", "cli"], "junior"),
        ("How do you handle secrets in Python services?", ["security"], "mid"),
        ("Explain GIL release in I/O-bound C extensions.", ["gil", "c-api"], "senior"),
    ],
    "Compass curated (python commons)",
    AW,
)

bulk(
    "qb_java",
    "java",
    [
        ("Explain JVM memory areas and a typical OOM investigation path.", ["jvm", "memory"], "senior"),
        ("HashMap vs ConcurrentHashMap internals and use cases.", ["collections", "concurrency"], "mid"),
        ("How does Spring Boot auto-configuration work at a high level?", ["spring"], "mid"),
        ("Transactional boundaries: REQUIRED vs REQUIRES_NEW pitfalls.", ["transactions", "spring"], "senior"),
        ("Explain GC algorithms you would choose for low-latency services.", ["gc"], "senior"),
        ("How do you design idempotent REST APIs?", ["rest", "reliability"], "mid"),
        ("Kafka consumer group rebalance: what goes wrong and how to mitigate?", ["kafka"], "senior"),
        ("JPA N+1 problem: detection and fixes.", ["jpa", "sql"], "mid"),
        ("Checked vs unchecked exceptions — API design guidance.", ["errors"], "junior"),
        ("Explain thread pools and rejection policies.", ["concurrency"], "mid"),
        ("How do you version APIs without breaking clients?", ["api"], "mid"),
        ("Docker multi-stage builds for Java services — why?", ["docker"], "junior"),
        ("Explain CAP trade-offs for a session store.", ["distributed"], "senior"),
        ("How do you secure Spring endpoints (authn/authz)?", ["security", "spring"], "mid"),
        ("Describe circuit breaker vs bulkhead patterns.", ["resilience"], "senior"),
    ],
    "Compass curated (java/backend commons)",
    AW,
)

bulk(
    "qb_fe",
    "frontend",
    [
        ("Explain event delegation and when you would use it.", ["javascript", "dom"], "junior"),
        ("How does the browser rendering pipeline work (layout/paint/composite)?", ["performance", "browser"], "mid"),
        ("What is the difference between == and ===?", ["javascript"], "junior"),
        ("Explain CSS specificity and cascade conflicts.", ["css"], "junior"),
        ("How do you prevent XSS in a React/Vue app?", ["security", "frontend"], "mid"),
        ("Describe critical rendering path optimizations.", ["performance"], "senior"),
        ("What are Web Vitals and how do you improve LCP?", ["performance"], "mid"),
        ("Explain closures with a practical UI example.", ["javascript"], "junior"),
        ("How does CORS work and how do you debug it?", ["network", "security"], "mid"),
        ("Difference between localStorage, sessionStorage, and cookies?", ["browser"], "junior"),
        ("Explain flexbox vs grid for responsive layouts.", ["css"], "junior"),
        ("How do you structure state in a large SPA?", ["architecture", "frontend"], "senior"),
        ("What is a service worker good for — and bad for?", ["pwa"], "mid"),
        ("Explain accessibility: ARIA roles you actually use.", ["a11y"], "mid"),
        ("How do you test frontend regressions effectively?", ["testing"], "mid"),
    ],
    "Adapted category from h5bp Front-end Interview Questions",
    H5BP,
)

bulk(
    "qb_sd",
    "system-design",
    [
        ("Design a URL shortener: APIs, storage, and scale bottlenecks.", ["system-design"], "mid"),
        ("Design a rate limiter for a public API.", ["system-design", "reliability"], "mid"),
        ("Design a news feed: fan-out strategies.", ["system-design"], "senior"),
        ("How would you design a feature store online path?", ["mlops", "system-design"], "senior"),
        ("Design job scheduling on Kubernetes for bursty batch work.", ["kubernetes", "system-design"], "senior"),
        ("Design an observability stack for microservices.", ["observability", "system-design"], "mid"),
        ("Design a multi-tenant SaaS isolation model.", ["system-design", "security"], "senior"),
        ("Design chat message delivery with at-least-once semantics.", ["system-design"], "mid"),
    ],
    "Compass curated (aligned with tech-interview-handbook topics)",
    TIH,
)

bulk(
    "qb_beh",
    "behavioral",
    [
        ("Tell me about a time you disagreed with a technical decision.", ["behavioral", "conflict"], "mid"),
        ("Describe a production incident you owned end-to-end.", ["behavioral", "ownership"], "mid"),
        ("How do you prioritize when everything is P0?", ["behavioral"], "mid"),
        ("Tell me about mentoring or raising the engineering bar.", ["behavioral", "leadership"], "senior"),
        ("Describe a failure and what you changed afterward.", ["behavioral"], "junior"),
        ("How do you communicate bad news to stakeholders?", ["behavioral"], "mid"),
    ],
    "Compass curated (behavioral; TIH-aligned)",
    TIH,
)

bulk(
    "qb_ml",
    "mlops",
    [
        ("Explain train/serving skew and how you detect it.", ["mlops", "ml"], "mid"),
        ("How do you version datasets and models in production?", ["mlops"], "mid"),
        ("Feature store: online vs offline consistency challenges.", ["feature-store", "mlops"], "senior"),
        ("How do you evaluate RAG systems beyond accuracy?", ["rag", "llm"], "mid"),
        ("Explain data leakage in time-series ML.", ["ml", "data"], "mid"),
        ("Kubernetes for model serving: autoscaling signals you trust.", ["kubernetes", "mlops"], "senior"),
        ("How do you roll back a bad model safely?", ["mlops", "reliability"], "mid"),
        ("Prompt injection risks and mitigations for LLM apps.", ["llm", "security"], "mid"),
        ("Spark job skew: symptoms and remedies.", ["spark", "data"], "mid"),
        ("Explain batch vs streaming feature pipelines.", ["data", "mlops"], "mid"),
        ("How do you monitor drift in production models?", ["mlops", "monitoring"], "senior"),
        ("Vector DB choice criteria for RAG.", ["rag", "vector-db"], "mid"),
    ],
    "Compass curated (ml/mlops commons)",
    AW,
)

bulk(
    "qb_ops",
    "devops",
    [
        ("Explain blue/green vs canary deployments.", ["devops"], "mid"),
        ("How do you debug CrashLoopBackOff in Kubernetes?", ["kubernetes"], "mid"),
        ("What SLOs would you set for an API gateway?", ["sre"], "mid"),
        ("Infrastructure as code: Terraform state pitfalls.", ["iac"], "mid"),
        ("How do you secure CI/CD supply chain?", ["security", "ci"], "senior"),
        ("Explain HPA metrics selection for a web service.", ["kubernetes"], "mid"),
        ("Linux: how do you diagnose high iowait?", ["linux"], "mid"),
        ("Redis: eviction policies and cache stampedes.", ["redis"], "mid"),
    ],
    "Compass curated (devops/sre commons)",
    AW,
)

bulk(
    "qb_algo",
    "algorithms",
    [
        ("Explain time/space of hash map operations and collision strategies.", ["algorithms"], "junior"),
        ("When is BFS preferable to DFS?", ["algorithms", "graphs"], "junior"),
        ("How do you detect a cycle in a linked list?", ["algorithms"], "junior"),
        ("Explain CAP and PACELC briefly.", ["distributed"], "mid"),
        ("Write SQL to find duplicate emails efficiently.", ["sql"], "junior"),
        ("Explain window functions with a ranking example.", ["sql"], "mid"),
        ("Normalize vs denormalize for analytics tables.", ["sql", "data"], "mid"),
        ("Describe ACID and a real isolation anomaly.", ["databases"], "mid"),
    ],
    "Compass curated (algorithms/sql commons)",
    TIH,
)

bulk(
    "qb_x",
    "polyglot",
    [
        ("Go: channels vs mutexes — when each?", ["go", "concurrency"], "mid"),
        ("Go: escape analysis and heap allocations.", ["go", "performance"], "senior"),
        ("Node.js event loop phases — what blocks them?", ["nodejs"], "mid"),
        ("Explain NestJS/Express middleware ordering bugs.", ["nodejs"], "mid"),
        ("C++: rule of five and move semantics basics.", ["cpp"], "mid"),
        ("Explain zero-copy networking concepts at a high level.", ["networking"], "senior"),
    ],
    "Compass curated (polyglot commons)",
    AW,
)

if __name__ == "__main__":
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} -> {OUT}")
