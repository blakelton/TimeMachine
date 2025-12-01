Resume previously paused work by loading saved context and continuing where you left off.

**Actions to perform:**

1. **Search for paused work** (in priority order):
   - Look for `.codex/plans/paused_work.*.md` files (newest first)
   - Look for `.codex/plans/*.paused.md` plan files (newest first)
   - Look for any `.codex/plans/*.in_progress.md` files (if no paused work found)

2. **If multiple paused items found**:
   - Read all pause documentation and paused plan files
   - Present list to user with:
     - Index number
     - Feature/bug name
     - Timestamp of pause
     - Work type
     - Progress summary (e.g., "Phase 2 of 3 - 60% complete")
     - Status (e.g., "1 HIGH issue needs fixing")
   - Ask: "Multiple paused work items found. Which would you like to resume? [1/2/3]"
   - Wait for user selection

3. **If single paused item found**:
   - Read pause documentation thoroughly
   - Present detailed summary to user:
     - What was being worked on
     - Last progress state
     - Tasks completed
     - Current task and progress
     - Files modified
     - Pending issues
     - What's next
   - Ask confirmation: "Would you like to resume this work? [Y/n]"
   - Wait for user response

4. **If no paused work found**:
   - Search for any `.in_progress.md` plans
   - If found: Present list and ask if user wants to resume any
   - If none: Say "No paused work found. What would you like to work on?"

5. **Resume work** (after user confirmation):
   - If resuming from plan file:
     - Rename: `feature_name.paused.md` → `feature_name.in_progress.md`
   - Archive pause documentation:
     - Rename: `paused_work.YYYY-MM-DD_HH-MM-SS.md` → `paused_work.resumed.YYYY-MM-DD_HH-MM-SS.md`
   - Load full context into working memory
   - Review "Next Actions" section from pause documentation
   - Continue from documented next actions
   - If there were pending CRITICAL/HIGH issues, address those first

6. **Present resumption plan**:
   - Show user what will happen next based on pause documentation
   - Execute the next actions sequentially

**Example presentation format:**

```
Resuming **[Feature/Bug Name]**

Last Session Summary:
- Completed: [List completed tasks]
- In Progress: [Current task description] - [X%] complete
- Files Modified: [List files with line ranges]
- Pending: [Any CRITICAL/HIGH issues that need attention]

Next Actions:
1. [First action from pause doc]
2. [Second action from pause doc]
3. [Third action from pause doc]

Would you like to continue with this work? [Y/n]
```
