#!/usr/bin/env python3
"""Search the compact cybersecurity skills index."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
REFRESH_SCRIPT = SKILL_DIR / "scripts" / "refresh_index.py"
DEFAULT_INDEX_PATH = SKILL_DIR / "references" / "skills-index.jsonl"
DEFAULT_REPO_DIR = Path(
    os.environ.get(
        "CYBER_SKILLS_REPO",
        "~/.agents/skill-archives/Anthropic-Cybersecurity-Skills",
    )
).expanduser()


TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def normalized(text: str) -> str:
    return " ".join(tokenize(text))


def load_records(index_path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if not index_path.exists():
        refresh(index_path, update=False)
    with index_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def refresh(index_path: Path, update: bool) -> None:
    cmd = [sys.executable, str(REFRESH_SCRIPT), "--index-path", str(index_path), "--quiet"]
    if update:
        cmd.append("--update")
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip()
        raise SystemExit(f"index refresh failed\n{message}")


def score(record: dict[str, str], query: str) -> float:
    query_norm = normalized(query)
    query_tokens = tokenize(query)
    name = record.get("name", "")
    frontmatter_name = record.get("frontmatter_name", "")
    title = record.get("title", "")
    description = record.get("description", "")

    name_norm = normalized(name)
    frontmatter_name_norm = normalized(frontmatter_name)
    title_norm = normalized(title)
    desc_norm = normalized(description)
    haystack = f"{name_norm} {frontmatter_name_norm} {title_norm} {desc_norm}"

    value = 0.0
    if query_norm and query_norm in haystack:
        value += 50.0
    if query_norm and query_norm in name_norm:
        value += 80.0

    name_tokens = set(tokenize(name))
    title_tokens = set(tokenize(f"{frontmatter_name} {title}"))
    desc_tokens = set(tokenize(description))

    for token in query_tokens:
        if token in name_tokens:
            value += 14.0
        if token in title_tokens:
            value += 8.0
        if token in desc_tokens:
            value += 4.0
        if any(part.startswith(token) or token.startswith(part) for part in name_tokens):
            value += 3.0
        if token in haystack:
            value += 1.0

    return value


def search(records: list[dict[str, str]], query: str, limit: int) -> list[tuple[float, dict[str, str]]]:
    ranked = [(score(record, query), record) for record in records]
    ranked.sort(key=lambda item: (-item[0], item[1].get("name", "")))
    return [item for item in ranked[:limit] if item[0] > 0]


def record_path(record: dict[str, str], repo_dir: Path) -> Path:
    if record.get("relative_path"):
        return repo_dir / record["relative_path"]
    if record.get("path"):
        return Path(record["path"])
    raise SystemExit(f"record has no path fields: {record.get('name', '<unknown>')}")


def read_skill(records: list[dict[str, str]], name: str, repo_dir: Path) -> int:
    for record in records:
        if record.get("name") == name:
            path = record_path(record, repo_dir)
            print(path.read_text(encoding="utf-8", errors="replace"))
            return 0
    matches = [record["name"] for record in records if name.lower() in record["name"].lower()]
    if matches:
        print("No exact match. Did you mean:")
        for match in matches[:20]:
            print(f"  {match}")
    else:
        print(f"No skill found: {name}", file=sys.stderr)
    return 1


def print_text(
    results: list[tuple[float, dict[str, str]]],
    total: int,
    query: str,
    repo_dir: Path,
) -> None:
    if not results:
        print(f"No matching skills found for: {query}")
        print(f"Indexed skills: {total}")
        return

    print(f"Matches for: {query}")
    print(f"Indexed skills: {total}")
    for idx, (value, record) in enumerate(results, start=1):
        desc = record.get("description", "")
        if len(desc) > 260:
            desc = desc[:257].rstrip() + "..."
        print(f"\n{idx}. {record['name']}  score={value:.1f}")
        display = record.get("title") or record.get("frontmatter_name")
        if display and normalized(display) != normalized(record["name"]):
            print(f"   title: {display}")
        if desc:
            print(f"   {desc}")
        print(f"   path: {record_path(record, repo_dir)}")
        print(f"   read: python3 {Path(__file__)} --read {record['name']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="*", help="search terms")
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--refresh", action="store_true", help="pull latest archive and rebuild index")
    parser.add_argument("--read", metavar="SKILL_NAME", help="print one archived skill by exact name")
    parser.add_argument("--json", action="store_true", help="emit JSON results")
    args = parser.parse_args()

    index_path = args.index_path.expanduser()
    repo_dir = args.repo_dir.expanduser()
    if args.refresh:
        refresh(index_path, update=True)

    records = load_records(index_path)
    if args.read:
        return read_skill(records, args.read, repo_dir)

    query = " ".join(args.query).strip()
    if not query:
        parser.error("provide a query or --read SKILL_NAME")

    results = search(records, query, args.limit)
    if args.json:
        print(json.dumps([{"score": value, **record} for value, record in results], ensure_ascii=False, indent=2))
    else:
        print_text(results, len(records), query, repo_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
