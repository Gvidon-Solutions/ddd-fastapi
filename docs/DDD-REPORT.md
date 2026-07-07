# DDD Report

Generated from the repository-local skills in `.agents/skills/`:

- `ddd-architecture`
- `ddd-jobs`
- `ddd-presentation`
- `ddd-review`
- `ddd-testing`

Date: 2026-07-07

## Verification

Commands run:

```bash
uv run ruff check backend tools
uv run ty check backend/app
uv run pytest backend/tests
uv run python tools/ddd_linter.py
```

Results:

- `ruff`: passed.
- `ty`: passed.
- `pytest`: passed, `178 passed in 3.14s`.
- `ddd_linter`: passed.

## Current State

The repository now passes the executable DDD policy in `tools/ddd_linter.py`.

The linter policy was adjusted to match the repository skills more precisely:

- existing test files must live under a known layer and keep layer-oriented
  placement;
- the linter no longer requires empty mirrored tests for every source file;
- infrastructure dataclasses are allowed for infrastructure DTO/helper output;
- usecase port dataclasses are allowed for external capability DTOs;
- event files may contain exactly one `*Payload` value object and exactly one
  event class when the event class has `payload: ThatPayload`;
- frozen value objects whose names end with `Error` are not treated as
  exceptions unless they inherit from an exception type.

## Fixes Applied

### Domain Placement

- Moved `Initiator` into `job/base/value_objects/initiator.py` so the file name
  matches the primary value object.
- Moved `JobEventPayload` into `job/base/value_objects/job_event_payload.py`
  because event payloads are values, not entities.
- Kept `JobEvent` in `job/base/entities/job_event.py`.
- Moved `JobExecutionRecord` into
  `job/base/value_objects/job_execution_record.py`.

### Usecase Outputs

- Moved `FindItemsResult` from the item usecase module into the item domain
  value objects.
- Moved `FindUsersResult` from the user usecase module into the user domain
  value objects.
- Avoided entity/value object import cycles with `TYPE_CHECKING`.

### Exceptions

- Moved `CodexExecFailedError` into
  `domain/job/codex_run_job_use_case/exceptions/`.
- Exported the new domain exception from the codex run job domain package.

### Tests

- Renamed `backend/tests/infrastructure/arq/test_job_queue.py` to
  `backend/tests/infrastructure/arq/test_job_runtime.py`, matching the runtime
  adapter it actually tests.

### Skills

- `ddd-review`, `ddd-jobs`, and `ddd-architecture` now document the event
  payload/event pair exception explicitly.
- `.agents/skills/` remains the canonical skill location.
- `.codex/skills/` remains symlink-only.

## Remaining Architectural Notes

The current linter intentionally checks enforceable conventions without
creating busywork. It does not claim every source file must have a dedicated
test file. New tests should still follow the `ddd-testing` skill: their path
must make the target layer and behavior obvious.

Future linter improvements can add stricter checks for:

- usecase input/output domain-only signatures;
- `@job_worker` annotation rules;
- generic job lifecycle mutation outside worker/repository/cancel flow;
- presentation imports of infrastructure helpers that should become use cases;
- AAA phase comments in tests.
