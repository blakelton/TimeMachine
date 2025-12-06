# TimeMachine Project - Claude Instructions

This file provides project-specific guidance for Claude Code when working on the TimeMachine Observation Chamber project.

## Project Overview

TimeMachine is a temperature-controlled observation chamber management system for Raspberry Pi 3+. It provides web-based control for camera management (CSI and USB), recording, timelapse creation, and future temperature control.

**Tech Stack:**
- Backend: Python 3.11, FastAPI, SQLAlchemy, GStreamer
- Frontend: React 18+, TypeScript, Vite, TanStack Query
- Database: SQLite with WAL mode
- Deployment: systemd, nginx

---

## Git Branching Strategy

### Branch Structure

```
main                    # Production-ready code only
└── develop             # Integration branch for features
    ├── feature/xxx     # Feature development branches
    ├── fix/xxx         # Bug fix branches
    └── chore/xxx       # Maintenance/infrastructure branches
```

### Branch Rules

| Branch | Purpose | Merges From | Merges To |
|--------|---------|-------------|-----------|
| `main` | Stable releases | `develop` (via PR) | - |
| `develop` | Integration/staging | `feature/*`, `fix/*`, `chore/*` | `main` |
| `feature/*` | New features | `develop` | `develop` |
| `fix/*` | Bug fixes | `develop` | `develop` |
| `chore/*` | Maintenance tasks | `develop` | `develop` |

### Workflow

1. **Starting New Work:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/feature-name
   ```

2. **During Development:**
   - Commit frequently with descriptive messages
   - Keep feature branches focused and small
   - Rebase on develop if it has moved ahead

3. **Completing Work:**
   ```bash
   git checkout develop
   git pull origin develop
   git merge feature/feature-name
   git push origin develop
   git branch -d feature/feature-name
   git push origin --delete feature/feature-name
   ```

4. **Releasing to Main:**
   - Create PR from `develop` to `main`
   - Ensure all tests pass
   - Get approval before merging

### Branch Naming Conventions

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New functionality | `feature/camera-discovery` |
| `fix/` | Bug fixes | `fix/memory-leak-preview` |
| `chore/` | Maintenance, refactoring | `chore/update-dependencies` |
| `docs/` | Documentation only | `docs/api-reference` |

### Commit Message Format

```
work_type(scope): description

[optional body]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

**Work Types:**
- `feat`: New features
- `fix`: Bug fixes
- `chore`: Maintenance tasks
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Adding/updating tests

**Examples:**
```
feat(camera): add CSI camera discovery via libcamera
fix(storage): prevent path traversal in file serving
chore(deps): update FastAPI to 0.104.1
docs(api): add OpenAPI descriptions to endpoints
```

---

## Development Plans

All development plans are located in `.claude/plans/`:

| File | Description |
|------|-------------|
| `00-master-plan.ready.md` | Master plan with integrated task order |
| `00-gap-remediation.ready.md` | Detailed gap fix implementations |
| `01-10-*.ready.md` | Individual sub-plans |
| `GAP_ANALYSIS_REPORT.md` | Gap analysis findings |

### Plan Lifecycle

1. `.ready.md` - Plan complete, ready for implementation
2. `.in_progress.md` - Currently being implemented
3. Move to `.claude/plans/completed/` when done

---

## Code Quality Standards

### Python (Backend)
- Use `ruff` for linting
- Use `black` for formatting
- Type hints required (mypy strict)
- Cyclomatic complexity < 10
- Test coverage > 70%

### TypeScript (Frontend)
- ESLint + Prettier
- Strict TypeScript mode
- Component tests with Vitest
- E2E tests with Playwright

---

## Key Constraints (Raspberry Pi 3)

- **Memory**: Max 700MB available (systemd limit: 800MB)
- **H.264 Encoder**: Single encoder, one recording at a time
- **SD Card**: Use WAL mode, recommend USB for media storage
- **USB Bandwidth**: Shared between cameras and ethernet

---

## Current Status

**Branch**: `develop`
**Phase**: Pre-implementation (plans complete)
**Next**: Begin Phase 1 - Backend Foundation
