---
description: Generate structured commit message from staged changes and TimeMachineDevelopment_Progress.md
---

You are tasked with creating a comprehensive, structured commit message for the currently staged git changes.

## Process:

1. **Analyze Staged Changes**:
   - Run `git diff --cached --stat` to see which files are staged
   - Run `git diff --cached` to see the actual changes
   - Identify the scope and nature of each change

2. **Review Development Progress**:
   - Read `TimeMachineDevelopment_Progress.md` if it exists
   - Match staged changes to relevant progress entries
   - Extract context about what was implemented and why

3. **Generate Structured Commit Message**:

   Use this format:

   ```
   ### Summary
   - work_type(scope): brief description of change
   - work_type(scope): brief description of change
   - work_type(scope): brief description of change

   ### Details:
   - Category Name
   -- Subcategory (if applicable)
   --- Specific change detail
   --- Another specific detail
   -- Another subcategory
   --- Detail here
   - Another Category
   -- Related changes grouped together
   -- Technical specifics

   Breaking Changes (if any):
   - What changed that affects existing behavior
   - Migration steps if needed
   ```

4. **Work Type Guidelines**:
   - `feat`: New features or functionality
   - `fix`: Bug fixes or corrections
   - `chore`: Maintenance, dependencies, infrastructure
   - `docs`: Documentation changes
   - `refactor`: Code restructuring without behavior change
   - `test`: Adding or updating tests

5. **Scope Guidelines**:
   - Use the component/module name (e.g., `camera`, `backend`, `frontend`, `deploy`)
   - Be specific but concise (e.g., `discovery` not `camera-discovery-service`)

6. **Detail Guidelines**:
   - Group related changes under meaningful categories
   - Use hierarchical structure with `-`, `--`, `---` for nesting
   - Include technical specifics (file names, function names, specific implementations)
   - Reference relevant entries from TimeMachineDevelopment_Progress.md
   - Focus on WHAT was done and WHY, not HOW (code explains how)

## Output:

Provide the complete commit message in a code block, ready to be used with:
```bash
git commit -F- <<'EOF'
[your generated message here]
EOF
```

Do NOT actually execute the commit - just provide the message for user review.
