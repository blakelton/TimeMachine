---
description: Save context and pause the current work session for later resumption
---

# Pause Work Command

## Purpose

Save complete context before pausing a work session. This enables seamless resumption with `/start-work` by capturing:
- Current progress
- In-flight work
- Next steps
- Any blockers or context

## Execution Steps

### Step 1: Identify Current Work

Find active work session by searching for:

```
.claude/plans/*.in_progress.md
```

If multiple in-progress plans found:
```markdown
## Multiple Active Plans

| # | Plan | Started | Progress |
|---|------|---------|----------|
| 1 | [name] | [date] | [X/Y phases] |
| 2 | [name] | [date] | [X/Y phases] |

**Which plan are you pausing?** Or "all" to pause everything.
```

If no in-progress plans:
```markdown
## No Active Work Session

There are no in-progress plans to pause.

If you were working without a plan, would you like to:
1. Create a plan for the current work and then pause
2. Just end the session without saving state

What would you like to do?
```

### Step 2: Gather Pause Context

Collect the following information:

**From conversation history**:
- What tasks were completed this session
- What is currently in progress
- What was about to be done next
- Any issues encountered

**From plan file**:
- Overall progress through phases
- Remaining tasks
- Dependencies

**From user (if not clear)**:
- Any additional context to save
- Known blockers
- Priority notes for resumption

### Step 3: Update the Plan File

Add a "Pause Note" section at the end of the plan:

```markdown
---

## Pause Note - [YYYY-MM-DD HH:MM]

### Session Summary
[Brief description of what was accomplished]

### Completed This Session
- [x] [Task 1]
- [x] [Task 2]

### Currently In Progress
- [ ] [Task being worked on]
  - Status: [how far along]
  - Blocker: [if any]

### Next Steps
1. [Immediate next action]
2. [Following action]
3. [And then]

### Modified Files This Session
- `path/to/file1.py` - [what changed]
- `path/to/file2.ts` - [what changed]

### Blockers/Issues
- [Blocker 1]: [details]
- [Question]: [details]

### Context Notes
[Any additional context that would be helpful when resuming]

---
```

### Step 4: Rename Plan File

```
feature_name.in_progress.md → feature_name.paused.md
```

### Step 5: Create Pause Context File

Create detailed context file at:
```
.claude/plans/paused_work.YYYY-MM-DD_HHMM.md
```

Content:

```markdown
# Paused Work Context

**Timestamp**: [ISO timestamp]
**Plan**: [plan name]
**Plan File**: `.claude/plans/[filename].paused.md`

## Session Overview

### Duration
- Started: [when this session began, if known]
- Paused: [now]

### Goals This Session
- [Goal 1]: [COMPLETED/PARTIAL/NOT STARTED]
- [Goal 2]: [COMPLETED/PARTIAL/NOT STARTED]

## Progress Summary

### Overall Plan Progress
- Phase 1: [STATUS]
- Phase 2: [STATUS]
- Phase 3: [STATUS]
- ...

### Completed Tasks
- [Task with details]
- [Task with details]

### In-Progress Task
**Task**: [Description]
**Status**: [How far along]
**Files Touched**: [list]
**Next Action**: [Specific next step]

## Files Modified

### This Session
| File | Status | Changes |
|------|--------|---------|
| [path] | Modified | [description] |
| [path] | Created | [description] |

### Pending Changes
[Any uncommitted changes noted]

## Technical Context

### Key Decisions Made
- [Decision]: [Rationale]

### Patterns Being Followed
- [Pattern]: [Where/why]

### Open Questions
- [Question that needs answering]

## Blockers & Issues

### Active Blockers
| Blocker | Impact | Resolution Needed |
|---------|--------|-------------------|
| [blocker] | [impact] | [what needs to happen] |

### Issues Encountered
- [Issue]: [Status/Resolution]

## Next Session Plan

### Immediate Priority
1. [First thing to do when resuming]

### Session Goals
1. [What to accomplish]
2. [What to accomplish]

### Time Estimate
[Rough estimate if helpful]

## Notes for Future Self

[Any context that would be helpful but doesn't fit above]

---
**Pause file created by**: /pause-work
**Resume with**: /start-work
```

### Step 6: Update Development Progress

Add entry to `Development_Progress.md`:

```markdown
### [YYYY-MM-DD HH:MM] Session: Paused
**Plan**: `feature_name.paused.md`
**Progress**: [Brief summary]
**Completed**: [List of completed items]
**In Progress**: [Current task]
**Next Steps**: [What to do next]
**Blockers**: [Any blockers, or "None"]
**Resume File**: `paused_work.YYYY-MM-DD_HHMM.md`
```

### Step 7: User Confirmation

Present summary to user:

```markdown
## Work Paused Successfully

### Saved Context
- **Plan**: `feature_name.paused.md`
- **Context File**: `paused_work.YYYY-MM-DD_HHMM.md`

### Progress Saved
- Completed: [X] tasks
- In progress: [Y] task
- Remaining: [Z] tasks

### To Resume
Run `/start-work` to continue where you left off.

### Files Modified This Session
- [file1]
- [file2]

**Note**: Remember to commit your changes if desired before closing.

Session paused at [timestamp]. See you next time!
```

## Quick Pause (Minimal Context)

If user is in a hurry, offer quick pause:

```markdown
## Quick Pause Mode

Saving minimal context for fast pause...

- Plan renamed: ✓
- Basic context saved: ✓
- Progress log updated: ✓

**Warning**: Detailed context not captured. When resuming, you may need to re-orient yourself in the codebase.

Session paused. Run `/start-work` to resume.
```

## Error Handling

### No Active Plan But Work Done
```markdown
## Unplanned Work Detected

You've made changes but there's no active plan. Would you like to:

1. Create a quick plan capturing the current work and pause it
2. Just log the session in Development_Progress.md
3. Continue without saving formal context

What would you like to do?
```

### Unable to Determine Progress
```markdown
## Context Unclear

I'm having trouble determining the current state. Please provide:

1. What task were you working on?
2. How far did you get?
3. What's the next step?

This will ensure accurate resumption.
```

## Notes

- Always rename the plan file BEFORE creating the pause context file
- The pause context file acts as a "save game" for the session
- Multiple pause files can exist (for different plans or sessions)
- Old pause files should be cleaned up after successful resume
- Update `Development_Progress.md` on every pause operation
