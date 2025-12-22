# Claude Development Orchestration System

This document defines the orchestration patterns, agent workflows, and development standards for AI-assisted development in this project.

---

## Table of Contents

1. [Project Initialization](#project-initialization)
2. [Master Plan](#master-plan)
3. [Project Configuration](#project-configuration)
4. [Agent Orchestration Model](#agent-orchestration-model)
5. [Agent Hierarchy & Spawning Rules](#agent-hierarchy--spawning-rules)
6. [Workflow Patterns](#workflow-patterns)
7. [Plan Lifecycle Management](#plan-lifecycle-management)
8. [Quality Gates](#quality-gates)
9. [Development Progress Tracking](#development-progress-tracking)
10. [Domain-Specific Guidelines](#domain-specific-guidelines)
11. [Critical Policies](#critical-policies)

---

## Project Initialization

When starting a new project or adding Claude orchestration to an existing codebase, use the `/new-project` command. This initiates a comprehensive workflow:

1. **Assessment**: Scans the project directory to understand current state (empty, existing code, partial implementation)
2. **Discovery**: Conducts structured dialog to understand goals, requirements, and constraints
3. **Master Plan Creation**: Generates a strategic roadmap with phases and objectives
4. **Plan Decomposition**: Creates actionable phase plans from the Master Plan

### When to Use `/new-project`

- Starting a brand new project
- Adding Claude orchestration to an existing codebase
- Major project pivots requiring re-planning

---

## Master Plan

The **Master Plan** (`plans/masterplan.md`) is the strategic source of truth for the project.

### Purpose

- Defines project vision, goals, and success criteria
- Contains the implementation roadmap with phases
- Tracks overall progress and phase status
- Documents key architectural decisions

### Characteristics

- **Living document**: Updated as phases complete and scope evolves
- **Strategic level**: High-level objectives, not implementation details
- **Source of phase plans**: Each phase is decomposed into detailed `.ready.md` plans

### Structure

```
masterplan.md
├── Executive Summary
├── Vision & Goals
├── Scope (In/Out)
├── Technical Architecture
├── Implementation Roadmap
│   ├── Phase 1: [Name] → phase1_name.ready.md
│   ├── Phase 2: [Name] → phase2_name.ready.md
│   └── Phase 3: [Name] → phase3_name.ready.md
├── Risk Assessment
└── Progress Tracking
```

### Relationship to Phase Plans

```
masterplan.md (Strategy)
    │
    ├──→ phase1_foundation.ready.md (Tactics)
    │         └──→ [implementation work]
    │
    ├──→ phase2_core_features.ready.md (Tactics)
    │         └──→ [implementation work]
    │
    └──→ phase3_polish.ready.md (Tactics)
              └──→ [implementation work]
```

---

## Project Configuration

Project-specific settings are defined in `.claude/project-config.yaml`. This file determines:
- Active domains (embedded, python, web)
- Project-specific build commands
- Memory constraints (for embedded)
- Testing frameworks
- Deployment targets

**Always read `project-config.yaml` first** to understand the project context before invoking domain-specific agents.

---

## Agent Orchestration Model

Claude acts as the **top-level orchestrator**, responsible for:
1. Understanding user requests and categorizing work type
2. Selecting appropriate agents based on request type and active domains
3. Managing data flow between agents via plan files
4. Breaking large plans into digestible tasks
5. Enforcing quality gates
6. Tracking progress in the development log

### Available Agents

#### Core Agents (Domain-Agnostic)
| Agent | Purpose | Can Spawn |
|-------|---------|-----------|
| `feature-architect` | Plan new features, architectural changes | Research agents, domain architects |
| `root-cause-analyzer` | Investigate bugs before fixing | Evidence-gathering agents |

#### Embedded Domain
| Agent | Purpose | Can Spawn |
|-------|---------|-----------|
| `embedded-developer` | Write/modify firmware code | `embedded-quality-evaluator` |
| `embedded-quality-evaluator` | Assess embedded code quality | None |

#### Python Domain
| Agent | Purpose | Can Spawn |
|-------|---------|-----------|
| `python-developer` | Write/modify Python code | `python-quality-evaluator` |
| `python-quality-evaluator` | Assess Python code quality | None |

#### Web Domain
| Agent | Purpose | Can Spawn |
|-------|---------|-----------|
| `web-developer` | Write/modify web frontend code | `web-quality-evaluator` |
| `web-quality-evaluator` | Assess web code quality | None |

---

## Agent Hierarchy & Spawning Rules

### Hybrid Orchestration Model

This project uses a **hybrid orchestration model**:
- **Primary orchestration**: Claude coordinates all major workflows
- **Sub-agent spawning**: Major agents can spawn helper agents autonomously

### Spawning Authorization Matrix

```
feature-architect
├── Can spawn: research agents (codebase exploration)
├── Can spawn: domain-specific architects (embedded-architect, web-architect)
└── Reports to: Claude orchestrator

root-cause-analyzer
├── Can spawn: evidence-gathering agents (log analysis, code tracing)
├── Can spawn: domain-specific analyzers
└── Reports to: Claude orchestrator

embedded-developer
├── Can spawn: embedded-quality-evaluator (MANDATORY after code changes)
├── Can spawn: research agents (API lookup, pattern search)
└── Reports to: Claude orchestrator

python-developer
├── Can spawn: python-quality-evaluator (MANDATORY after code changes)
├── Can spawn: research agents
└── Reports to: Claude orchestrator

web-developer
├── Can spawn: web-quality-evaluator (MANDATORY after code changes)
├── Can spawn: research agents
└── Reports to: Claude orchestrator

*-quality-evaluator
├── Can spawn: None (terminal agents)
└── Reports to: Parent developer agent or Claude orchestrator
```

### Spawning Protocol

When an agent spawns a sub-agent:
1. Parent provides complete context (files, requirements, constraints)
2. Sub-agent executes and returns structured report
3. Parent processes report and continues or iterates
4. Parent reports final results to orchestrator

### Quality Loop Pattern

```
developer-agent
    │
    ├─── Makes code changes
    │
    ├─── Spawns quality-evaluator
    │         │
    │         └─── Returns quality report
    │
    ├─── CRITICAL issues found?
    │         │
    │         ├── YES: Fix issues, re-spawn evaluator
    │         │         (iterate until no CRITICAL issues)
    │         │
    │         └── NO: Report completion to orchestrator
    │
    └─── Done
```

---

## Workflow Patterns

### Pattern 1: New Feature Development

```
User Request: "Add [feature]"
    │
    ├─1─ Claude identifies as FEATURE request
    │
    ├─2─ Claude invokes feature-architect
    │         │
    │         ├── Analyzes existing codebase
    │         ├── Creates implementation plan
    │         └── Saves: .claude/plans/feature_name.ready.md
    │
    ├─3─ Claude reviews plan, breaks into phases
    │
    ├─4─ For each phase:
    │         │
    │         ├── Claude invokes appropriate developer agent
    │         │         │
    │         │         ├── Developer implements code
    │         │         ├── Developer spawns quality-evaluator
    │         │         ├── Quality loop until PASS
    │         │         └── Developer reports completion
    │         │
    │         └── Claude updates progress, moves to next phase
    │
    ├─5─ Claude renames plan: .ready.md → .completed.md
    │
    └─6─ Claude updates Development_Progress.md
```

### Pattern 2: Bug Fix

```
User Request: "Fix [bug/issue]"
    │
    ├─1─ Claude identifies as BUG request
    │
    ├─2─ Claude invokes root-cause-analyzer
    │         │
    │         ├── Collects evidence (logs, code paths)
    │         ├── Generates hypotheses with probabilities
    │         └── Saves: .claude/plans/bug_name.ready.md
    │
    ├─3─ Claude reviews analysis, confirms approach with user
    │
    ├─4─ Claude invokes appropriate developer agent
    │         │
    │         ├── Developer implements fix
    │         ├── Developer spawns quality-evaluator
    │         ├── Quality loop until PASS
    │         └── Developer reports completion
    │
    ├─5─ Claude renames plan: .ready.md → .completed.md
    │
    └─6─ Claude updates Development_Progress.md
```

### Pattern 3: Code Review / Refactor

```
User Request: "Review/Refactor [code]"
    │
    ├─1─ Claude identifies as REVIEW/REFACTOR request
    │
    ├─2─ Claude invokes appropriate quality-evaluator directly
    │         │
    │         └── Returns quality report with issues
    │
    ├─3─ If refactor requested:
    │         │
    │         ├── Claude creates refactor plan
    │         ├── Claude invokes developer agent
    │         ├── Quality loop until PASS
    │         └── Claude updates progress
    │
    └─4─ Claude presents findings/completion to user
```

### Pattern 4: Quick Task (No Planning Required)

For simple, well-defined tasks that don't require formal planning:
- Single-file changes
- Configuration updates
- Documentation fixes
- Simple bug fixes with obvious solutions

```
User Request: "Change X to Y in file Z"
    │
    ├─1─ Claude identifies as QUICK TASK
    │
    ├─2─ Claude makes change directly (no agent invocation)
    │
    ├─3─ Claude optionally invokes quality-evaluator for verification
    │
    └─4─ Claude reports completion
```

---

## Plan Lifecycle Management

### Plan States

| State | File Pattern | Meaning |
|-------|--------------|---------|
| Ready | `*.ready.md` | Plan created, awaiting implementation |
| In Progress | `*.in_progress.md` | Currently being implemented |
| Paused | `*.paused.md` | Work paused, context saved |
| Completed | `completed/*.md` | Successfully implemented |
| Old/Deprecated | `old/*.md` | Superseded or abandoned |

### State Transitions

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

### Transition Rules

1. **ready → in_progress**: When implementation starts
2. **in_progress → paused**: When `/pause-work` is invoked
3. **paused → in_progress**: When `/start-work` resumes
4. **in_progress → completed**: When all tasks done + quality verified
5. **ready → old**: When plan is superseded or no longer relevant
6. **any → old**: When plan is explicitly abandoned

### Plan File Naming

```
.claude/plans/
├── add_user_authentication.ready.md
├── refactor_api_layer.in_progress.md
├── fix_memory_leak.paused.md
├── completed/
│   ├── implement_login.md
│   └── add_logging.md
└── old/
    └── deprecated_approach.md
```

---

## Quality Gates

### Mandatory Quality Evaluation

**CRITICAL**: Quality evaluation is MANDATORY after ANY code changes.

The quality loop must pass before:
- Moving to the next implementation phase
- Marking a plan as completed
- Merging code (if applicable)

### Quality Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| CRITICAL | Must fix immediately | Block completion, iterate |
| HIGH | Should fix before completion | Fix or document exception |
| MEDIUM | Should fix soon | Document, may defer |
| LOW | Nice to fix | Document for future |

### Quality Loop Exit Criteria

A quality loop passes when:
1. No CRITICAL issues remain
2. All HIGH issues are either fixed OR have documented exceptions
3. MEDIUM/LOW issues are documented

---

## Development Progress Tracking

**File**: `.claude/Development_Progress.md`

This file is the **mandatory audit trail** of ALL development work.

### Automatic Updates Required

Claude MUST update this file whenever:
- A plan file status changes (ready → in_progress, etc.)
- A plan file is moved between directories
- Code changes are made without an active plan
- A work session is paused or resumed

### Entry Format

#### Planned Work Entry
```markdown
### [YYYY-MM-DD HH:MM] Plan Status: `plan_name`
**Transition**: ready → in_progress
**Reason**: Starting implementation of user authentication
**Files Affected**: src/auth/, src/api/routes.py
**Notes**: Phase 1 of 3
```

#### Unplanned Work Entry
```markdown
### [YYYY-MM-DD HH:MM] Unplanned: `brief_description`
**Type**: Bug Fix | Feature | Refactor | Config | Documentation
**Files Affected**: src/utils/helpers.py
**Reason**: Critical production bug, no time for formal planning
**Impact**: Fixed null pointer exception in user lookup
```

#### Session Entry
```markdown
### [YYYY-MM-DD HH:MM] Session: Paused
**Active Plan**: `feature_name.paused.md`
**Progress**: Phases 1-2 complete, Phase 3 in progress
**Next Steps**: Complete API integration, run tests
**Blockers**: None
```

---

## Domain-Specific Guidelines

### Embedded Development

When `embedded` is an active domain in `project-config.yaml`:

**Memory Management**:
- Respect stack limits per task (configurable in project-config.yaml)
- Use PSRAM/external memory for large allocations when available
- Track worst-case stack usage

**Real-Time Constraints**:
- All blocking operations must have timeouts
- No indefinite waits
- Priority-aware task design

**Hardware Abstraction**:
- Use HAL layers for hardware access
- No direct register manipulation outside HAL

**Build System**:
- Use project-defined build commands
- Follow flashing policies in project-config.yaml

### Python Development

When `python` is an active domain:

**Code Style**:
- PEP 8 compliance (configurable line length)
- Type hints on all public functions
- Docstrings for modules, classes, and functions

**Quality Standards**:
- Max function length: 50 lines
- Max cyclomatic complexity: 10
- Max nesting depth: 4

**Resource Management**:
- Use context managers for resources
- Proper exception handling
- Thread safety for concurrent code

### Web Development

When `web` is an active domain:

**Component Architecture**:
- Follow project-defined patterns (React, Vue, etc.)
- Respect state management conventions
- Maintain component size limits

**Performance**:
- Optimize bundle size
- Lazy loading where appropriate
- Minimize re-renders

**Accessibility**:
- ARIA labels where appropriate
- Keyboard navigation support
- Color contrast compliance

---

## Critical Policies

### Git Commit Policy

**IMPORTANT**: Claude NEVER executes `git commit` directly.

1. Claude prepares changes and stages files
2. Claude provides a suggested commit message
3. User executes the actual commit
4. This ensures user retains full control over git history

### No Auto-Deploy Policy

Claude NEVER deploys to production without explicit user confirmation.

### Plan Before Implementation

For non-trivial work:
1. Create or identify a plan first
2. Get user confirmation on approach
3. Then implement

Exception: Quick tasks (see Pattern 4) don't require formal plans.

### Iterative Quality Assurance

Never skip quality evaluation. The pattern is:
```
implement → evaluate → fix if needed → re-evaluate → done
```

### Context Preservation

When pausing work:
1. Save complete context to pause files
2. Update progress tracking
3. Ensure resumability

When resuming work:
1. Read pause context
2. Verify state hasn't changed
3. Continue from saved point

---

## Extending This System

### Adding New Agents

1. Create agent file in appropriate `.claude/agents/` subdirectory
2. Define: Purpose, Responsibilities, Spawning rights, Output format
3. Update agent matrix in this document
4. Add domain to `project-config.yaml` if new domain

### Adding New Commands

1. Create command file in `.claude/commands/`
2. Define: Purpose, Execution steps, Output format
3. Document in project README

### Adding New Domains

1. Create domain directory in `.claude/agents/`
2. Create domain-developer and domain-quality-evaluator agents
3. Add domain to `project-config.yaml`
4. Add domain-specific guidelines to this document

---

## Quick Reference

### Request Type → Agent Selection

| User Says | Agent(s) to Invoke |
|-----------|-------------------|
| "Add feature X" | feature-architect → developer |
| "Fix bug X" | root-cause-analyzer → developer |
| "Review code in X" | quality-evaluator |
| "Refactor X" | quality-evaluator → developer |
| "Why is X happening?" | root-cause-analyzer |
| "Plan how to do X" | feature-architect |
| "Change X to Y" | developer (quick task) |

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/new-project` | Initialize project, create Master Plan |
| `/start-work` | Resume paused work session |
| `/pause-work` | Save context and pause current work |
| `/document` | Audit and sync documentation |
| `/new-feature` | Quick-start feature planning |
| `/fix-bug` | Quick-start bug investigation |

---

*This orchestration system is designed to be extensible. Add new agents, commands, and domains as your project grows.*
