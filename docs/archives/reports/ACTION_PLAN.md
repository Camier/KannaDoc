# Action Plan: Layra Project Improvements

## Phase 1: Project Organization & Hygiene (Completed)
- [x] **Root Cleanup**: Consolidated specialized docker files into `deploy/`.
- [x] **Docs Consolidation**: Moved non-essential Markdown files to `docs/`.
- [x] **Baseline Testing**: All 22 backend tests passed (including security checks).

## Phase 2: Security & Maintenance
- [x] **Security Audit**: `verify_password_legacy` is isolated. Deadline confirmed for 2026-02-23.
- [ ] **Dependency Audit**: Check for outdated packages (optional).

## Phase 3: Frontend Modernization (In Progress)
- [x] **Test Infrastructure**: Installed Vitest, React Testing Library.
- [x] **Baseline Testing**: Created and passed unit tests for `utils/date` and `stores/authStore`.
- [ ] **E2E Testing**: Setup Playwright (Next step).
- [ ] **Component Tests**: Add tests for critical UI components.