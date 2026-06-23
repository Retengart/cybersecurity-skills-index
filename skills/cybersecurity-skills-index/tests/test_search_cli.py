import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SEARCH = SKILL_DIR / "scripts" / "search_skills.py"


class SearchCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "archive"
        self.index = self.root / "index.jsonl"
        skill_root = self.repo / "skills"
        self._write_skill(
            skill_root,
            "triaging-security-alerts-in-splunk",
            "Triaging Security Alerts in Splunk",
            "Triages Splunk incident triage alerts in Splunk Enterprise Security by investigating notable events.",
        )
        self._write_skill(
            skill_root,
            "building-incident-response-playbook",
            "Building Incident Response Playbooks",
            "Designs structured incident response playbooks for security teams.",
        )
        self._write_skill(
            skill_root,
            "analyzing-security-logs-with-splunk",
            "Analyzing Security Logs with Splunk",
            "Analyzes Splunk security logs during incident investigations.",
        )
        records = [
            {
                "name": "triaging-security-alerts-in-splunk",
                "frontmatter_name": "triaging-security-alerts-in-splunk",
                "title": "Triaging Security Alerts in Splunk",
                "description": "Triages Splunk incident triage alerts in Splunk Enterprise Security by investigating notable events.",
                "relative_path": "skills/triaging-security-alerts-in-splunk/SKILL.md",
                "repo_head": "fixture",
            },
            {
                "name": "building-incident-response-playbook",
                "frontmatter_name": "building-incident-response-playbook",
                "title": "Building Incident Response Playbooks",
                "description": "Designs structured incident response playbooks for security teams.",
                "relative_path": "skills/building-incident-response-playbook/SKILL.md",
                "repo_head": "fixture",
            },
            {
                "name": "analyzing-security-logs-with-splunk",
                "frontmatter_name": "analyzing-security-logs-with-splunk",
                "title": "Analyzing Security Logs with Splunk",
                "description": "Analyzes Splunk security logs during incident investigations.",
                "relative_path": "skills/analyzing-security-logs-with-splunk/SKILL.md",
                "repo_head": "fixture",
            },
        ]
        self.index.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

    def _write_skill(self, skill_root, name, title, description):
        path = skill_root / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(
            f"""---
name: {name}
description: {description}
---

# {title}

## When to Use

- Fixture skill.
""",
            encoding="utf-8",
        )

    def run_cli(self, *args):
        return subprocess.run(
            [
                "python3",
                str(SEARCH),
                "--index-path",
                str(self.index),
                "--repo-dir",
                str(self.repo),
                *args,
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_jsonl_emits_meta_and_match_objects(self):
        proc = self.run_cli("--jsonl", "--why", "--limit", "1", "splunk incident triage")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(lines[0]["type"], "meta")
        self.assertEqual(lines[0]["schema"], "cyber-skills.search.v1")
        self.assertEqual(lines[1]["type"], "match")
        self.assertEqual(lines[1]["rank"], 1)
        self.assertEqual(lines[1]["name"], "triaging-security-alerts-in-splunk")
        self.assertIn("why", lines[1])

    def test_jsonl_limit_10_returns_descriptions_for_agent_selection(self):
        records = []
        for idx in range(12):
            name = f"agent-selection-skill-{idx:02d}"
            records.append(
                {
                    "name": name,
                    "frontmatter_name": name,
                    "title": f"Agent Selection Skill {idx:02d}",
                    "description": f"agentselectionterm relevant description {idx:02d}",
                    "relative_path": f"skills/{name}/SKILL.md",
                    "repo_head": "fixture",
                }
            )
        self.index.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

        proc = self.run_cli("--jsonl", "--why", "--limit", "10", "agentselectionterm")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        matches = [line for line in lines if line["type"] == "match"]
        self.assertEqual(lines[0]["result_count"], 10)
        self.assertEqual(len(matches), 10)
        self.assertTrue(all(match.get("description") for match in matches))

    def test_compact_output_is_one_line_per_match(self):
        proc = self.run_cli("--compact", "--why", "--limit", "1", "splunk incident triage")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn("\ttriaging-security-alerts-in-splunk\t", lines[0])
        self.assertIn("why=", lines[0])

    def test_read_top_prints_delimited_skill_bodies(self):
        proc = self.run_cli("--read-top", "1", "splunk incident triage")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("# cyber-skills read-top v1", proc.stdout)
        self.assertIn("===== BEGIN SKILL rank=1", proc.stdout)
        self.assertIn("# Triaging Security Alerts in Splunk", proc.stdout)
        self.assertIn("===== END SKILL name=triaging-security-alerts-in-splunk", proc.stdout)

    def test_fail_on_empty_exits_nonzero(self):
        proc = self.run_cli("--fail-on-empty", "quasar violin marmalade")

        self.assertEqual(proc.returncode, 1)
        self.assertIn("No matching skills found", proc.stdout)

    def test_missing_index_bootstrap_uses_repo_dir(self):
        custom_repo = self.root / "custom-archive"
        self._write_skill(
            custom_repo / "skills",
            "custom-bootstrap-skill",
            "Custom Bootstrap Skill",
            "Routes a uniquebootstrapterm query to the custom archive.",
        )
        subprocess.run(["git", "init"], cwd=custom_repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "add", "."], cwd=custom_repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-m",
                "fixture",
            ],
            cwd=custom_repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        missing_index = self.root / "missing-index.jsonl"

        proc = subprocess.run(
            [
                "python3",
                str(SEARCH),
                "--index-path",
                str(missing_index),
                "--repo-dir",
                str(custom_repo),
                "--compact",
                "uniquebootstrapterm",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("custom-bootstrap-skill", proc.stdout)


if __name__ == "__main__":
    unittest.main()
