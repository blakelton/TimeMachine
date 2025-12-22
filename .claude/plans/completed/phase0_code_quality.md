# Phase 0: Code Quality Remediation

> Resolve all HIGH priority issues before adding new features

**Status**: ready
**Created**: 2025-12-21
**Parent**: [masterplan.md](masterplan.md)

---

## Objective

The codebase currently has a B+ grade with 0 CRITICAL and 7 HIGH issues. Before adding new features, we need to resolve all HIGH issues to ensure a stable foundation for future development.

## Prerequisites

- None (start immediately)

## Deliverables

### 1. Fix Backend Type Issues

**Issue**: Type mismatch in stats_broadcaster.py (lines 29-34)
**Impact**: WebSocket clients may error on unexpected data types

**Tasks**:
- [ ] Review stats_broadcaster.py:29-34
- [ ] Identify the type mismatch
- [ ] Fix type annotations and/or data transformations
- [ ] Add appropriate type guards
- [ ] Verify with mypy

**Files**: `backend/app/services/stats_broadcaster.py`

---

### 2. Fix Hardcoded URLs

**Issue**: Hardcoded localhost URLs in AuthContext.tsx (lines 27, 61)
**Impact**: Authentication fails in production deployment

**Tasks**:
- [ ] Review AuthContext.tsx:27,61
- [ ] Replace hardcoded URLs with relative paths or config-based URLs
- [ ] Use the existing API_BASE_URL constant
- [ ] Test in both development and production builds

**Files**: `frontend/src/contexts/AuthContext.tsx`

---

### 3. Add Error Boundary

**Issue**: Missing Error Boundary in App.tsx
**Impact**: Unhandled errors crash the entire application

**Tasks**:
- [ ] Create ErrorBoundary component
- [ ] Wrap main app content with ErrorBoundary
- [ ] Design fallback UI for error state
- [ ] Add error reporting/logging
- [ ] Test with intentional error

**Files**:
- `frontend/src/components/ErrorBoundary.tsx` (new)
- `frontend/src/App.tsx`

---

### 4. Create Constants Module

**Issue**: Magic numbers throughout codebase
**Impact**: Hard to maintain, easy to introduce inconsistencies

**Tasks**:
- [ ] Audit codebase for magic numbers (timeouts, intervals, limits)
- [ ] Create `backend/app/core/constants.py`
- [ ] Create `frontend/src/constants.ts`
- [ ] Replace magic numbers with named constants
- [ ] Document each constant's purpose

**Files**:
- `backend/app/core/constants.py` (new)
- `frontend/src/constants.ts` (new)
- Multiple files with replacements

**Common magic numbers to extract**:
- WebSocket reconnect intervals
- Polling intervals
- Timeout values
- Buffer sizes
- UI dimensions/limits

---

### 5. Extract Shared Utilities

**Issue**: Duplicate formatDate functions in 5+ files
**Impact**: Inconsistent formatting, maintenance burden

**Tasks**:
- [ ] Identify all duplicate utility functions
- [ ] Create `frontend/src/utils/formatters.ts`
- [ ] Consolidate formatDate and similar functions
- [ ] Update all imports
- [ ] Consider i18n implications

**Files**:
- `frontend/src/utils/formatters.ts` (new)
- All files with duplicate utilities

---

### 6. Refactor cameras.py Router

**Issue**: Large cameras.py router at 1138 lines
**Impact**: Hard to navigate, test, and maintain

**Tasks**:
- [ ] Analyze current structure
- [ ] Plan split into logical sub-routers:
  - `cameras_crud.py` - CRUD operations
  - `cameras_preview.py` - Preview operations
  - `cameras_recording.py` - Recording operations
  - `cameras_timelapse.py` - Timelapse operations
- [ ] Create sub-router files
- [ ] Move endpoints to appropriate files
- [ ] Update main router to include sub-routers
- [ ] Verify all endpoints still work

**Files**:
- `backend/app/api/routes/cameras.py`
- `backend/app/api/routes/cameras/` (new directory)

---

### 7. Fix Direct fetch() Calls

**Issue**: Direct fetch() bypasses auth in multiple files
**Impact**: Auth context not respected, inconsistent error handling

**Tasks**:
- [ ] Audit for direct fetch() usage
- [ ] Create/enhance API client with auth handling
- [ ] Replace direct fetch() with API client calls
- [ ] Ensure consistent error handling

**Files**: Multiple frontend files

---

## Testing Requirements

After all changes:
- [ ] Run `mypy backend/` with no errors
- [ ] Run `npm run build` with no TypeScript errors
- [ ] Run existing tests (`pytest`, `npm run test`)
- [ ] Manual smoke test of all major features:
  - [ ] Home dashboard loads
  - [ ] Camera preview works
  - [ ] Recording starts/stops
  - [ ] Timelapse works
  - [ ] File browser works
  - [ ] Settings save

## Quality Gate

- [ ] Run quality evaluator
- [ ] Verify 0 CRITICAL issues
- [ ] Verify 0 HIGH issues
- [ ] Document any deferred MEDIUM/LOW issues

## Success Criteria

1. Quality grade improves to A- or better
2. No HIGH priority issues remain
3. All existing functionality still works
4. Code is more maintainable and navigable

## Notes

- Work through issues in order (dependencies are minimal)
- Each issue can be a separate commit
- If an issue is more complex than expected, document and adjust scope

---

**Estimated Effort**: 1-2 days
**Dependencies**: None
**Blocks**: Phase 1, Phase 3
