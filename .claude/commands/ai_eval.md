# AI Code Evaluation Command

## Purpose

Perform a comprehensive AI-driven code quality evaluation of the entire codebase, producing detailed reports for each major component and an executive summary prioritizing critical issues.

## Usage

```
/ai_eval
```

## Execution Steps

### Step 1: Setup

Ensure the evaluation output directory exists:

```
docs/ai_eval/
```

### Step 2: Identify Major Components

Analyze the codebase structure and identify major components. For this project, the major components are:

**Backend Components:**
1. `backend/app/api/routes/` - API Routes (cameras, observations, environment, settings, jobs)
2. `backend/app/services/camera/` - Camera Services (timelapse, capture, overlay, preview)
3. `backend/app/services/observation/` - Observation Services (lifecycle, progress, media)
4. `backend/app/services/environment/` - Environment Services (sensors, readings)
5. `backend/app/db/` - Database Layer (models, repositories, session)
6. `backend/app/core/` - Core Infrastructure (config, logging, errors)

**Frontend Components:**
7. `frontend/src/components/` - React Components
8. `frontend/src/hooks/` - Custom Hooks
9. `frontend/src/api/` - API Client Layer

### Step 3: Component Analysis

For EACH major component, spawn a quality-evaluator agent to analyze:

```
Task(
    subagent_type="general-purpose",
    prompt="""
    Perform a deep code quality analysis of [COMPONENT_PATH].

    Analyze the following aspects:

    ## 1. SOLID Principles Compliance
    - Single Responsibility: Does each class/module have one reason to change?
    - Open/Closed: Is code open for extension, closed for modification?
    - Liskov Substitution: Can subtypes replace base types?
    - Interface Segregation: Are interfaces focused and minimal?
    - Dependency Inversion: Do high-level modules depend on abstractions?

    ## 2. DRY Principle (Don't Repeat Yourself)
    - Identify duplicated code patterns
    - Suggest extraction opportunities
    - Note copy-paste code smells

    ## 3. Error Handling & Edge Cases
    - Uncaught exceptions
    - Missing error handling
    - Incomplete validation
    - Edge cases not covered

    ## 4. Race Conditions & Concurrency
    - Shared mutable state
    - Missing locks/synchronization
    - Async/await pitfalls
    - Resource contention issues

    ## 5. Design Patterns
    - Patterns used correctly
    - Anti-patterns present
    - Missing patterns that would help
    - Over-engineering concerns

    ## 6. Performance
    - N+1 query problems
    - Memory leaks
    - Inefficient algorithms
    - Blocking operations in async code

    ## 7. Complexity Metrics
    Run and report:
    - McCabe Cyclomatic Complexity (radon cc)
    - Maintainability Index (radon mi)
    - Cognitive Complexity where applicable
    - Halstead metrics if relevant

    ## 8. Code Smells
    - Long methods/functions
    - Large classes
    - Feature envy
    - Inappropriate intimacy
    - Dead code

    ## Output Format

    Create a markdown report with:
    - Executive Summary (2-3 sentences)
    - Severity ratings: CRITICAL, HIGH, MEDIUM, LOW
    - Specific file:line references
    - Recommended fixes
    - Metrics summary table

    Save report to: docs/ai_eval/[component_name].md
    """
)
```

### Step 4: Architecture Analysis

Analyze overall codebase architecture:

```
Task(
    subagent_type="general-purpose",
    prompt="""
    Analyze the overall architecture of the TimeMachine codebase.

    ## Modern Practices Assessment
    - Is the code using modern Python/TypeScript patterns?
    - Are async patterns used correctly?
    - Is type safety enforced?
    - Are dependencies up to date?

    ## Architectural Concerns
    - Separation of concerns
    - Layer boundaries respected
    - Circular dependencies
    - Module coupling analysis

    ## Foundational Design Issues
    - Scalability concerns
    - Testability issues
    - Maintainability blockers
    - Technical debt hotspots

    ## Security Review
    - Input validation
    - Authentication/authorization patterns
    - Sensitive data handling
    - Injection vulnerabilities

    Save to: docs/ai_eval/architecture_review.md
    """
)
```

### Step 5: Generate Executive Report

After all component analyses complete, create the executive summary:

```markdown
# AI Evaluation Executive Report

**Generated:** [TIMESTAMP]
**Codebase:** TimeMachine
**Components Analyzed:** [N]

## Critical Issues (Must Fix)

| # | Component | Issue | File:Line | Impact |
|---|-----------|-------|-----------|--------|
| 1 | [name] | [description] | [location] | [impact] |

## High Priority Issues

| # | Component | Issue | File:Line | Recommended Fix |
|---|-----------|-------|-----------|-----------------|

## Foundational Design Concerns

### Issue 1: [Title]
**Severity:** [CRITICAL/HIGH]
**Description:** [Details]
**Impact:** [What happens if not fixed]
**Recommendation:** [How to fix]

## Metrics Summary

| Component | MI Score | Max CC | Files | Lines | Grade |
|-----------|----------|--------|-------|-------|-------|

## Technical Debt Inventory

| Area | Debt Type | Estimated Effort | Priority |
|------|-----------|------------------|----------|

## Recommendations Priority List

1. **Immediate (This Sprint):** [List]
2. **Short-term (Next 2 Sprints):** [List]
3. **Long-term (Backlog):** [List]

## Conclusion

[2-3 paragraph summary of overall health, key concerns, and next steps]
```

Save to: `docs/ai_eval/EXECUTIVE_REPORT.md`

### Step 6: Update Index

Create/update an index file listing all reports:

```markdown
# AI Evaluation Reports Index

**Last Updated:** [TIMESTAMP]

## Reports

| Report | Component | Last Analyzed | Status |
|--------|-----------|---------------|--------|
| [EXECUTIVE_REPORT.md](EXECUTIVE_REPORT.md) | Full Codebase | [date] | [status] |
| [component.md](component.md) | [name] | [date] | [status] |

## Quick Stats

- Total Issues Found: [N]
- Critical: [N]
- High: [N]
- Medium: [N]
- Low: [N]

## How to Use These Reports

1. Start with EXECUTIVE_REPORT.md for priorities
2. Drill into component reports for details
3. Use file:line references to locate issues
4. Follow recommended fixes in order
```

Save to: `docs/ai_eval/README.md`

## Parallelization Strategy

To minimize execution time, run component analyses in parallel:

```
# Batch 1: Backend Services (parallel)
- camera services
- observation services
- environment services

# Batch 2: API & DB (parallel)
- API routes
- database layer
- core infrastructure

# Batch 3: Frontend (parallel)
- components
- hooks
- api client

# Sequential: Architecture + Executive Report
```

## Notes

- This command may take 10-15 minutes to complete fully
- Intermediate results are saved as each component completes
- Re-running updates existing reports with new timestamps
- Historical reports can be archived to `docs/ai_eval/archive/`
