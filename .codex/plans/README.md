# Codex Plan Workflow

Plans live here and track work for the Raspberry Pi Python webserver + USB cameras. Status is encoded in the filename suffix.

## File Naming and Status
- `<feature_or_bug>.ready.md` – plan/analysis is complete and ready to start.
- `<name>.in_progress.md` – implementation is underway.
- `<name>.paused.md` – work paused (paired with `paused_work.*.md` context files).
- `<name>.completed.md` – work finished and verified.
- `<name>.old.md` – deprecated/abandoned approach.
- `paused_work.YYYY-MM-DD_HH-MM-SS.md` – pause snapshots; archive as `paused_work.resumed.*.md` after resuming.

## Lifecycle
1. Architect/analyst creates `.ready.md`.
2. When coding begins, rename to `.in_progress.md`.
3. If pausing, follow `/pause-work` to create pause doc and rename plan to `.paused.md`.
4. On resume, `/start-work` renames back to `.in_progress.md` and loads next actions.
5. After implementation + quality gate, rename to `.completed.md`.
6. Superseded plans become `.old.md`.

## Feature Plan Template (summary)
```
# <Feature Name> - Plan (.ready)
## Context
- Goal, assumptions, success criteria

## Architecture Decisions
- Web/API, camera pipeline, storage, security/network, ops/reliability

## Phases & Tasks
- Phase 1: ...
  - [ ] Task...
  - Acceptance:
- Phase 2: ...

## Testing
- Automated + hardware-in-the-loop coverage

## Risks / Open Questions
```

## Bug Analysis Template (root-cause-analyzer output)
```
# <Bug Name> - Root Cause Analysis (.ready)
## Summary (symptom, environment, repro)
## Evidence (logs, camera state, resource observations)
## Findings (ranked with evidence)
## Recommended Fix Approach (steps, tests, mitigations)
```

## Quality Gate
- Every code change must be reviewed by `code-quality-evaluator`.
- CRITICAL issues block completion; iterate developer ↔ evaluator until clean.
