# Plans Directory

This directory contains all development plans managed by the Claude orchestration system.

## Directory Structure

```
plans/
├── README.md              # This file
├── masterplan.md          # Strategic project roadmap (created by /new-project)
├── phase*_*.ready.md      # Phase plans derived from Master Plan
├── *.ready.md             # Other plans ready for implementation
├── *.in_progress.md       # Plans currently being implemented
├── *.paused.md            # Plans with paused work sessions
├── paused_work.*.md       # Session context files (created by /pause-work)
├── completed/             # Successfully completed plans
│   └── *.md
├── old/                   # Deprecated or superseded plans
│   └── *.md
└── archived/              # Historical plans (kept for reference)
    └── *.md
```

## Master Plan

The **Master Plan** (`masterplan.md`) is a special document that serves as the strategic source of truth:

- Created by `/new-project` command
- Defines project vision, goals, and implementation roadmap
- Contains phases that are decomposed into individual phase plans
- Living document updated as the project progresses

### Master Plan → Phase Plans

```
masterplan.md (Strategic Overview)
    │
    ├──→ phase1_foundation.ready.md
    ├──→ phase2_core_features.ready.md
    └──→ phase3_polish.ready.md
```

Phase plans are created by the feature-architect based on Master Plan phases.

## Plan Lifecycle

```
                    ┌──────────────────────────┐
                    │                          │
                    v                          │
[NEW] ──> .ready.md ──> .in_progress.md ──> .paused.md
              │               │                  │
              │               v                  │
              │        completed/*.md <──────────┘
              │               │
              │               v
              └─────────> old/*.md
```

## File Naming Conventions

### Feature Plans
```
add_user_authentication.ready.md
implement_dark_mode.in_progress.md
refactor_api_layer.paused.md
```

### Bug Plans
```
bug_memory_leak_in_parser.ready.md
bug_null_pointer_on_startup.in_progress.md
```

### Session Context Files
```
paused_work.2025-01-15_1430.md
paused_work.2025-01-16_0900.md
```

## Status Meanings

| Status | File Pattern | Meaning |
|--------|--------------|---------|
| **Ready** | `*.ready.md` | Plan complete, awaiting implementation |
| **In Progress** | `*.in_progress.md` | Currently being implemented |
| **Paused** | `*.paused.md` | Work paused, context saved |
| **Completed** | `completed/*.md` | Successfully implemented |
| **Old** | `old/*.md` | Deprecated or superseded |
| **Archived** | `archived/*.md` | Historical reference |

## Working with Plans

### Initialize a Project
Use `/new-project` to create the Master Plan and phase plans for a new or existing project.

### Create a New Plan
Use `/new-feature` or `/fix-bug` commands, or invoke the `feature-architect` or `root-cause-analyzer` agents directly.

### Start/Resume Work
Use `/start-work` command to find and resume paused work or start a ready plan.

### Pause Work
Use `/pause-work` command to save context and pause current work.

### Audit Plans
Use `/document` command to validate, clean up, and sync plans with actual progress.

## Plan Template

New plans should follow this structure:

```markdown
# [Plan Type]: [Name]

## Overview
[Brief description]

## Requirements
- [ ] [Requirement 1]
- [ ] [Requirement 2]

## Implementation Plan

### Phase 1: [Name]
[Details]

### Phase 2: [Name]
[Details]

## Success Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

---
**Status**: ready
**Created**: [timestamp]
**Author**: [agent name]
```

## Maintenance

- Run `/document` periodically to clean up stale plans
- Move completed plans to `completed/` promptly
- Move abandoned plans to `old/` with a note explaining why
- Delete pause files after successful resume

## Notes

- All plan status changes are logged in `Development_Progress.md`
- Plans in `completed/` serve as documentation of what was built
- Plans in `old/` may contain useful context for future reference
