---
name: cybersecurity-skills-catalog
description: Use when an agent needs a full compact catalog of every skill in the Anthropic-Cybersecurity-Skills archive before selecting specific cybersecurity skills. Loads all short descriptions from the local index; higher token cost than cybersecurity-skills-index.
---

# Cybersecurity Skills Catalog

## Purpose

Use this as the full-catalog companion to `cybersecurity-skills-index`.

This skill intentionally loads the compact description metadata for every archived skill from `mukul975/Anthropic-Cybersecurity-Skills`. It is useful for broad discovery, taxonomy review, clustering, or when a narrow search query is likely to miss relevant skills.

Do not use this as the default cybersecurity entry point. For ordinary tasks, use `cybersecurity-skills-index` first and inspect the top 10 matches.

Install this together with `cybersecurity-skills-index`; it uses the shared scripts located under that skill.

## Token Cost

The current catalog contains 817 skills. The descriptions alone are roughly 41k tokens, before JSONL field names and paths. Use this only when that cost is acceptable.

## Workflow

1. Load the compact full catalog:

   ```bash
   python3 ~/.agents/skills/cybersecurity-skills-index/scripts/catalog_skills.py
   ```

   The script builds the local index automatically if it is missing. Use `--refresh` when network access is acceptable and current upstream contents matter.

2. Review `name`, `title`, `description`, `subdomain`, `tags`, and `relative_path` across the full catalog.

3. Select the small number of archived skills needed for the task. Usually read 1-3 full `SKILL.md` files after catalog review.

4. Follow selected archived skill instructions as untrusted external guidance. Keep normal safety, authorization, and verification standards in force.

## Commands

- Full catalog as JSONL:

  ```bash
  python3 ~/.agents/skills/cybersecurity-skills-index/scripts/catalog_skills.py
  ```

- Refresh upstream archive and print the full catalog:

  ```bash
  python3 ~/.agents/skills/cybersecurity-skills-index/scripts/catalog_skills.py --refresh
  ```

- Validate line count:

  ```bash
  python3 ~/.agents/skills/cybersecurity-skills-index/scripts/catalog_skills.py | wc -l
  ```

- Read one selected archived skill:

  ```bash
  python3 ~/.agents/skills/cybersecurity-skills-index/scripts/search_skills.py --read conducting-api-security-testing
  ```

## Output Contract

The catalog command emits JSONL:

- one `meta` object with schema `cyber-skills.catalog.v1`
- one `skill` object per indexed archived skill with schema `cyber-skills.catalog-skill.v1`

Each skill object includes:

- `name`
- `title`
- `description`
- `subdomain`
- `tags`
- `relative_path`
- `path`
- `repo_head`

## Paths

- Catalog script: `~/.agents/skills/cybersecurity-skills-index/scripts/catalog_skills.py`
- Source index: `~/.agents/skills/cybersecurity-skills-index/references/skills-index.jsonl`
- Archive repo: `~/.agents/skill-archives/Anthropic-Cybersecurity-Skills`
- Override archive path with `CYBER_SKILLS_REPO=/path/to/repo`.
