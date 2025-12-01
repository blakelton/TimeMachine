Pause the current work and save complete context for later resumption.

**Actions to perform:**

1. **Identify what's being worked on**:
   - Check for any `.in_progress.md` plan files in `.codex/plans/`
   - Review conversation history for current task context
   - Identify files that have been modified recently

2. **Create pause documentation** in `.codex/plans/paused_work.YYYY-MM-DD_HH-MM-SS.md` with:
   - Timestamp of pause
   - Work type (Feature Implementation | Bug Fix | Refactoring | Investigation)
   - Associated plan file name (if any)
   - Completed tasks in this session
   - Current in-progress task with progress details
   - Files modified with line ranges
   - Pending CRITICAL/HIGH issues from quality evaluator
   - Recent code changes summary
   - Quality evaluation status
   - Next actions when resuming
   - Open questions or blockers

3. **Update active plan** (if one exists):
   - Read the `.in_progress.md` plan file
   - Add "## Work Paused" section with:
     - Timestamp
     - Tasks completed since plan started
     - Current task state (partial completion, blockers)
     - Reference to pause documentation file
   - Rename: `feature_name.in_progress.md` → `feature_name.paused.md`

4. **Confirm pause** with summary:
   - Show what was captured
   - Show where pause documentation was saved
   - Show plan file status change (if applicable)

**Pause Documentation Format:**
```markdown
# Paused Work Session - [Feature/Bug Name]

**Paused At**: YYYY-MM-DD HH:MM:SS
**Work Type**: [Feature Implementation | Bug Fix | Refactoring | Investigation]
**Associated Plan**: [plan_filename.paused.md or "None"]

## Current Progress

### Completed Tasks
- [List of tasks completed in this session]

### In-Progress Task
- **Task**: [Description of current task]
- **Progress**: [What's done, what's left]
- **Files Modified**: [List of files with line ranges]

### Pending Issues
- **CRITICAL**: [Any critical issues found but not yet resolved]
- **HIGH**: [Any high-priority issues]

## Recent Changes

### Code Modifications
- **File**: path/to/file.py
  - **Lines**: 123-156
  - **What Changed**: [Brief description]
  - **Quality Status**: [Evaluated | Needs Evaluation]

### Quality Reports
- **Last Evaluation**: [Rating and key findings]
- **Unresolved Issues**: [Count and severity breakdown]

## Next Actions

When resuming:
1. [First action to take]
2. [Second action to take]
3. [Remaining tasks from plan]

## Open Questions / Blockers
- [Any questions that need user input]
- [Any blockers preventing progress]

## Context Notes
[Any additional context that would help resume work effectively]
```
