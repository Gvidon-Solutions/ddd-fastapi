---
name: skills-ddd-review
description: Use when reviewing backend DDD correctness, checking layer boundaries, validating entity/value object/repository placement, auditing job architecture, or running the repository's deterministic DDD linter.
---

# DDD Review Skill

Use before finalizing backend architectural changes and whenever the user asks
for review.

## Review Order

1. Restate touched layers.
2. Check domain ownership: entity vs value object vs repository port vs usecase
   port.
3. Check dependency direction.
4. Check file granularity: one primary entity/value object/exception per file.
5. Check tests mirror source paths.
6. Run deterministic checks:

```bash
uv run ruff check backend
uv run ty check backend/app
uv run pytest backend/tests
uv run python tools/ddd_linter.py
```

## DDD Linter

`tools/ddd_linter.py` checks:

- forbidden layer imports;
- dataclasses outside approved domain/test locations;
- multiple entity/value object dataclasses in one file;
- exceptions outside exception modules;
- exception files and exports;
- repository ports outside domain;
- repository implementations inside domain;
- missing mirrored tests.

The linter is intentionally strict. If it fails on existing debt, report the
violations and separate them from regressions introduced by the current change.

## Output Format For Reviews

Findings first, ordered by severity. Each finding must include:

- file path;
- rule violated;
- why it matters;
- concrete fix.

Then include verification commands and residual risk.
