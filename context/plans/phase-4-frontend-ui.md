# Phase 4: Frontend UI (Week 7-8)

## Goals
- User-friendly interface for the entire flow (Analyze -> Configure -> Deploy).
- Dashboard for managing deployments.

## Tasks
- [ ] **Landing Page**
    - [ ] GitHub URL input with validation.
    - [ ] "Analyze" button triggering loading state.
- [ ] **Configuration Form**
    - [ ] Dynamic form builder (react-hook-form) based on JSON schema.
    - [ ] Secret field masking.
- [ ] **Deployment Dashboard**
    - [ ] List active deployments.
    - [ ] Show status (Running, Stopped).
    - [ ] Action buttons (Delete, Restart, Copy URL).
    - [ ] Instructions modal for connecting to Claude.

## Technical Details
- **Framework**: Next.js 15 (App Router).
- **Styling**: Tailwind CSS 4.
- **State**: React Query (for API data).
