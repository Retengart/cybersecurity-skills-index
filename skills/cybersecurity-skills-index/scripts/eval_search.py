#!/usr/bin/env python3
"""Evaluate cybersecurity skill search against golden queries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import search_skills  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise SystemExit(f"missing file: {path}")
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return records


def load_index(index_path: Path) -> list[dict[str, str]]:
    return load_jsonl(index_path)  # type: ignore[return-value]


def names(results: list[tuple[float, dict[str, str]]]) -> list[str]:
    return [record["name"] for _, record in results]


def as_list(case: dict[str, object], key: str) -> list[str]:
    value = case.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value:
        return [value]
    return []


def check_case(
    case: dict[str, object],
    records: list[dict[str, str]],
    default_limit: int,
) -> tuple[bool, list[str], list[str]]:
    query = str(case.get("query", "")).strip()
    if not query:
        return False, [], ["missing query"]

    limit = int(case.get("limit", default_limit))
    top_k = int(case.get("top_k", limit))
    results = search_skills.search(records, query, limit)
    top_names = names(results)
    checked_names = top_names[:top_k]
    failures: list[str] = []

    if bool(case.get("expect_empty", False)):
        if top_names:
            failures.append(f"expected empty results, got {top_names[:top_k]}")
        return not failures, top_names, failures

    expected_top1 = as_list(case, "expected_top1")
    if expected_top1 and (not top_names or top_names[0] not in expected_top1):
        failures.append(f"expected top1 one of {expected_top1}, got {top_names[:1]}")

    for expected in as_list(case, "expected_topk"):
        acceptable = as_list(case, "acceptable_topk")
        has_acceptable = any(name in checked_names for name in acceptable)
        if expected not in checked_names and not has_acceptable:
            failures.append(f"expected top{k_label(top_k)} to include {expected}, got {checked_names}")

    for forbidden in as_list(case, "must_not_topk"):
        if forbidden in checked_names:
            failures.append(f"must not include {forbidden} in top{k_label(top_k)}, got {checked_names}")

    return not failures, top_names, failures


def k_label(top_k: int) -> str:
    return str(top_k)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-path", type=Path, default=search_skills.DEFAULT_INDEX_PATH)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--category")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--include-xfail", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    records = load_index(args.index_path.expanduser())
    cases = load_jsonl(args.golden.expanduser())
    if args.category:
        cases = [case for case in cases if case.get("category") == args.category]
    if not args.include_xfail:
        cases = [case for case in cases if not case.get("xfail", False)]

    if not cases:
        print("no eval cases matched")
        return 1 if args.strict else 0

    failures: list[dict[str, object]] = []
    top1_pass = 0
    hit_at_k_pass = 0

    for case in cases:
        ok, top_names, case_failures = check_case(case, records, args.limit)
        expected_top1 = as_list(case, "expected_top1")
        expected_topk = as_list(case, "expected_topk")
        if expected_top1 and top_names[:1] and top_names[0] in expected_top1:
            top1_pass += 1
        checked = top_names[: int(case.get("top_k", args.limit))]
        acceptable_topk = as_list(case, "acceptable_topk")
        topk_ok = (
            not expected_topk
            or all(name in checked for name in expected_topk)
            or any(name in checked for name in acceptable_topk)
        )
        if ok and topk_ok:
            hit_at_k_pass += 1
        if not ok:
            failures.append(
                {
                    "id": case.get("id", "<unknown>"),
                    "query": case.get("query", ""),
                    "actual": top_names[: int(case.get("top_k", args.limit))],
                    "failures": case_failures,
                }
            )

    summary = {
        "cases": len(cases),
        "top1": top1_pass,
        "hit_at_k": hit_at_k_pass,
        "failures": len(failures),
    }

    if args.json:
        print(json.dumps({"summary": summary, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        print(
            f"cases={summary['cases']} top1={summary['top1']}/{summary['cases']} "
            f"hit@k={summary['hit_at_k']}/{summary['cases']} failures={summary['failures']}"
        )
        for failure in failures:
            print(f"\n{failure['id']}: {failure['query']}")
            for item in failure["failures"]:  # type: ignore[index]
                print(f"  - {item}")
            print(f"  actual: {failure['actual']}")

    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
