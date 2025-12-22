---
description: Quick-start feature planning with the feature-architect agent
---

# New Feature Command

## Purpose

Quick-start the feature development workflow by:
1. Gathering initial requirements
2. Invoking the feature-architect agent
3. Setting up the plan lifecycle

This is a convenience wrapper that streamlines feature planning.

## Usage

```
/new-feature [optional: brief description]
```

## Execution Steps

### Step 1: Gather Requirements

If description provided:
```markdown
## New Feature Request

**Initial Description**: [user's description]

Let me ask a few clarifying questions to ensure the plan is comprehensive.
```

If no description:
```markdown
## New Feature

What feature would you like to implement? Please describe:
1. What the feature should do
2. Who/what will use it
3. Any specific requirements or constraints
```

### Step 2: Clarification Questions

Ask targeted questions based on the feature type:

**For User-Facing Features**:
```markdown
### Feature Details

1. **User Story**: As a [user], I want to [action] so that [benefit]
2. **Acceptance Criteria**: How will we know it's working correctly?
3. **Edge Cases**: Any special scenarios to handle?
4. **Priority**: Is this blocking other work?
```

**For Technical Features**:
```markdown
### Technical Details

1. **Purpose**: What problem does this solve?
2. **Integration Points**: What existing code will this interact with?
3. **Constraints**: Any performance, memory, or compatibility requirements?
4. **Testing**: How should this be tested?
```

**For Cross-Cutting Features**:
```markdown
### Scope Details

1. **Affected Areas**: Which parts of the codebase will change?
2. **Breaking Changes**: Will this require migration or updates elsewhere?
3. **Rollout**: Can this be done incrementally?
4. **Fallback**: What if something goes wrong?
```

### Step 3: Check for Related Work

Before creating a new plan, check for related existing work:

```markdown
## Related Work Check

Searching for related plans and implementations...

### Existing Plans
| Plan | Relevance | Status |
|------|-----------|--------|
| [plan] | [why related] | [status] |

### Existing Code
| Component | Relevance |
|-----------|-----------|
| [component] | [how it relates] |

### Recommendation
[Whether to proceed with new plan or extend existing]
```

If significant overlap found:
```markdown
### Overlap Detected

The requested feature has significant overlap with `[existing_plan]`.

**Options**:
1. Extend the existing plan
2. Create a new plan that references the existing one
3. Proceed with a completely new plan

Which approach would you prefer?
```

### Step 4: Invoke Feature Architect

Pass gathered context to the feature-architect agent:

```markdown
## Initiating Feature Planning

Invoking **feature-architect** agent with:
- Feature description: [description]
- Requirements: [gathered requirements]
- Constraints: [noted constraints]
- Related work: [related items]

The architect will now analyze the codebase and create a detailed implementation plan...
```

### Step 5: Review Plan Output

When feature-architect completes:

```markdown
## Feature Plan Created

**Plan File**: `.claude/plans/[feature_name].ready.md`

### Overview
[Brief summary from plan]

### Phases
1. [Phase 1 name] - [brief description]
2. [Phase 2 name] - [brief description]
3. [Phase 3 name] - [brief description]

### Estimated Scope
- New files: [N]
- Modified files: [N]
- New tests: [N]

### Ready to Proceed?

1. **Start Implementation**: Begin with Phase 1
2. **Review Plan First**: Open the plan file for detailed review
3. **Modify Plan**: Adjust scope or approach
4. **Defer**: Save plan for later

What would you like to do?
```

### Step 6: Handle User Choice

**If Start Implementation**:
1. Rename plan: `.ready.md` → `.in_progress.md`
2. Update Development_Progress.md
3. Begin Phase 1 with appropriate developer agent

**If Review Plan**:
Present the full plan for user review.

**If Modify Plan**:
Re-engage feature-architect with modifications.

**If Defer**:
```markdown
## Plan Saved

The feature plan has been saved at:
`.claude/plans/[feature_name].ready.md`

To start implementation later:
- Run `/start-work` and select this plan
- Or open the plan file directly

Plan will remain in 'ready' status until started.
```

### Step 7: Log Creation

Add to Development_Progress.md:

```markdown
### [YYYY-MM-DD HH:MM] Plan Created: `[feature_name]`
**Command**: /new-feature
**Status**: ready
**Description**: [brief description]
**Phases**: [N]
**Notes**: [any notes]
```

## Quick Mode

For simple features, offer streamlined flow:

```markdown
## Quick Feature Mode

This appears to be a straightforward feature. Would you like to:

1. **Quick Start**: Skip detailed planning, create minimal plan and start
2. **Full Planning**: Go through complete feature-architect process

For complex features, full planning is recommended.
```

Quick Start creates a simplified plan:

```markdown
# Quick Feature: [Name]

## Objective
[What to implement]

## Tasks
- [ ] [Task 1]
- [ ] [Task 2]
- [ ] [Task 3]

## Notes
- [Constraint or consideration]

---
**Status**: ready
**Created**: [timestamp]
**Mode**: quick
```

## Error Handling

### Project Config Missing
```markdown
## Configuration Needed

No `project-config.yaml` found. The feature-architect needs to know:
- Which domains are active (embedded, python, web)?
- Any project-specific constraints?

Would you like to:
1. Create a basic project config now
2. Proceed without config (generic planning)
```

### Feature Too Vague
```markdown
## More Detail Needed

The feature description is too vague for effective planning. Please provide:
- Specific functionality desired
- Clear success criteria
- Scope boundaries (what's NOT included)

Current description: "[description]"
Clarified description:
```

## Notes

- This command is the recommended way to start new features
- It ensures proper planning before implementation
- The feature-architect agent does the heavy lifting
- All plans go through the standard lifecycle (ready → in_progress → completed)
- Use `/fix-bug` instead for bug-related work
