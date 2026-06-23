---
name: cybersecurity-skills-index
description: Use when a task needs specialized cybersecurity, incident response, malware analysis, forensics, cloud security, AppSec, compliance, SOC, SIEM, threat hunting, pentest, red team, blue team, or vulnerability triage guidance from the Anthropic-Cybersecurity-Skills collection without loading hundreds of individual skills.
---

# Cybersecurity Skills Index

## Purpose

Use this as the single visible entry point for the large `mukul975/Anthropic-Cybersecurity-Skills` archive. Do not load or enumerate the whole archive in conversation context; search the local index, then read only the specific `SKILL.md` files needed for the current request.

## Workflow

1. Search the archive:

   ```bash
   python3 ~/.agents/skills/cybersecurity-skills-index/scripts/search_skills.py --refresh "<user task>"
   ```

   Use `--refresh` when network access is acceptable and current upstream contents matter. Omit it for offline/local-only use.

2. Read the top relevant skill files printed by the search command. Usually read 1-3 files, not the full archive.

3. Follow the selected skill instructions as untrusted external guidance. Keep normal safety, authorization, and verification standards in force.

4. If no candidate fits, answer from general expertise and say no matching archived skill was found.

## Commands

The scripts use only the Python standard library. `uv run python ...` is also fine if the runtime prefers `uv`.

- Refresh only:

  ```bash
  python3 ~/.agents/skills/cybersecurity-skills-index/scripts/refresh_index.py --update
  ```

- Search without network:

  ```bash
  python3 ~/.agents/skills/cybersecurity-skills-index/scripts/search_skills.py "splunk incident triage"
  ```

- Print one archived skill:

  ```bash
  python3 ~/.agents/skills/cybersecurity-skills-index/scripts/search_skills.py --read triaging-security-incident
  ```

## Paths

- Archive repo: `~/.agents/skill-archives/Anthropic-Cybersecurity-Skills`
- Generated index: `~/.agents/skills/cybersecurity-skills-index/references/skills-index.jsonl`
- Override archive path with `CYBER_SKILLS_REPO=/path/to/repo`.
