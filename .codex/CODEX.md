# CODEX.md

Guidance for Codex when working in this repository. Use this as the primary instructions for Codex-driven workflows; `.claude/` exists only as reference.

## Project Overview
- Target: Raspberry Pi on a network, running a Python web server that interacts with two generic USB microscopes/cameras.
- Goals: Serve a web UI/API for preview/streaming/capture, basic device control, and data access over the LAN.
- Constraints: Limited CPU/memory and I/O on the Pi, USB camera throughput, and reliability of long-running services.

## Git Commit Policy
- **Never run `git commit` without explicit user approval.**
- Stage and draft commit messages only when asked; always show the proposed message before any commit action.

## Development and Ops Basics
- Python environment: Prefer a virtual env (`python -m venv .venv && source .venv/bin/activate`) and lock dependencies (`pip install -r requirements.txt` or `pip install -e .`).
- Run server locally (examples; adjust to the actual entrypoint): `uvicorn app.main:app --reload` or `flask run --host=0.0.0.0 --port=8000`.
- Tests: Default to `pytest` (or `npm test`/`make test` if a frontend exists). Ask the user if unsure.
- Lint/format: Prefer `ruff`, `black`, `isort`, `mypy` if configured. Do not add new dependencies without approval.
- Services: For Pi deployment, expect `systemd` units or `supervisor` configs for the web app and camera workers; keep configs under version control when possible.

## Plan and Work Session Management
- Plans live in `.codex/plans/` using status-based suffixes: `.ready.md`, `.in_progress.md`, `.paused.md`, `.completed.md`, `.old.md`.
- Plan lifecycle: architect creates `.ready.md` → start work rename to `.in_progress.md` → pause/rename to `.paused.md` → resume/rename back → finish/rename to `.completed.md`. Use `.old.md` for deprecated approaches.
- Paused work docs: create `paused_work.YYYY-MM-DD_HH-MM-SS.md` when pausing; archive as `paused_work.resumed.*.md` after resuming.
- Commands: `/pause-work` and `/start-work` are defined in `.codex/commands/` and orchestrate pause/resume behavior.

## Agent Workflow (Codex Orchestration)
- Codex is the orchestrator: decide which agent to use, feed it focused instructions, and move outputs through the pipeline.
- Agents (see `.codex/agents/`):
  - `feature-architect`: plans medium/large features.
  - `pi-web-python-developer`: implements and refactors Python/web/camera code.
  - `code-quality-evaluator`: runs post-change quality reviews (mandatory after any code change).
  - `root-cause-analyzer`: performs evidence-based bug investigations before fixes.
  - `test-architect`: designs automated tests (unit/integration/e2e/HW-in-the-loop).
- Quality gate: run `code-quality-evaluator` after every code change. Resolve CRITICAL issues before moving on.

## Workflow Patterns
- New feature: use `feature-architect` → plan saved as `.ready.md` → rename to `.in_progress.md` → feed tasks one at a time to `pi-web-python-developer` → evaluate with `code-quality-evaluator` → iterate until clean → rename plan to `.completed.md`.
- Bug fix: start with `root-cause-analyzer` to produce `.ready.md` analysis → confirm fix scope → rename to `.in_progress.md` → developer implements fixes → quality evaluation loop → rename to `.completed.md`.
- Small/refactor: send focused task to `pi-web-python-developer` → mandatory `code-quality-evaluator` → iterate until no CRITICAL issues.
- Pause/resume: use `/pause-work` and `/start-work` to snapshot and restore context; keep plan files in sync with status.

## Raspberry Pi + Python Web Considerations
- Performance: keep request handlers non-blocking; offload camera capture/processing to worker threads/processes; avoid heavy per-request CPU use on the Pi.
- Cameras: treat USB devices as dynamic (`/dev/video*` may change), probe capabilities (resolution, fps, pixel format), and handle disconnect/reconnect gracefully.
- Streaming: prefer MJPEG/fragmented MP4/RTSP-like patterns; cap frame rate/resolution to what the Pi can sustain; throttle/queue to avoid memory bloat.
- File I/O: store captures predictably, rotate or clean up storage, and avoid excessive writes to SD cards.
- Networking/security: bind to the intended interface, validate inputs, sanitize filenames, and gate any remote control endpoints (auth or IP allowlists when applicable).
- Observability: structured logging with correlation ids per request/capture; lightweight metrics (latency, frame drops, disk usage); health endpoints that verify camera availability.
- Reliability: design idempotent startup/shutdown; systemd service files should restart on failure; handle partial failures (one camera down should not crash the server).
