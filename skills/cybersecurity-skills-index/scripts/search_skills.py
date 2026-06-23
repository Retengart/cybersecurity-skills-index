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


def load_records(index_path: Path, repo_dir: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if not index_path.exists():
        refresh(index_path, repo_dir, update=False)
    with index_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def refresh(index_path: Path, repo_dir: Path, update: bool) -> None:
    cmd = [
        sys.executable,
        str(REFRESH_SCRIPT),
        "--index-path",
        str(index_path),
        "--repo-dir",
        str(repo_dir),
        "--quiet",
    ]
    if update:
        cmd.append("--update")
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip()
        raise SystemExit(f"index refresh failed\n{message}")


def add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def score_with_explanation(record: dict[str, str], query: str) -> tuple[float, dict[str, object]]:
    query_norm = normalized(query)
    query_tokens = tokenize(query)
    name = record.get("name", "")
    frontmatter_name = record.get("frontmatter_name", "")
    title = record.get("title", "")
    description = record.get("description", "")
    reasons: list[str] = []
    matched_tokens: set[str] = set()

    name_norm = normalized(name)
    frontmatter_name_norm = normalized(frontmatter_name)
    title_norm = normalized(title)
    desc_norm = normalized(description)
    haystack = f"{name_norm} {frontmatter_name_norm} {title_norm} {desc_norm}"

    value = 0.0
    if query_norm and query_norm == name_norm:
        value += 200.0
        add_reason(reasons, "full query matched skill name")
    if query_norm and query_norm in {frontmatter_name_norm, title_norm}:
        value += 160.0
        add_reason(reasons, "full query matched title")
    if query_norm and query_norm in haystack:
        value += 50.0
        add_reason(reasons, "full query phrase matched indexed text")
    if query_norm and query_norm in name_norm:
        value += 80.0
        add_reason(reasons, "query phrase matched skill name")

    name_tokens = set(tokenize(name))
    title_tokens = set(tokenize(f"{frontmatter_name} {title}"))
    desc_tokens = set(tokenize(description))

    for token in query_tokens:
        if token in name_tokens:
            value += 14.0
            matched_tokens.add(token)
            add_reason(reasons, f"{token} matched name")
        if token in title_tokens:
            value += 8.0
            matched_tokens.add(token)
            add_reason(reasons, f"{token} matched title")
        if token in desc_tokens:
            value += 4.0
            matched_tokens.add(token)
            add_reason(reasons, f"{token} matched description")
        if any(part.startswith(token) or token.startswith(part) for part in name_tokens):
            value += 3.0
            matched_tokens.add(token)
            add_reason(reasons, f"{token} prefix-matched name")
        if token in haystack:
            value += 1.0
            matched_tokens.add(token)

    explanation = {
        "matched_tokens": sorted(matched_tokens),
        "unmatched_tokens": [token for token in query_tokens if token not in matched_tokens],
        "why": reasons[:8],
    }
    return value, explanation


def score(record: dict[str, str], query: str) -> float:
    return score_with_explanation(record, query)[0]


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


def build_result(
    rank: int,
    value: float,
    record: dict[str, str],
    query: str,
    repo_dir: Path,
    explain: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "rank": rank,
        "score": value,
        **record,
        "path": str(record_path(record, repo_dir)),
    }
    if explain:
        _, explanation = score_with_explanation(record, query)
        result["explanation"] = explanation
        result["why"] = explanation["why"]
    return result


def print_why(result: dict[str, object]) -> None:
    why = result.get("why")
    if isinstance(why, list) and why:
        print(f"   why: {'; '.join(str(item) for item in why[:5])}")


def print_text(
    results: list[tuple[float, dict[str, str]]],
    total: int,
    query: str,
    repo_dir: Path,
    explain: bool = False,
) -> None:
    if not results:
        print(f"No matching skills found for: {query}")
        print(f"Indexed skills: {total}")
        return

    print(f"Matches for: {query}")
    print(f"Indexed skills: {total}")
    for idx, (value, record) in enumerate(results, start=1):
        result = build_result(idx, value, record, query, repo_dir, explain)
        desc = record.get("description", "")
        if len(desc) > 260:
            desc = desc[:257].rstrip() + "..."
        print(f"\n{idx}. {record['name']}  score={value:.1f}")
        display = record.get("title") or record.get("frontmatter_name")
        if display and normalized(display) != normalized(record["name"]):
            print(f"   title: {display}")
        if desc:
            print(f"   {desc}")
        if explain:
            print_why(result)
        print(f"   path: {record_path(record, repo_dir)}")
        print(f"   read: python3 {Path(__file__)} --read {record['name']}")


def print_compact(
    results: list[tuple[float, dict[str, str]]],
    query: str,
    repo_dir: Path,
    explain: bool,
) -> None:
    for idx, (value, record) in enumerate(results, start=1):
        fields = [
            str(idx),
            f"{value:.1f}",
            record["name"],
            record.get("title") or record.get("frontmatter_name") or "",
            record.get("relative_path") or str(record_path(record, repo_dir)),
        ]
        if explain:
            result = build_result(idx, value, record, query, repo_dir, True)
            why = result.get("why", [])
            fields.append("why=" + "; ".join(str(item) for item in why[:5]))
        print("\t".join(fields))


def print_jsonl(
    results: list[tuple[float, dict[str, str]]],
    total: int,
    query: str,
    repo_dir: Path,
    limit: int,
    explain: bool,
) -> None:
    print(
        json.dumps(
            {
                "type": "meta",
                "schema": "cyber-skills.search.v1",
                "query": query,
                "indexed_skills": total,
                "limit": limit,
                "result_count": len(results),
            },
            ensure_ascii=False,
        )
    )
    for idx, (value, record) in enumerate(results, start=1):
        result = build_result(idx, value, record, query, repo_dir, explain)
        result["type"] = "match"
        result["schema"] = "cyber-skills.search-result.v1"
        print(json.dumps(result, ensure_ascii=False))


def read_top(
    results: list[tuple[float, dict[str, str]]],
    query: str,
    repo_dir: Path,
    count: int,
) -> int:
    count = max(1, min(count, 3))
    selected = results[:count]
    print("# cyber-skills read-top v1")
    print(f"query: {query}")
    print(f"count: {len(selected)}")
    for idx, (value, record) in enumerate(selected, start=1):
        path = record_path(record, repo_dir)
        print()
        print(
            f"===== BEGIN SKILL rank={idx} score={value:.1f} "
            f"name={record['name']} path={path} ====="
        )
        print(path.read_text(encoding="utf-8", errors="replace").rstrip())
        print(f"===== END SKILL name={record['name']} =====")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="*", help="search terms")
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--refresh", action="store_true", help="pull latest archive and rebuild index")
    parser.add_argument("--read", metavar="SKILL_NAME", help="print one archived skill by exact name")
    parser.add_argument("--json", action="store_true", help="emit JSON results")
    parser.add_argument("--jsonl", action="store_true", help="emit newline-delimited JSON results")
    parser.add_argument("--compact", action="store_true", help="emit one terse line per result")
    parser.add_argument("--why", "--explain", dest="explain", action="store_true", help="include lexical ranking signals")
    parser.add_argument("--read-top", nargs="?", const=1, type=int, metavar="N", help="read the top N matching skills, capped at 3")
    parser.add_argument("--fail-on-empty", action="store_true", help="exit 1 when a search has no matches")
    args = parser.parse_args()

    index_path = args.index_path.expanduser()
    repo_dir = args.repo_dir.expanduser()
    if args.refresh:
        refresh(index_path, repo_dir, update=True)

    records = load_records(index_path, repo_dir)
    if args.read:
        return read_skill(records, args.read, repo_dir)

    query = " ".join(args.query).strip()
    if not query:
        parser.error("provide a query or --read SKILL_NAME")

    results = search(records, query, args.limit)
    if args.fail_on_empty and not results:
        print_text(results, len(records), query, repo_dir, args.explain)
        return 1
    if args.read_top is not None:
        return read_top(results, query, repo_dir, args.read_top)
    if args.jsonl:
        print_jsonl(results, len(records), query, repo_dir, args.limit, args.explain)
    elif args.json:
        payload = [
            build_result(idx, value, record, query, repo_dir, args.explain)
            for idx, (value, record) in enumerate(results, start=1)
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.compact:
        print_compact(results, query, repo_dir, args.explain)
    else:
        print_text(results, len(records), query, repo_dir, args.explain)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
