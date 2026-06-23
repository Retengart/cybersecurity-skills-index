# Cybersecurity Skills Index

Single index skill for the large [`mukul975/Anthropic-Cybersecurity-Skills`](https://github.com/mukul975/Anthropic-Cybersecurity-Skills) archive.

It keeps only one visible skill in an agent context, then searches a local JSONL index and tells the agent which specific archived `SKILL.md` files to read.

## Install

```bash
npx skills add <owner>/cybersecurity-skills-index --skill cybersecurity-skills-index -g
```

For a local checkout:

```bash
npx skills add . --skill cybersecurity-skills-index -g
```

## Use

Refresh the upstream archive and rebuild the local index:

```bash
python3 skills/cybersecurity-skills-index/scripts/refresh_index.py --update
```

Search:

```bash
python3 skills/cybersecurity-skills-index/scripts/search_skills.py "splunk incident triage"
```

Print one archived skill:

```bash
python3 skills/cybersecurity-skills-index/scripts/search_skills.py --read triaging-security-incident
```

The scripts use only the Python standard library. `uv run python ...` also works.

## What Is Committed

This repo commits the wrapper skill and scripts. It does not commit the generated `skills-index.jsonl` cache or the cloned upstream archive. The index is rebuilt locally from the upstream Apache-2.0 repository.

## Attribution

This wrapper indexes the community project `mukul975/Anthropic-Cybersecurity-Skills`, which is licensed under Apache-2.0. This wrapper is not affiliated with Anthropic PBC or the upstream project.
