import json
import tempfile
import unittest
from pathlib import Path

import sys

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import refresh_index  # noqa: E402


class FrontmatterParsingTests(unittest.TestCase):
    def test_folded_block_description_drops_yaml_marker(self):
        text = """---
name: sample-skill
description: >-
  First line of the description
  continues on the next line.
tags:
- aws
- cloudtrail
mitre_attack:
- T1078.004
---

# Sample Skill
"""

        parsed = refresh_index.parse_frontmatter(text)

        self.assertEqual(
            parsed["description"],
            "First line of the description continues on the next line.",
        )
        self.assertEqual(parsed["tags"], ["aws", "cloudtrail"])
        self.assertEqual(parsed["mitre_attack"], ["T1078.004"])

    def test_plain_multiline_description_stays_one_line(self):
        text = """---
name: sample-skill
description: Analyze Azure activity logs for suspicious operations,
  privilege escalation, and persistence attempts.
domain: cybersecurity
subdomain: security-operations
---
# Sample Skill
"""

        parsed = refresh_index.parse_frontmatter(text)

        self.assertEqual(
            parsed["description"],
            "Analyze Azure activity logs for suspicious operations, privilege escalation, and persistence attempts.",
        )
        self.assertIn("domain", parsed)
        self.assertIn("subdomain", parsed)
        self.assertEqual(parsed.get("domain"), "cybersecurity")
        self.assertEqual(parsed.get("subdomain"), "security-operations")

    def test_scan_skills_preserves_list_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            skill_dir = repo / "skills" / "sample-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                """---
name: sample-skill
description: >-
  Search CloudTrail logs for suspicious IAM activity.
domain: cybersecurity
subdomain: cloud-security
tags:
- aws
- cloudtrail
nist_csf:
- DE.CM-01
mitre_attack:
- T1078.004
---

# Sample Skill
""",
                encoding="utf-8",
            )

            records = refresh_index.scan_skills(repo, "https://example.invalid/repo.git", "abc123")

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["description"], "Search CloudTrail logs for suspicious IAM activity.")
        self.assertEqual(record["domain"], "cybersecurity")
        self.assertEqual(record["subdomain"], "cloud-security")
        self.assertEqual(record["tags"], ["aws", "cloudtrail"])
        self.assertEqual(record["frameworks"]["nist_csf"], ["DE.CM-01"])
        self.assertEqual(record["frameworks"]["mitre_attack"], ["T1078.004"])
        json.dumps(record)


if __name__ == "__main__":
    unittest.main()
