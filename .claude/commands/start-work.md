---
description: Resume a previously paused work session or start a ready plan
---

# Start Work Command

## Purpose

Resume a previously paused work session or start work on a ready plan. This command restores context from saved pause files and continues implementation where you left off.

## Execution Steps

### Step 1: Search for Paused Work

Search for work to resume in priority order:

**Option A - Explicit Pause Files (Highest Priority)**:
```
.claude/plans/paused_work.*.md
```
These files contain saved session context from `/pause-work`.

**Option B - Paused Plans**:
```
.claude/plans/*.paused.md
```
These are plans that were paused mid-implementation.

**Option C - In-Progress Plans (May be interrupted)**:
```
.claude/plans/*.in_progress.md
```
These may be from interrupted sessions.

**Option D - Ready Plans (No previous work)**:
```
.claude/plans/*.ready.md
```
New work ready to start.

### Step 2: Present Findings

If paused work found, present a summary:

```markdown
## Paused Work Found

### [Plan Name]
**File**: [filename]
**Last Paused**: [timestamp from file]

#### Progress
- Completed: [list completed items]
- In Progress: [current item]
- Remaining: [list remaining items]

#### Context Summary
[Brief summary of what was happening]

#### Last Actions
- [Recent action 1]
- [Recent action 2]

#### Next Steps
1. [Immediate next step]
2. [Following step]

#### Files Modified
- [file1]
- [file2]

#### Blockers/Issues
[Any noted blockers]

---

**Resume this work?** [YES/NO]
```

### Step 3: Handle Multiple Paused Sessions

If multiple paused sessions exist:

```markdown
## Multiple Paused Work Sessions Found

| # | Plan | Last Paused | Progress | Priority |
|---|------|-------------|----------|----------|
| 1 | [name] | [date] | [X/Y phases] | [suggested priority] |
| 2 | [name] | [date] | [X/Y phases] | [suggested priority] |
| 3 | [name] | [date] | [X/Y phases] | [suggested priority] |

**Which would you like to resume?** Enter number or "list" for details.
```

### Step 4: Resume Selected Work

When user confirms:

1. **Rename plan file** (if paused):
   ```
   feature_name.paused.md → feature_name.in_progress.md
   ```

2. **Load context from pause file**:
   - Read saved context
   - Restore understanding of state
   - Identify exact resumption point

3. **Update Development Progress**:
   ```markdown
   ### [YYYY-MM-DD HH:MM] Session: Resumed
   **Plan**: `feature_name.in_progress.md`
   **Resumed From**: [pause timestamp]
   **Next Step**: [immediate action]
   ```

4. **Delete pause context file** (after successful load):
   ```
   .claude/plans/paused_work.*.md → DELETE
   ```

5. **Present resumption summary**:
   ```markdown
   ## Work Resumed: [Plan Name]

   ### Current State
   [Description of where we are]

   ### Immediate Next Step
   [What to do now]

   ### Today's Goals
   1. [Goal 1]
   2. [Goal 2]

   Ready to continue. What would you like to focus on first?
   ```

### Step 5: Handle Ready Plans (No Paused Work)

If no paused work but ready plans exist:

```markdown
## Ready Plans Available

| # | Plan | Type | Created | Phases |
|---|------|------|---------|--------|
| 1 | [name] | Feature | [date] | [N] |
| 2 | [name] | Bug Fix | [date] | [N] |

**Which plan would you like to start?** Enter number for details.
```

When user selects:

1. **Rename plan file**:
   ```
   feature_name.ready.md → feature_name.in_progress.md
   ```

2. **Update Development Progress**:
   ```markdown
   ### [YYYY-MM-DD HH:MM] Plan Status: `feature_name`
   **Transition**: ready → in_progress
   **Reason**: Starting implementation
   **Notes**: Beginning Phase 1
   ```

3. **Present plan summary and first tasks**

### Step 6: No Work Found

If no paused or ready plans:

```markdown
## No Pending Work Found

There are no paused sessions or ready plans to resume.

### Options
1. **Create a new feature plan**: Use `/new-feature` command
2. **Investigate a bug**: Use `/fix-bug` command
3. **Run documentation audit**: Use `/document` command

Or describe what you'd like to work on, and I'll help you get started.
```

## Error Handling

### Corrupt Pause Files
If pause file cannot be parsed:
```markdown
## Warning: Pause File Corrupted

The pause file `[filename]` appears to be corrupted or malformed.

**Options**:
1. Attempt to recover from the plan file itself
2. Skip this pause file and try next
3. Delete corrupted file and start fresh

What would you like to do?
```

### Missing Plan Files
If pause file references a plan that no longer exists:
```markdown
## Warning: Referenced Plan Missing

The pause file references `[plan_name].in_progress.md` which no longer exists.

This may indicate:
- Plan was completed and moved to `completed/`
- Plan was abandoned and moved to `old/`
- File was accidentally deleted

**Options**:
1. Check `completed/` and `old/` directories
2. Delete orphan pause file
3. Recreate plan from scratch

What would you like to do?
```

## Notes

- This command prioritizes the most recent pause file if multiple exist
- Context is preserved across sessions through the pause file system
- Always verify the plan file exists before resuming
- Update `Development_Progress.md` on every resume operation
