---
description: Audit plans, sync documentation, and clean up stale files
---

# Document Command

## Purpose

Comprehensive project maintenance and documentation audit. This command:
- Validates all plans for relevance and accuracy
- Syncs documentation with actual code changes
- Cleans up obsolete or superseded plans
- Updates the development progress log

## Execution Steps

### Phase 1: Plan Discovery

Locate all plans across the project:

```markdown
## Plan Inventory

### Active Plans
| File | Status | Created | Last Modified |
|------|--------|---------|---------------|
| [name].ready.md | Ready | [date] | [date] |
| [name].in_progress.md | In Progress | [date] | [date] |
| [name].paused.md | Paused | [date] | [date] |

### Completed Plans
| File | Completed | Summary |
|------|-----------|---------|
| completed/[name].md | [date] | [brief] |

### Archived/Old Plans
| File | Status | Reason |
|------|--------|--------|
| old/[name].md | Deprecated | [why] |
```

### Phase 2: Plan Validation

For each active plan (ready, in_progress, paused), validate:

#### 2.1 Superseded Check
Compare against completed plans and other active plans:
- Is this plan superseded by a newer plan?
- Has this work been done under a different name?
- Is there significant overlap with another plan?

If superseded:
```markdown
### Plan Superseded: `[plan_name]`

**Reason**: [Explanation]
**Superseded By**: `[other_plan_name]`

**Action**: Move to `old/` with notation
```

#### 2.2 Validity Check
Verify the plan is still relevant:

**For Bug Plans**:
- Is the bug still present?
- Has it been fixed elsewhere?
- Is the root cause analysis still valid?

**For Feature Plans**:
- Is the feature still needed?
- Has the requirement changed?
- Is the approach still valid?

**For Refactor Plans**:
- Is the refactor still needed?
- Has the code changed significantly?
- Is the approach still applicable?

If invalid:
```markdown
### Plan Invalid: `[plan_name]`

**Reason**: [Explanation]
**Evidence**: [What showed it's invalid]

**Action**: Move to `old/` with notation
```

#### 2.3 Accuracy Check
For valid plans, verify accuracy:
- File paths still correct?
- Interfaces/APIs unchanged?
- Dependencies still valid?

If needs update:
```markdown
### Plan Needs Update: `[plan_name]`

**Issues**:
- [Issue 1]
- [Issue 2]

**Action**: Update plan with current information
```

### Phase 3: Code-to-Documentation Sync

#### 3.1 Scan Recent Changes

Check git history (if available) for recent changes:
```bash
git log --since="2 weeks ago" --oneline
git diff HEAD~20 --stat
```

Identify:
- New files created
- Significant modifications
- Deleted/moved files
- New features/fixes

#### 3.2 Identify Undocumented Changes

For each significant change, check if it's documented:
- Is there a corresponding plan in `completed/`?
- Is it mentioned in `Development_Progress.md`?
- Is relevant documentation updated?

Undocumented changes:
```markdown
### Undocumented Changes Found

| Change | Files | Plan | Progress Log |
|--------|-------|------|--------------|
| [description] | [files] | Missing | Missing |
| [description] | [files] | Found | Missing |
```

#### 3.3 Update Documentation

For undocumented changes, add to `Development_Progress.md`:

```markdown
### [YYYY-MM-DD HH:MM] Unplanned Change: `[description]`
**Type**: Bug Fix | Feature | Refactor | Config | Documentation
**Files Affected**: [list]
**Reason**: Discovered during /document audit
**Impact**: [what changed]
**Notes**: [context]
```

### Phase 4: README/CLAUDE.md Sync

Check for documentation that needs updating:

#### 4.1 CLAUDE.md Review
- Are workflows still accurate?
- Are agent descriptions current?
- Do commands match actual usage?

#### 4.2 README Review (if exists)
- Does it reflect current functionality?
- Are setup instructions current?
- Are examples still valid?

If updates needed:
```markdown
### Documentation Updates Needed

| File | Section | Issue | Suggested Fix |
|------|---------|-------|---------------|
| CLAUDE.md | Agents | New agent not listed | Add [agent] |
| README.md | Setup | Outdated command | Change [x] to [y] |
```

### Phase 5: Development Progress Sync

Ensure `Development_Progress.md` is current:

- All plan status changes logged
- No missing entries for completed work
- Timestamps accurate
- No orphaned references

If gaps found:
```markdown
### Progress Log Gaps

| Gap | Type | Suggested Entry |
|-----|------|-----------------|
| [date range] | Missing plan completion | [suggested entry] |
| [plan] | Status change not logged | [suggested entry] |
```

### Phase 6: Generate Summary Report

```markdown
# Documentation Audit Report

**Date**: [timestamp]
**Auditor**: /document command

## Summary

| Category | Count | Action Taken |
|----------|-------|--------------|
| Plans Validated | [N] | - |
| Plans Superseded | [N] | Moved to old/ |
| Plans Invalid | [N] | Moved to old/ |
| Plans Updated | [N] | Content updated |
| Undocumented Changes | [N] | Logged in progress |
| Docs Updated | [N] | [list] |

## Plans Moved to old/

| Plan | Reason |
|------|--------|
| [plan] | [reason] |

## Plans Updated

| Plan | Updates |
|------|---------|
| [plan] | [what changed] |

## Undocumented Work Logged

| Change | Type | Files |
|--------|------|-------|
| [change] | [type] | [files] |

## Documentation Updates

| File | Updates |
|------|---------|
| [file] | [what updated] |

## Recommendations

### Immediate Actions
1. [Action needed]
2. [Action needed]

### Future Improvements
1. [Suggestion]
2. [Suggestion]

## Integrity Check

- [x] All active plans validated
- [x] No orphaned pause files
- [x] Progress log current
- [x] Documentation synced

---
**Audit completed at [timestamp]**
```

### Phase 7: Update Progress Log

Log this audit:

```markdown
### [YYYY-MM-DD HH:MM] Documentation Audit
**Command**: /document
**Plans Reviewed**: [N]
**Plans Moved**: [N] to old/
**Changes Documented**: [N]
**Docs Updated**: [list or "None"]
**Report**: See `.claude/reports/audit_YYYY-MM-DD.md`
```

## Optional: Save Full Report

If significant findings, save report to:
```
.claude/reports/audit_YYYY-MM-DD_HHMM.md
```

## Notes

- Run this command periodically (weekly/bi-weekly) to maintain hygiene
- This is a read-heavy operation - minimal writes except for:
  - Moving superseded/invalid plans
  - Updating progress log
  - Fixing documentation
- Always get user confirmation before moving plans to old/
- The audit helps prevent "plan rot" where old plans become obstacles
