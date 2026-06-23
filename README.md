# Cybersecurity Skills Index

Two compact skills for the large [`mukul975/Anthropic-Cybersecurity-Skills`](https://github.com/mukul975/Anthropic-Cybersecurity-Skills) archive.

- `cybersecurity-skills-index`: default entry point. Searches the local index, shows the 10 closest skill descriptions, then tells the agent which specific archived `SKILL.md` files to read.
- `cybersecurity-skills-catalog`: full-catalog companion. Loads compact metadata for every archived skill when broad discovery is worth the token cost.

## Install

Install both skills:

```bash
npx skills add Retengart/cybersecurity-skills-index -g
```

Install only the search index skill:

```bash
npx skills add Retengart/cybersecurity-skills-index --skill cybersecurity-skills-index -g
```

Do not install `cybersecurity-skills-catalog` by itself. It is a companion skill that uses the shared scripts shipped with `cybersecurity-skills-index`; install both skills with the first command when you need the catalog.

For a local checkout:

```bash
npx skills add . -g
```

## Use

Refresh the upstream archive and rebuild the local index:

```bash
python3 skills/cybersecurity-skills-index/scripts/refresh_index.py --update
```

Search:

```bash
python3 skills/cybersecurity-skills-index/scripts/search_skills.py --jsonl --why --limit 10 "splunk incident triage"
```

Print the full compact catalog:

```bash
python3 skills/cybersecurity-skills-index/scripts/catalog_skills.py
```

Print one archived skill:

```bash
python3 skills/cybersecurity-skills-index/scripts/search_skills.py --read triaging-security-incident
```

The scripts use only the Python standard library. `uv run python ...` also works.

## What Is Committed

This repo commits the wrapper skills, scripts, tests, and small golden query file. It does not commit the generated `skills-index.jsonl` cache, local install lock files, or the cloned upstream archive. The index is rebuilt locally from the upstream Apache-2.0 repository.

## Attribution

This wrapper indexes the community project `mukul975/Anthropic-Cybersecurity-Skills`, which is licensed under Apache-2.0. This wrapper is not affiliated with Anthropic PBC or the upstream project.
