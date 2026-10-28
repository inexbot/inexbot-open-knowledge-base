#!/usr/bin/env python3
"""Ad-hoc keyword retrieval against the local inexbot-open KB index.

Used when the proxy injection isn't enough (proxy only injects top-3 summary
results from each KB; this script returns more detail, including full md content).

NOTE: index.json is a DICT mapping URL path -> {title, description, path,
content_snippet}, NOT a list of docs. Earlier versions of this script assumed
a list and crashed with `AttributeError: 'str' object has no attribute 'get'`.

Usage:
    python3 scripts/retrieve.py "keyword1 keyword2 ..." [top_n]
"""
import json
import sys
from pathlib import Path

IDX_ROOT = Path.home() / ".hermes/kb/inexbot-open"
IDX_FILE = IDX_ROOT / "index.json"
MD_ROOT = IDX_ROOT / "md"


def load_index() -> dict[str, dict]:
    if not IDX_FILE.exists():
        sys.exit(f"index.json not found at {IDX_FILE}; run crawler.py first")
    data = json.loads(IDX_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit(
            f"unexpected index.json shape: {type(data).__name__} "
            "(expected dict mapping path -> doc)"
        )
    return data


def score(doc: dict, terms: list[str]) -> int:
    haystack_parts: list[str] = []
    title = doc.get("title", "")
    desc = doc.get("description", "")
    body = doc.get("content_snippet", "")
    if title:
        haystack_parts.append(title * 4)
    if desc:
        haystack_parts.append(desc * 2)
    if body:
        haystack_parts.append(body)
    haystack = " ".join(haystack_parts).lower()
    return sum(haystack.count(t.lower()) for t in terms)


def find_md(path: str) -> Path | None:
    rel = path.lstrip("/").replace("/", "-")
    if not rel:
        return None
    candidates = [MD_ROOT / rel, MD_ROOT / f"{rel}.md"]
    for prefix in ("zh-", "en-", "kr-"):
        candidates.append(MD_ROOT / f"{prefix}{rel}")
        candidates.append(MD_ROOT / f"{prefix}{rel}.md")
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: retrieve.py \"<keywords>\" [top_n]")
    terms = sys.argv[1].split()
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    index = load_index()
    scored: list[tuple[int, str, dict]] = []
    for path, doc in index.items():
        if not isinstance(doc, dict):
            continue
        s = score(doc, terms)
        if s > 0:
            scored.append((s, path, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    for s, path, doc in scored[:top_n]:
        print(f"=== {s}  {path}")
        if doc.get("title"):
            print(f"title: {doc['title']}")
        if doc.get("description"):
            print(f"desc:  {doc['description']}")
        print()
    for s, path, _doc in scored[:top_n]:
        md_path = find_md(path)
        if md_path is None:
            continue
        print(f"\n--- {md_path.name} ---")
        print(md_path.read_text(encoding="utf-8", errors="ignore")[:8000])


if __name__ == "__main__":
    main()