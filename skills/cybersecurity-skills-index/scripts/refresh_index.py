#!/usr/bin/env python3
"""Build a compact JSONL index for the Anthropic Cybersecurity Skills archive."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_URL = "https://github.com/mukul975/Anthropic-Cybersecurity-Skills.git"
DEFAULT_REPO_DIR = Path(
    os.environ.get(
        "CYBER_SKILLS_REPO",
        "~/.agents/skill-archives/Anthropic-Cybersecurity-Skills",
    )
).expanduser()
DEFAULT_INDEX_PATH = (
    Path(__file__).resolve().parents[1] / "references" / "skills-index.jsonl"
)


def run(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip()
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{message}")
    return proc.stdout.strip()


def ensure_repo(repo_dir: Path, repo_url: str, update: bool) -> None:
    if not (repo_dir / ".git").exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", repo_url, str(repo_dir)])
        return
    if update:
        run(["git", "pull", "--ff-only"], cwd=repo_dir)


def repo_head(repo_dir: Path) -> str:
    return run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_dir)


BLOCK_SCALAR_RE = re.compile(r"^[>|](?:[0-9]+)?[+-]?$")


def clean_scalar(value: str) -> str:
    value = one_line(value)
    if BLOCK_SCALAR_RE.match(value):
        return ""
    return value.strip().strip('"').strip("'").strip()


def one_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_list_item(value: str) -> str:
    return clean_scalar(value.strip()[1:].strip())


def is_top_level_key(line: str) -> bool:
    return bool(line and not line.startswith((" ", "\t", "-")) and ":" in line)


def parse_block_scalar(lines: list[str], start: int, style: str) -> tuple[str, int]:
    collected: list[str] = []
    idx = start
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "---" or is_top_level_key(line):
            break
        collected.append(line.strip())
        idx += 1
    if style.startswith("|"):
        return one_line("\n".join(collected)), idx
    return one_line(" ".join(collected)), idx


def parse_frontmatter(text: str) -> dict[str, object]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter.append(line)

    data: dict[str, object] = {}
    idx = 0
    while idx < len(frontmatter):
        line = frontmatter[idx]
        if not line.strip() or not is_top_level_key(line):
            idx += 1
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        raw_value = value.strip()
        idx += 1

        if BLOCK_SCALAR_RE.match(raw_value):
            parsed, idx = parse_block_scalar(frontmatter, idx, raw_value)
            data[key] = clean_scalar(parsed)
            continue

        if not raw_value:
            items: list[str] = []
            while idx < len(frontmatter):
                next_line = frontmatter[idx]
                if next_line.strip() == "---" or is_top_level_key(next_line):
                    break
                if next_line.lstrip().startswith("-"):
                    item = parse_list_item(next_line.lstrip())
                    if item:
                        items.append(item)
                idx += 1
            data[key] = items
            continue

        parts = [raw_value]
        while idx < len(frontmatter):
            next_line = frontmatter[idx]
            if next_line.strip() == "---" or is_top_level_key(next_line) or next_line.lstrip().startswith("-"):
                break
            if next_line.strip():
                parts.append(next_line.strip())
            idx += 1
        data[key] = clean_scalar(" ".join(parts))

    for key, value in list(data.items()):
        if isinstance(value, str):
            data[key] = clean_scalar(value)
        elif isinstance(value, list):
            deduped: list[str] = []
            for item in value:
                if item and item not in deduped:
                    deduped.append(item)
            data[key] = deduped
    return data


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return one_line(line[2:])
    return ""


def list_value(data: dict[str, object], key: str) -> list[str]:
    value = data.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def string_value(data: dict[str, object], key: str) -> str:
    value = data.get(key, "")
    return value if isinstance(value, str) else ""


def scan_skills(repo_dir: Path, source_url: str, head: str) -> list[dict[str, str]]:
    skills_root = repo_dir / "skills"
    if not skills_root.exists():
        raise SystemExit(f"missing skills directory: {skills_root}")

    indexed_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, str]] = []

    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        name = skill_file.parent.name
        frontmatter_name = string_value(fm, "name")
        frameworks = {
            "nist_csf": list_value(fm, "nist_csf"),
            "mitre_attack": list_value(fm, "mitre_attack"),
            "d3fend_techniques": list_value(fm, "d3fend_techniques"),
            "mitre_f3": list_value(fm, "mitre_f3"),
            "nist_ai_rmf": list_value(fm, "nist_ai_rmf"),
            "atlas_techniques": list_value(fm, "atlas_techniques"),
        }
        records.append(
            {
                "name": name,
                "frontmatter_name": frontmatter_name,
                "description": string_value(fm, "description"),
                "title": first_heading(text) or frontmatter_name,
                "domain": string_value(fm, "domain"),
                "subdomain": string_value(fm, "subdomain"),
                "tags": list_value(fm, "tags"),
                "frameworks": frameworks,
                "relative_path": str(skill_file.relative_to(repo_dir)),
                "source": "mukul975/Anthropic-Cybersecurity-Skills",
                "source_url": source_url,
                "repo_head": head,
                "indexed_at": indexed_at,
            }
        )

    return records


def write_index(records: list[dict[str, str]], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--repo-url", default=REPO_URL)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--update", action="store_true", help="pull latest repo changes")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    repo_dir = args.repo_dir.expanduser()
    index_path = args.index_path.expanduser()

    ensure_repo(repo_dir, args.repo_url, args.update)
    head = repo_head(repo_dir)
    records = scan_skills(repo_dir, args.repo_url, head)
    write_index(records, index_path)

    if not args.quiet:
        print(f"Indexed {len(records)} skills from {repo_dir} @ {head}")
        print(f"Wrote {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
