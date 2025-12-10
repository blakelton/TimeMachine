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

## Development Environment (CRITICAL)

**⚠️ NEVER RUN SYSTEM DIAGNOSTIC COMMANDS ON THE DEVELOPMENT MACHINE ⚠️**

This project is developed on a **development workstation** but deployed to a **Raspberry Pi 3** target device.

### Development Rules:

1. **NO System Commands on Development Machine**:
   - NEVER run `sudo` commands on the development machine
   - NEVER run diagnostic commands like `v4l2-ctl`, `libcamera-hello`, etc. on dev machine
   - NEVER test hardware-specific features on dev machine

2. **Create Diagnostic Scripts Instead**:
   - When Pi-specific diagnostics are needed, create a script in `/scripts/` directory
   - User will deploy the script to Pi, run it, and provide results
   - Examples: `scripts/test-camera-discovery.sh`, `scripts/diagnose-camera-discovery.sh`

3. **Safe Commands on Development Machine**:
   - Git operations (status, add, commit, push, pull, etc.)
   - Code editing and file operations
   - Node/npm/python package management for development
   - Reading files and searching codebase

4. **Deployment Process**:
   - Code changes: Edit locally, commit to git
   - User runs `ssh timemachine.local ./projects/TimeMachine/scripts/install.sh` to deploy
   - Diagnostics: Create script → user deploys → user runs → user provides output

### Target Device Specifications:

- **Platform**: Raspberry Pi 3+
- **OS**: Debian-based Linux
- **Hardware**: CSI camera port, USB ports for cameras
- **Video Devices**: `/dev/video0-9` (cameras), `/dev/video10+` (codecs/ISP)
- **Service User**: `timemachine` (runs backend service)
- **Required Groups**: `video` group for camera access

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

Use a structured format with header lines followed by categorized details:

```
work_type(scope): short summary line 1
work_type(scope): short summary line 2
work_type(scope): short summary line 3

Category Name:
- Bullet point detail
- Another detail with context
- Specific implementation note

Another Category:
- Related changes grouped together
- Technical specifics

Breaking Changes (if any):
- What changed that affects existing behavior
- Migration steps if needed
```

**Work Types:**
- `feat`: New features or functionality
- `fix`: Bug fixes
- `chore`: Maintenance, dependencies, infrastructure
- `docs`: Documentation changes
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests

**Example:**
```
feat(camera): add CSI camera discovery via libcamera
feat(camera): add USB camera detection via V4L2
chore(deps): add picamera2 and opencv-python dependencies

Camera Discovery:
- Implemented CameraDiscovery class with async detection
- Added CSI camera detection using libcamera-hello
- Added USB camera enumeration via /dev/video* glob
- Created CameraInfo dataclass with capabilities

Dependencies:
- Added picamera2>=0.3.12 for CSI camera support
- Added opencv-python-headless for USB camera handling
- Pinned GStreamer bindings version
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
