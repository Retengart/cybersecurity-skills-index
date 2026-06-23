import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
CATALOG = SKILL_DIR / "scripts" / "catalog_skills.py"


class CatalogCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "archive"
        self.index = self.root / "index.jsonl"
        records = []
        for idx in range(3):
            name = f"catalog-skill-{idx}"
            records.append(
                {
                    "name": name,
                    "frontmatter_name": name,
                    "title": f"Catalog Skill {idx}",
                    "description": f"Short description for catalog skill {idx}.",
                    "subdomain": "api-security",
                    "tags": ["api-security", f"tag-{idx}"],
                    "relative_path": f"skills/{name}/SKILL.md",
                    "repo_head": "fixture",
                }
            )
        self.index.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

    def test_catalog_jsonl_emits_all_skill_descriptions(self):
        proc = subprocess.run(
            [
                "python3",
                str(CATALOG),
                "--index-path",
                str(self.index),
                "--repo-dir",
                str(self.repo),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(lines[0]["type"], "meta")
        self.assertEqual(lines[0]["schema"], "cyber-skills.catalog.v1")
        self.assertEqual(lines[0]["skill_count"], 3)
        skills = [line for line in lines if line["type"] == "skill"]
        self.assertEqual(len(skills), 3)
        self.assertTrue(all(skill.get("description") for skill in skills))
        self.assertEqual(
            set(skills[0]),
            {
                "type",
                "schema",
                "rank",
                "name",
                "title",
                "description",
                "subdomain",
                "tags",
                "relative_path",
                "path",
                "repo_head",
            },
        )

    def test_missing_index_bootstrap_uses_repo_dir(self):
        custom_repo = self.root / "custom-archive"
        skill_dir = custom_repo / "skills" / "custom-catalog-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            """---
name: custom-catalog-skill
description: Custom catalog bootstrap description.
domain: cybersecurity
subdomain: api-security
tags:
- api-security
---

# Custom Catalog Skill
""",
            encoding="utf-8",
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
                str(CATALOG),
                "--index-path",
                str(missing_index),
                "--repo-dir",
                str(custom_repo),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(line) for line in proc.stdout.splitlines()]
        skills = [line for line in lines if line["type"] == "skill"]
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["name"], "custom-catalog-skill")


if __name__ == "__main__":
    unittest.main()
