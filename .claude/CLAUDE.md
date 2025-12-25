# Claude Development Orchestration System

---

# 🛑 ORCHESTRATION IS NON-NEGOTIABLE 🛑

## YOU CANNOT PROCEED WITHOUT COMPLETING THESE STEPS

This is not guidance. This is not a suggestion. These are **requirements**.

**Failure to follow orchestration = Invalid work that must be redone.**

---

## BEFORE ANY TASK - MANDATORY GATE

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│   YOU ARE BLOCKED FROM WRITING CODE UNTIL YOU COMPLETE THESE STEPS:       │
│                                                                            │
│   1. ☐ Invoke the REQUIRED skill (/fix-bug, /new-feature, etc.)           │
│   2. ☐ Wait for agent investigation/planning to complete                   │
│   3. ☐ Get user approval on approach                                       │
│   4. ☐ Create TodoWrite task list                                          │
│                                                                            │
│   ONLY THEN may you write code.                                            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## AFTER ANY CODE CHANGE - MANDATORY GATE

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│   YOU ARE BLOCKED FROM REPORTING COMPLETION UNTIL YOU:                     │
│                                                                            │
│   1. ☐ Spawn quality-evaluator agent (Task tool)                          │
│   2. ☐ Review the evaluation report                                        │
│   3. ☐ Fix all CRITICAL and HIGH issues                                    │
│   4. ☐ Re-evaluate if fixes were made                                      │
│   5. ☐ Update Development_Progress.md                                      │
│                                                                            │
│   ONLY THEN is the work complete.                                          │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## REQUIRED SKILL FOR EACH REQUEST TYPE

| User Request Pattern | REQUIRED Action | If You Skip This |
|---------------------|-----------------|------------------|
| Bug / Issue / Broken / Fix | `Skill: fix-bug` | ❌ INVALID - Redo |
| Add / Create / Implement feature | `Skill: new-feature` | ❌ INVALID - Redo |
| Where / How / Find (exploration) | `Task: Explore agent` | ❌ INVALID - Redo |
| After ANY code change | `Task: quality evaluation` | ❌ INVALID - Redo |

**There are NO exceptions. "Quick fixes" still require quality evaluation.**

---

## THE ORCHESTRATION SEQUENCE

### For Bugs (REQUIRED: `/fix-bug`)

```
User reports bug
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 1: Invoke /fix-bug skill       │  ◄── REQUIRED
│  This spawns root-cause-analyzer     │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 2: Agent investigates          │  ◄── WAIT FOR THIS
│  - Reads logs                        │
│  - Traces code paths                 │
│  - Creates hypothesis                │
│  - Writes plan file                  │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 3: Review with user            │  ◄── GET APPROVAL
│  - Confirm root cause                │
│  - Agree on fix approach             │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 4: Create TodoWrite list       │  ◄── REQUIRED
│  - Track each fix step               │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 5: Implement fix               │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 6: Quality evaluation          │  ◄── REQUIRED
│  Task(subagent_type="general-purpose"│
│  prompt="Evaluate code quality...")  │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 7: Fix issues from evaluation  │  ◄── IF ANY FOUND
│  Then re-evaluate                    │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 8: Update progress log         │  ◄── REQUIRED
│  .claude/Development_Progress.md     │
└──────────────────────────────────────┘
       │
       ▼
     DONE
```

### For Features (REQUIRED: `/new-feature`)

```
User requests feature
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 1: Invoke /new-feature skill   │  ◄── REQUIRED
│  This spawns feature-architect       │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 2: Agent plans                 │  ◄── WAIT FOR THIS
│  - Analyzes codebase                 │
│  - Designs architecture              │
│  - Writes implementation plan        │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 3: Review with user            │  ◄── GET APPROVAL
│  - Confirm approach                  │
│  - Agree on phases                   │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 4: Create TodoWrite list       │  ◄── REQUIRED
│  - Track each implementation phase   │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 5: Implement each phase        │
│         │                            │
│         ▼                            │
│  STEP 6: Quality eval EACH phase     │  ◄── REQUIRED PER PHASE
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 7: Update progress log         │  ◄── REQUIRED
└──────────────────────────────────────┘
       │
       ▼
     DONE
```

