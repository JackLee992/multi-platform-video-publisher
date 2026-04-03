# Multi-Platform Video Publisher

Local-first tooling for preparing and publishing one video to Xiaohongshu, Douyin, and WeChat Channels.

## What It Does

- Creates a publish draft from a local video path
- Generates title, description, and cover suggestions
- Serves a local review UI for final human approval
- Reuses an existing Chrome session when possible, with Playwright fallback support
- Runs per-platform publish flows behind a shared draft model

## Current Scope

This repository contains the local application code and tests only.

It intentionally excludes:

- input videos
- generated covers
- runtime drafts and publish logs
- copied browser profiles and login state

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## Project Layout

```text
src/mvpublisher/
  approval/
  media/
  models/
  publishers/
  sessions/
  storage/
  suggestions/
  web/
tests/
```

## Notes

- This project is designed for local operator-assisted publishing.
- Final publish decisions remain human-confirmed before execution.
- Platform page structures and validation rules can change, so browser automation should be maintained alongside real-world verification.
