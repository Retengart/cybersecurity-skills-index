#!/usr/bin/env python3
"""Emit the full compact cybersecurity skills catalog from the local index."""

from __future__ import annotations

import argparse
import json
import os
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


def load_records(index_path: Path, repo_dir: Path, update: bool) -> list[dict[str, object]]:
    if update or not index_path.exists():
        refresh(index_path, repo_dir, update)
    if not index_path.exists():
        raise SystemExit(f"missing index: {index_path}")
    records: list[dict[str, object]] = []
    with index_path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{index_path}:{lineno}: invalid JSON: {exc}") from exc
    return records


def record_path(record: dict[str, object], repo_dir: Path) -> str:
    relative_path = record.get("relative_path")
    if isinstance(relative_path, str) and relative_path:
        return str(repo_dir / relative_path)
    path = record.get("path")
    return path if isinstance(path, str) else ""


def catalog_record(rank: int, record: dict[str, object], repo_dir: Path) -> dict[str, object]:
    return {
        "type": "skill",
        "schema": "cyber-skills.catalog-skill.v1",
        "rank": rank,
        "name": record.get("name", ""),
        "title": record.get("title") or record.get("frontmatter_name") or "",
        "description": record.get("description", ""),
        "subdomain": record.get("subdomain", ""),
        "tags": record.get("tags", []),
        "relative_path": record.get("relative_path", ""),
        "path": record_path(record, repo_dir),
        "repo_head": record.get("repo_head", ""),
    }


def emit_jsonl(records: list[dict[str, object]], repo_dir: Path) -> None:
    repo_heads = sorted({str(record.get("repo_head", "")) for record in records if record.get("repo_head")})
    print(
        json.dumps(
            {
                "type": "meta",
                "schema": "cyber-skills.catalog.v1",
                "skill_count": len(records),
                "repo_heads": repo_heads,
            },
            ensure_ascii=False,
        )
    )
    for rank, record in enumerate(records, start=1):
        print(json.dumps(catalog_record(rank, record, repo_dir), ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--refresh", action="store_true", help="pull latest archive and rebuild index before emitting catalog")
    args = parser.parse_args()

    index_path = args.index_path.expanduser()
    repo_dir = args.repo_dir.expanduser()
    records = load_records(index_path, repo_dir, args.refresh)
    emit_jsonl(records, repo_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
