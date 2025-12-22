---
description: Initialize project with Master Plan and orchestration setup
---

# New Project Command

## Purpose

Initialize or onboard a project with Claude orchestration. This command:
1. Assesses the current state of the project (empty vs existing code)
2. Conducts a discovery dialog to understand goals and requirements
3. Creates a Master Plan with phases and objectives
4. Decomposes the Master Plan into actionable phase plans

This is the **starting point** for any new project or when adding Claude orchestration to an existing codebase.

## Usage

```
/new-project
```

## Execution Steps

### Phase 1: Project State Assessment

#### 1.1 Scan Project Directory

Determine what exists in the project:

```markdown
## Project Assessment

Scanning project directory...

### Directory Analysis
- **Total files**: [N]
- **Code files**: [N]
- **Configuration files**: [N]
- **Documentation files**: [N]

### Technology Detection
| Category | Detected | Confidence |
|----------|----------|------------|
| Language(s) | [list] | [High/Med/Low] |
| Framework(s) | [list] | [High/Med/Low] |
| Build System | [detected] | [High/Med/Low] |
| Package Manager | [detected] | [High/Med/Low] |
| Testing Framework | [detected] | [High/Med/Low] |

### Project Structure
[Tree or summary of key directories]

### Existing Documentation
- README.md: [Found/Not Found] - [summary if found]
- Other docs: [list]

### Code Analysis Summary
- Estimated complexity: [Low/Medium/High]
- Apparent architecture: [description]
- Key components identified: [list]
```

#### 1.2 Classify Project State

Determine which scenario applies:

**Scenario A: Empty/New Project**
```markdown
### Project State: NEW PROJECT

This appears to be a new/empty project. No significant code detected.

We'll start from scratch:
1. Define project vision and goals
2. Identify requirements and constraints
3. Design architecture
4. Create implementation roadmap
```

**Scenario B: Existing Codebase - No Documentation**
```markdown
### Project State: EXISTING CODE (Undocumented)

Found existing codebase without clear documentation.

Detected:
- [N] source files in [languages]
- [Framework/patterns detected]
- [Key components identified]

We'll need to:
1. Understand current functionality
2. Identify gaps and goals
3. Plan enhancements or completion
```

**Scenario C: Existing Codebase - With Documentation**
```markdown
### Project State: EXISTING CODE (Documented)

Found existing codebase with documentation.

From README/docs:
- Purpose: [extracted purpose]
- Current state: [what exists]
- Known issues: [if documented]

We'll:
1. Verify understanding matches reality
2. Identify what's complete vs planned
3. Plan next steps
```

**Scenario D: Partial Implementation**
```markdown
### Project State: PARTIAL IMPLEMENTATION

Found code that appears to be a work-in-progress.

Observations:
- Complete: [what seems finished]
- In progress: [what seems partial]
- Planned: [TODOs, stubs found]

We'll:
1. Map current state
2. Understand original vision
3. Plan completion or pivot
```

### Phase 2: Discovery Dialog

Engage in structured conversation to understand the project.

#### 2.1 For New Projects

```markdown
## Project Discovery

Let's define your project. I'll ask questions in a few categories.

### Vision & Purpose

1. **What problem does this project solve?**
   [User's answer]

2. **Who is the target user/audience?**
   [User's answer]

3. **What's the core value proposition?**
   [User's answer]

### Scope & Boundaries

4. **What are the must-have features (MVP)?**
   [User's answer]

5. **What's explicitly out of scope (for now)?**
   [User's answer]

6. **Are there existing solutions? How is this different?**
   [User's answer]

### Technical Context

7. **Any technology preferences or constraints?**
   [User's answer]

8. **What environments will this run in?**
   [User's answer]

9. **Any integration requirements?**
   [User's answer]

### Constraints & Requirements

10. **Timeline or milestone pressures?**
    [User's answer]

11. **Performance, security, or compliance requirements?**
    [User's answer]

12. **Team context (solo, team, open source)?**
    [User's answer]
```

#### 2.2 For Existing Codebases

