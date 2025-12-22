---
description: Quick-start bug investigation with the root-cause-analyzer agent
---

# Fix Bug Command

## Purpose

Quick-start the bug investigation and fix workflow by:
1. Gathering bug details and symptoms
2. Invoking the root-cause-analyzer agent
3. Setting up the investigation plan
4. Facilitating the fix workflow

This is a convenience wrapper that streamlines bug resolution.

## Usage

```
/fix-bug [optional: brief description or error message]
```

## Execution Steps

### Step 1: Gather Bug Details

If description provided:
```markdown
## Bug Report

**Initial Description**: [user's description]

Let me gather more details to ensure thorough investigation.
```

If no description:
```markdown
## Bug Report

Please describe the bug:
1. What is happening? (Actual behavior)
2. What should happen? (Expected behavior)
3. How can it be reproduced?
```

### Step 2: Collect Symptoms

Ask targeted questions based on bug type:

**For Runtime Errors**:
```markdown
### Error Details

1. **Error Message**: [exact error text]
2. **Stack Trace**: [if available]
3. **When It Occurs**: [trigger conditions]
4. **Frequency**: [always / sometimes / rare]
5. **Environment**: [where it happens]
```

**For Behavioral Bugs**:
```markdown
### Behavior Details

1. **Steps to Reproduce**:
   1. [Step 1]
   2. [Step 2]
   3. [Step 3]

2. **Actual Result**: [what happens]
3. **Expected Result**: [what should happen]
4. **Started When**: [when first noticed / after what change]
5. **Workaround**: [if any]
```

**For Performance Issues**:
```markdown
### Performance Details

1. **Symptom**: [slow / high memory / high CPU / etc.]
2. **When**: [always / specific conditions]
3. **Metrics**: [any numbers - response time, memory usage, etc.]
4. **Comparison**: [was it better before? when?]
5. **Impact**: [how severe]
```

**For Embedded/Hardware Bugs**:
```markdown
### Hardware Context

1. **Hardware State**: [board state, connections, etc.]
2. **Logs**: [serial output, debug logs]
3. **Timing**: [when in boot sequence, during operation]
4. **Reproducibility**: [hardware reset required? specific sequence?]
5. **Environment**: [temperature, power source, etc.]
```

### Step 3: Collect Available Evidence

Request relevant artifacts:

```markdown
## Evidence Collection

Please provide any available:

### Logs
- [ ] Error logs
- [ ] Application logs
- [ ] System logs

### Context
- [ ] Recent code changes (git log)
- [ ] Configuration changes
- [ ] Environment changes

### Reproduction
- [ ] Steps to reproduce
- [ ] Test case (if exists)
- [ ] Sample data causing issue
```

### Step 4: Check for Related Issues

Search for related bugs or fixes:

```markdown
## Related Issues Check

Searching for related bugs and fixes...

### Similar Bug Reports
| Plan | Similarity | Status | Relevant? |
|------|------------|--------|-----------|
| bug_[name].md | [description] | [status] | [yes/no] |

### Recent Fixes in Area
| Commit/Change | Area | Date |
|---------------|------|------|
| [change] | [area] | [date] |

### Known Issues
| Issue | Status | Related? |
|-------|--------|----------|
| [issue] | [status] | [assessment] |
```

If related bug found:
```markdown
### Related Bug Detected

This appears related to `bug_[name]`:
- [How they're related]
- [Whether it might be the same issue]
- [Whether the previous fix applies]

**Options**:
1. Investigate as new issue (might be different root cause)
2. Re-open related bug (if fix was incomplete)
3. Mark as duplicate of existing issue

Which approach?
```

### Step 5: Invoke Root Cause Analyzer

Pass gathered context to the root-cause-analyzer agent:

```markdown
## Initiating Bug Investigation

Invoking **root-cause-analyzer** agent with:
- Symptom: [main symptom]
- Error: [error message if any]
- Reproduction: [steps]
- Context: [gathered context]
- Evidence: [available evidence]

The analyzer will now investigate possible causes...
```

### Step 6: Review Analysis Output

When root-cause-analyzer completes:

