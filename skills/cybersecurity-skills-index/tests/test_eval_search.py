import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
EVAL = SKILL_DIR / "scripts" / "eval_search.py"


class EvalSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.index = root / "index.jsonl"
        self.golden = root / "golden.jsonl"
        records = [
            {
                "name": "triaging-security-alerts-in-splunk",
                "frontmatter_name": "triaging-security-alerts-in-splunk",
                "title": "Triaging Security Alerts in Splunk",
                "description": "Triages Splunk incident triage alerts in Splunk Enterprise Security by investigating notable events.",
            },
            {
                "name": "analyzing-security-logs-with-splunk",
                "frontmatter_name": "analyzing-security-logs-with-splunk",
                "title": "Analyzing Security Logs with Splunk",
                "description": "Analyzes Splunk security logs during incident investigations.",
            },
            {
                "name": "building-incident-response-playbook",
                "frontmatter_name": "building-incident-response-playbook",
                "title": "Building Incident Response Playbooks",
                "description": "Designs structured incident response playbooks for security teams.",
            },
        ]
        self.index.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

    def run_eval(self, golden_records, *extra):
        self.golden.write_text(
            "".join(json.dumps(record) + "\n" for record in golden_records),
            encoding="utf-8",
        )
        return subprocess.run(
            [
                "python3",
                str(EVAL),
                "--index-path",
                str(self.index),
                "--golden",
                str(self.golden),
                "--limit",
                "3",
                *extra,
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_eval_passes_matching_golden_query(self):
        proc = self.run_eval(
            [
                {
                    "id": "soc/splunk-alert-triage",
                    "category": "soc-siem",
                    "query": "splunk incident triage",
                    "top_k": 3,
                    "expected_top1": ["triaging-security-alerts-in-splunk"],
                    "expected_topk": [],
                    "acceptable_topk": [],
                    "must_not_topk": [],
                    "expect_empty": False,
                }
            ]
        )

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("top1", proc.stdout)
        self.assertIn("failures=0", proc.stdout)

    def test_eval_fails_when_expected_top1_is_missing(self):
        proc = self.run_eval(
            [
                {
                    "id": "soc/wrong",
                    "category": "soc-siem",
                    "query": "splunk incident triage",
                    "top_k": 3,
                    "expected_top1": ["building-incident-response-playbook"],
                    "expected_topk": [],
                    "acceptable_topk": [],
                    "must_not_topk": [],
                    "expect_empty": False,
                }
            ],
            "--strict",
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("soc/wrong", proc.stdout)
        self.assertIn("expected top1", proc.stdout)

    def test_strict_eval_fails_when_filter_matches_no_cases(self):
        proc = self.run_eval(
            [
                {
                    "id": "soc/splunk-alert-triage",
                    "category": "soc-siem",
                    "query": "splunk incident triage",
                    "top_k": 3,
                    "expected_top1": ["triaging-security-alerts-in-splunk"],
                    "expected_topk": [],
                    "acceptable_topk": [],
                    "must_not_topk": [],
                    "expect_empty": False,
                }
            ],
            "--category",
            "missing-category",
            "--strict",
        )

        self.assertEqual(proc.returncode, 1)
        self.assertIn("no eval cases matched", proc.stdout)

    def test_acceptable_topk_can_satisfy_expected_topk_alternative(self):
        proc = self.run_eval(
            [
                {
                    "id": "soc/acceptable-alternative",
                    "category": "soc-siem",
                    "query": "splunk incident triage",
                    "top_k": 3,
                    "expected_top1": ["triaging-security-alerts-in-splunk"],
                    "expected_topk": ["nonexistent-preferred-skill"],
                    "acceptable_topk": ["analyzing-security-logs-with-splunk"],
                    "must_not_topk": [],
                    "expect_empty": False,
                }
            ],
            "--strict",
        )

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("failures=0", proc.stdout)


if __name__ == "__main__":
    unittest.main()