```markdown
## Project Discovery

I've analyzed the existing codebase. Let me verify my understanding and learn more.

### Current State Verification

1. **Is this assessment accurate?**
   [Present findings from Phase 1]

   User confirmation: [Yes/No with corrections]

2. **What is the project's purpose?**
   [User's answer or confirmation of detected purpose]

3. **What's the current development status?**
   - [ ] Early development
   - [ ] MVP complete
   - [ ] In production
   - [ ] Maintenance mode
   - [ ] Needs revival/refactoring

### Goals Going Forward

4. **What do you want to accomplish next?**
   [User's answer]

5. **Are there known issues or technical debt to address?**
   [User's answer]

6. **Any features planned but not yet implemented?**
   [User's answer]

### Context

7. **What's working well that we should preserve?**
   [User's answer]

8. **What's painful or needs improvement?**
   [User's answer]
```

#### 2.3 Iterative Clarification

Continue dialog until clear understanding:

```markdown
### Clarification Needed

Based on your answers, I have some follow-up questions:

1. [Specific clarification question]
2. [Another clarification]

[Continue until picture is clear]
```

### Phase 3: Update Project Configuration

Based on discovery, update `project-config.yaml`:

```markdown
## Configuring Project

Based on our discussion, I'll configure the project settings:

### Domains Enabled
- Embedded: [Yes/No] - [reason]
- Python: [Yes/No] - [reason]
- Web: [Yes/No] - [reason]

### Key Settings
[Show relevant configuration being set]

Updating `project-config.yaml`...
```

### Phase 4: Create Master Plan

Generate the strategic Master Plan document.

#### 4.1 Master Plan Structure

Create `.claude/plans/masterplan.md`:

```markdown
# Master Plan: [Project Name]

> This is a living document that defines the project vision, objectives, and implementation roadmap.
> Last updated: [timestamp]

## Executive Summary

[2-3 paragraph overview of what this project is and why it exists]

## Vision Statement

[Clear, inspiring statement of what success looks like]

## Problem Statement

[What problem does this solve? For whom?]

## Goals & Objectives

### Primary Goals
1. [Goal 1]: [Description]
2. [Goal 2]: [Description]
3. [Goal 3]: [Description]

### Success Metrics
| Metric | Target | How Measured |
|--------|--------|--------------|
| [metric] | [target] | [measurement] |

## Scope

### In Scope (MVP)
- [Feature/capability 1]
- [Feature/capability 2]
- [Feature/capability 3]

### In Scope (Future)
- [Future feature 1]
- [Future feature 2]

### Out of Scope
- [Explicitly excluded 1]
- [Explicitly excluded 2]

## Technical Architecture

### Overview
[High-level architecture description]

### Technology Stack
| Layer | Technology | Rationale |
|-------|------------|-----------|
| [layer] | [tech] | [why] |

### Key Design Decisions
| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| [decision] | [choice] | [alternatives] | [why] |

### Constraints
- [Technical constraint 1]
- [Technical constraint 2]

## Implementation Roadmap

### Phase 1: [Phase Name]
**Objective**: [What this phase accomplishes]
**Duration Estimate**: [Optional - only if user wants estimates]

#### Deliverables
- [ ] [Deliverable 1]
- [ ] [Deliverable 2]
- [ ] [Deliverable 3]

#### Key Tasks
1. [Task 1]
2. [Task 2]
3. [Task 3]

#### Dependencies
- [What must exist before this phase]

#### Success Criteria
- [How we know this phase is complete]

---

### Phase 2: [Phase Name]
[Same structure as Phase 1]

---

### Phase 3: [Phase Name]
[Same structure as Phase 1]

---

[Additional phases as needed]

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| [risk] | [H/M/L] | [H/M/L] | [mitigation] |

## Open Questions

- [ ] [Question that needs answering]
- [ ] [Another question]

## Progress Tracking

### Current Status
**Active Phase**: [None - not started]
**Overall Progress**: 0%

### Phase Status
| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| Phase 1 | Not Started | 0% | - |
| Phase 2 | Not Started | 0% | - |
| Phase 3 | Not Started | 0% | - |

### Changelog
| Date | Change | Reason |
|------|--------|--------|
| [today] | Initial plan created | Project initialization |

---

**Status**: active
**Created**: [timestamp]
**Author**: /new-project + feature-architect
```