---

## QUALITY EVALUATION IS MANDATORY

### You MUST spawn a quality evaluator after:

- ✓ Every bug fix
- ✓ Every feature implementation
- ✓ Every refactor
- ✓ Every code change, no matter how small
- ✓ Even "quick" single-line fixes

### How to Evaluate

```python
Task(
    subagent_type="general-purpose",
    prompt="""
    Evaluate code quality of the following files:
    - [list files here]

    Check for:
    1. Syntax errors
    2. Import issues
    3. Type consistency
    4. Logic errors
    5. Missing error handling

    This is evaluation only - do not write code.
    Report issues by severity: CRITICAL, HIGH, MEDIUM, LOW.
    """
)
```

### Evaluation Response Requirements

| Severity | Your Action |
|----------|-------------|
| CRITICAL | STOP. Fix immediately. Re-evaluate. |
| HIGH | Fix before completing. Re-evaluate. |
| MEDIUM | Document. May proceed. |
| LOW | Note for future. May proceed. |

---

## TODOWRITE IS REQUIRED

For any task with more than one step:

1. Create a TodoWrite list BEFORE starting
2. Mark items `in_progress` when working on them
3. Mark items `completed` when done
4. Only ONE item should be `in_progress` at a time

```python
TodoWrite(todos=[
    {"content": "Step 1", "status": "in_progress", "activeForm": "Doing step 1"},
    {"content": "Step 2", "status": "pending", "activeForm": "Doing step 2"},
    {"content": "Quality evaluation", "status": "pending", "activeForm": "Evaluating code quality"},
])
```

---

## DEVELOPMENT PROGRESS LOG IS REQUIRED

**File**: `.claude/Development_Progress.md`

Update this file when:
- Starting work
- Completing work
- Making any code changes

Format:
```markdown
### [YYYY-MM-DD HH:MM] Type: `name`
**Summary**: What was done
**Files Changed**: List of files
**Quality**: Evaluation result (passed/issues found)
```

---

## EXPLORATION REQUIRES EXPLORE AGENT

When user asks:
- "Where is X?"
- "How does Y work?"
- "Find Z in the codebase"

You MUST use:
```python
Task(
    subagent_type="Explore",
    prompt="Find/explain [whatever user asked]"
)
```

You MUST NOT use Grep/Glob directly for open-ended exploration.

---

## SLASH COMMANDS REFERENCE

| Command | Required When | What Happens |
|---------|--------------|--------------|
| `/fix-bug` | Any bug/issue | Spawns root-cause-analyzer |
| `/new-feature` | Any new functionality | Spawns feature-architect |
| `/start-work` | Resuming paused work | Loads saved context |
| `/pause-work` | Stopping mid-task | Saves context |

---

## SELF-VERIFICATION CHECKLIST

Before reporting ANY task as complete, verify:

```
□ Did I use the required skill (/fix-bug or /new-feature)?
□ Did I wait for agent investigation/planning?
□ Did I get user approval before coding?
□ Did I use TodoWrite to track progress?
□ Did I spawn quality-evaluator AFTER code changes?
□ Did I fix CRITICAL/HIGH issues from evaluation?
□ Did I update Development_Progress.md?
```

**If ANY box is unchecked, the work is INCOMPLETE.**

---

## VIOLATIONS

The following are orchestration violations that invalidate your work:

| Violation | Why It's Invalid |
|-----------|------------------|
| Fixing a bug without `/fix-bug` | No root cause analysis performed |
| Implementing feature without `/new-feature` | No architecture planning done |
| Skipping quality evaluation | Bugs may exist in code |
| Not using TodoWrite | Progress not tracked |
| Not updating progress log | No audit trail |
| Using Grep/Glob for exploration | Incomplete search |

**If you commit a violation, you must redo the work correctly.**

---

## REMEMBER

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Orchestration is not overhead.                            │
│   Orchestration is not optional.                            │
│   Orchestration IS the work.                                │
│                                                             │
│   Without orchestration, code changes are:                  │
│   - Unplanned                                               │
│   - Unverified                                              │
│   - Untracked                                               │
│   - Unreliable                                              │
│                                                             │
│   Follow the process. Every time. No shortcuts.             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