```markdown
## Root Cause Analysis Complete

**Analysis File**: `.claude/plans/bug_[name].ready.md`

### Summary
[Brief summary of findings]

### Most Likely Cause (Probability: [X]%)
[Description of most likely cause]

### Alternative Causes
1. [Cause 2] - [X]%
2. [Cause 3] - [X]%

### Recommended Fix
[High-level fix approach]

### Next Steps

1. **Proceed with Fix**: Implement recommended fix
2. **Review Full Analysis**: See detailed report
3. **Investigate Further**: Gather more evidence
4. **Different Approach**: Try alternative cause

What would you like to do?
```

### Step 7: Handle User Choice

**If Proceed with Fix**:
1. Rename plan: `.ready.md` → `.in_progress.md`
2. Update Development_Progress.md
3. Invoke appropriate developer agent with fix context

**If Review Analysis**:
Present the full analysis for user review.

**If Investigate Further**:
List what additional evidence would help narrow down the cause.

**If Different Approach**:
Re-analyze focusing on alternative hypothesis.

### Step 8: Fix Workflow

When proceeding with fix:

```markdown
## Implementing Fix

### Fix Strategy
[Description of fix approach]

### Files to Modify
| File | Change |
|------|--------|
| [file] | [what to change] |

### Invoking Developer

Passing to **[domain]-developer** agent:
- Analysis: `bug_[name].in_progress.md`
- Focus: [specific cause to address]
- Validation: [how to verify fix]
```

After fix implemented:

```markdown
## Fix Implemented

### Changes Made
| File | Changes |
|------|---------|
| [file] | [changes] |

### Verification

Please verify the fix:
1. [Verification step 1]
2. [Verification step 2]
3. [Verification step 3]

Does the bug appear to be fixed?
- **Yes**: Mark as completed
- **No**: Investigate further
- **Partially**: Identify remaining symptoms
```

### Step 9: Completion

When fix verified:

```markdown
## Bug Fixed

### Resolution
[Brief description of what was wrong and how it was fixed]

### Plan Status
- Moved: `bug_[name].in_progress.md` → `completed/bug_[name].md`

### Prevention
[Recommendations to prevent similar bugs]

### Documentation
- Updated Development_Progress.md
- Added to completed plans
```

Log completion:

```markdown
### [YYYY-MM-DD HH:MM] Bug Fixed: `[bug_name]`
**Root Cause**: [brief description]
**Fix**: [brief description of fix]
**Files Changed**: [list]
**Verified**: Yes
```

## Quick Fix Mode

For obvious bugs with clear fixes:

```markdown
## Quick Fix Mode

This appears to be a straightforward bug. Would you like to:

1. **Quick Fix**: Skip analysis, apply obvious fix directly
2. **Full Analysis**: Go through complete root-cause-analyzer process

Quick fix is appropriate for:
- Obvious typos or mistakes
- Clear logic errors
- Simple configuration issues

Full analysis is recommended for:
- Intermittent bugs
- Complex interactions
- Performance issues
- Memory/concurrency problems
```

## Error Handling

### Cannot Reproduce
```markdown
## Reproduction Issue

Unable to reproduce the bug with provided information.

This could mean:
1. Missing reproduction steps
2. Environment-specific issue
3. Intermittent/timing bug
4. Already fixed

Would you like to:
1. Provide more detailed reproduction steps
2. Investigate as intermittent issue
3. Check if recent changes might have fixed it
4. Set up monitoring to catch next occurrence
```

### Multiple Possible Causes
```markdown
## Ambiguous Root Cause

The analysis identified multiple equally likely causes:

| Cause | Probability | Test to Differentiate |
|-------|-------------|----------------------|
| [cause1] | [X]% | [test] |
| [cause2] | [X]% | [test] |

Recommendation: Run differentiating tests before implementing fix.

Would you like to:
1. Investigate [cause1] first
2. Investigate [cause2] first
3. Run tests to differentiate
```

## Notes

- This command is the recommended way to investigate bugs
- Always use root-cause-analyzer before implementing fixes
- Avoid "try things and see" approach - analyze first
- Quality evaluation is still mandatory after fix implementation
- Document prevention recommendations for similar bugs