### Phase 5: Decompose into Phase Plans

For each phase in the Master Plan, create detailed implementation plans.

#### 5.1 Invoke Feature Architect

For each phase:

```markdown
## Creating Phase Plans

The Master Plan defines [N] phases. Now creating detailed implementation plans for each...

### Phase 1: [Name]
Invoking feature-architect to create detailed plan...

[Feature architect analyzes Phase 1 requirements and creates:]
→ `.claude/plans/phase1_[name].ready.md`

### Phase 2: [Name]
Invoking feature-architect to create detailed plan...

→ `.claude/plans/phase2_[name].ready.md`

[Continue for all phases]
```

#### 5.2 Complex Item Decomposition

For complex items within phases:

```markdown
### Decomposing Complex Items

Phase 1 contains complex items that need their own plans:

- **[Complex Item]**: Creating separate plan...
  → `.claude/plans/phase1_[item_name].ready.md`
```

### Phase 6: Finalization

#### 6.1 Summary Report

```markdown
## Project Initialization Complete

### Created Documents

| Document | Purpose |
|----------|---------|
| `project-config.yaml` | Project configuration |
| `plans/masterplan.md` | Strategic overview and roadmap |
| `plans/phase1_[name].ready.md` | Phase 1 implementation plan |
| `plans/phase2_[name].ready.md` | Phase 2 implementation plan |
| [additional plans] | [purposes] |

### Project Overview

**Name**: [Project name]
**Type**: [New/Existing enhancement]
**Domains**: [enabled domains]
**Phases**: [N]

### Roadmap Summary

```
Phase 1: [Name] ─────────────────────────→ [Deliverable]
    │
Phase 2: [Name] ─────────────────────────→ [Deliverable]
    │
Phase 3: [Name] ─────────────────────────→ [Deliverable]
```

### Ready to Start

To begin implementation:
1. Run `/start-work` to see available plans
2. Select Phase 1 plan to begin
3. Or review `masterplan.md` first

### Next Steps
1. [Recommended first action]
2. [Second recommended action]

Would you like to start with Phase 1 now?
```

#### 6.2 Update Development Progress

```markdown
### [YYYY-MM-DD HH:MM] Project Initialized
**Command**: /new-project
**Project**: [name]
**State**: [New/Existing]
**Master Plan**: `plans/masterplan.md`
**Phases Created**: [N]
**Phase Plans**: [list]
**Notes**: [any notes]
```

## Handling Edge Cases

### Conflicting Information
```markdown
## Clarification Needed

I found some conflicting information:
- [Conflict 1]
- [Conflict 2]

Which is correct? This affects how I structure the plan.
```

### Scope Too Large
```markdown
## Scope Assessment

The described project is quite large. Consider:

**Option A**: Full scope as described
- [N] phases estimated
- Complex architecture
- Long timeline

**Option B**: Reduced MVP scope
- Focus on: [core features]
- Defer: [secondary features]
- Faster to first value

**Option C**: Phased rollout
- Start with [minimal viable]
- Expand in future phases

Which approach would you prefer?
```

### Existing Codebase Issues
```markdown
## Codebase Assessment Findings

During analysis, I found some concerns:

### Technical Debt
- [Issue 1]: [severity]
- [Issue 2]: [severity]

### Architectural Concerns
- [Concern]: [implication]

### Recommendations
1. Address [critical issue] before new features
2. Refactor [component] as part of Phase 1
3. [Other recommendations]

Should we incorporate these into the plan?
```

## Notes

- This command should be run once at project start
- The Master Plan becomes the source of truth for project direction
- Update Master Plan when major scope changes occur
- Phase plans are the working documents; Master Plan is the strategy
- Re-run `/new-project` only for major pivots (it will ask to archive existing)
