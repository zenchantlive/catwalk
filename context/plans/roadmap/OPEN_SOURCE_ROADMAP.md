# Catwalk-Live: Open-Source Roadmap Revision
**Vision**: The Vercel for MCP Servers - Open-Source Demo Platform
**Last Updated**: 2025-12-20

## Executive Summary

**What Changed**: Catwalk-live is now fully open-source with a Vercel demo deployment approach. Users provide their own API keys (Fly.io, OpenRouter, etc.) instead of a monetization model.

**New Focus**:
- Developer experience and ease of self-hosting
- Bulletproof Vercel demo showcasing the platform
- Comprehensive documentation and onboarding
- Community-driven features over enterprise features

**Impact on Roadmap**: 
- Cost optimization becomes less critical (users pay their own Fly.io costs)
- Settings/key management UI becomes P0 (required for Vercel demo)
- Enterprise features deprioritized or community-driven
- Documentation and DX elevated to P0

---

## Phase 0: Settings & Key Management (NEW - IMMEDIATE PRIORITY)
**Duration**: 1-2 weeks
**Priority**: P0 (Blocking for Vercel demo)
**Goal**: Enable users to paste their own API keys in a secure settings UI

### Why This Is Critical
The Vercel demo cannot work without this - users need to provide:
- **Fly.io API Token** (for creating MCP machines)
- **OpenRouter API Key** (for Claude analysis)
- **Encryption Key** (for credential storage)

This is the "Settings" page that makes the platform self-service.

### Implementation Checklist

#### 1. Settings Storage Model
- [ ] Create `UserSettings` table (or single-row config if no auth):
  ```sql
  CREATE TABLE user_settings (
    id UUID PRIMARY KEY,
    fly_api_token TEXT,
    fly_app_name TEXT,
    openrouter_api_key TEXT,
    encryption_key TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
  );
  ```
- [ ] For MVP (no auth): Single row with id='default'
- [ ] Settings encrypted at rest (separate master key in Vercel env)

#### 2. Settings API
- [ ] `GET /api/settings` - Return settings (with secrets masked)
- [ ] `POST /api/settings` - Update settings (validate keys)
- [ ] `POST /api/settings/validate` - Test keys before saving
  - Validate Fly.io token by calling Fly API
  - Validate OpenRouter key by test API call
  - Validate encryption key format (Fernet compatible)

#### 3. Frontend Settings Page
- [ ] Create `/settings` route
- [ ] **Vercel-style .env paste UI**:
  ```
  +--------------------------------------------------+
  | Paste your .env file here:                       |
  |                                                  |
  | FLY_API_TOKEN=fo1_...                            |
  | FLY_APP_NAME=catwalk-mcp-app                     |
  | OPENROUTER_API_KEY=sk-...                        |
  | ENCRYPTION_KEY=...                               |
  |                                                  |
  +--------------------------------------------------+
  [ Parse .env ] or [ Add Keys Manually ]
  ```
- [ ] **Individual key input fields** (alternative to .env paste):
  - Fly.io API Token (with "Create token" link)
  - Fly.io App Name (with instructions)
  - OpenRouter API Key (with sign-up link)
  - Encryption Key (with "Generate" button)
- [ ] **Validation feedback**:
  - Green checkmark if key validated
  - Red X with error message if invalid
  - "Testing..." spinner during validation
- [ ] **Help text and docs links**:
  - How to get Fly.io token
  - How to create Fly.io app
  - OpenRouter signup link
  - Encryption key generation

#### 4. Key Generation Utilities
- [ ] **Frontend**: "Generate Encryption Key" button
  ```typescript
  async function generateEncryptionKey() {
    // Call backend endpoint
    const key = await fetch('/api/settings/generate-key').then(r => r.json());
    return key.encryption_key;
  }
  ```
- [ ] **Backend**: `GET /api/settings/generate-key`
  ```python
  from cryptography.fernet import Fernet
  @router.get("/settings/generate-key")
  async def generate_encryption_key():
      return {"encryption_key": Fernet.generate_key().decode()}
  ```

#### 5. Integration with Deployment Flow
- [ ] **Check settings on deployment creation**:
  - If settings incomplete, return 400 error: "Configure API keys in Settings first"
  - Frontend redirects to /settings with banner: "Add your API keys to create deployments"
- [ ] **Use user-provided keys**:
  - FlyDeploymentService uses `user_settings.fly_api_token`
  - AnalysisService uses `user_settings.openrouter_api_key`
  - EncryptionService uses `user_settings.encryption_key`

#### 6. Vercel Demo Setup Guide
- [ ] Create `/docs/vercel-demo.md`:
  - Prerequisites (Fly.io account, OpenRouter account)
  - Step-by-step setup instructions
  - Screenshot guide for getting API keys
  - Troubleshooting common issues

#### 7. Security Considerations
- [ ] Settings stored encrypted (using Vercel env master key)
- [ ] Never log API tokens
- [ ] Mask tokens in UI (show only last 4 chars)
- [ ] Clear settings on logout (if auth added later)

### Files to Create
- `backend/app/models/user_settings.py`
- `backend/app/api/settings.py`
- `backend/tests/test_settings.py`
- `frontend/app/settings/page.tsx`
- `frontend/components/EnvPaster.tsx`
- `catwalk-live/docs/vercel-demo.md`

### Success Criteria
- ✅ Users can paste .env or add keys individually
- ✅ Keys validated before saving
- ✅ Deployments use user-provided keys
- ✅ Clear error messages if keys missing/invalid
- ✅ Help text guides users through setup

---

## Revised Priority Matrix

### P0 (Must-Have for Vercel Demo)
1. **Phase 0: Settings & Key Management** (NEW) - 1-2 weeks
2. **Phase 1: Validation & Error Handling** (COMPLETE ✅)
3. **Phase 2: Health Monitoring** - 2-3 weeks
4. **Documentation & Onboarding** (NEW) - Ongoing

### P1 (Core Reliability)
5. **Phase 3: Multi-Runtime Support** - 2-3 weeks
6. **Phase 4: Container Logs** - 3-4 weeks

### P2 (Quality of Life)
7. **Frontend Polish** (NEW) - 1-2 weeks
8. **Self-Hosting Guide** (NEW) - 1 week
9. **Phase 6: Advanced Features** (Version pinning, OAuth) - Selective implementation

### P3 (Community-Driven)
10. **Phase 5: Serverless** - Nice-to-have (less critical for demo)
11. **Marketplace/Discovery** - Community can contribute
12. **Teams/Enterprise** - Future/community-driven

---

## Roadmap by Quarter

### Q1 2025 (Next 3 Months) - Foundation for Open-Source
**Goal**: Production-ready Vercel demo + self-hosting docs

**Month 1 (Jan)**: Settings & Core Reliability
- Week 1-2: **Phase 0 - Settings UI** (NEW)
  - .env paste interface
  - Key validation
  - Integration with deployment flow
- Week 3-4: **Phase 2 - Health Monitoring**
  - Background health checks
  - Status tracking
  - Progress indicators

**Month 2 (Feb)**: Multi-Runtime & Observability
- Week 1-2: **Phase 3 - Multi-Runtime**
  - Python support
  - Unified Dockerfile
  - Runtime detection
- Week 3-4: **Phase 4 - Container Logs**
  - Log collection
  - Frontend log viewer
  - Debug-friendly errors

**Month 3 (Mar)**: Polish & Documentation
- Week 1-2: **Frontend Polish** (NEW)
  - Responsive design
  - Loading states
  - Empty states
  - Error boundaries
- Week 3-4: **Documentation & Guides** (NEW)
  - Self-hosting guide
  - Vercel deployment guide
  - Architecture docs
  - Contributing guide

**Q1 Success Metrics**:
- ✅ Vercel demo deployed and public
- ✅ 95% deployment success rate
- ✅ Complete self-hosting documentation
- ✅ 5+ community contributors

---

### Q2 2025 (Months 4-6) - Community Growth
**Goal**: Community adoption + ecosystem expansion

**Month 4 (Apr)**: Advanced Features (Selective)
- Version pinning (high value)
- GitHub-only repos (high value)
- Skip: OAuth (can be community PR)

**Month 5 (May)**: Developer Experience
- One-click examples (deploy pre-configured servers)
- Template gallery (common use cases)
- Video tutorials
- Blog posts

**Month 6 (Jun)**: Community Ecosystem
- Plugin system (if needed)
- Community server showcase
- Integration guides (Claude Desktop, VS Code, etc.)
- GitHub Discussions/Discord

**Q2 Success Metrics**:
- ✅ 100+ GitHub stars
- ✅ 20+ community deployments shared
- ✅ 10+ blog posts/tutorials
- ✅ Active Discord/Discussions

---

### Q3-Q4 2025 (Months 7-12) - Platform Maturity
**Goal**: Production-grade platform + community ownership

**Areas of Focus**:
1. **Reliability & Scale**
   - Edge cases handled
   - Performance optimization
   - Monitoring and alerting
   - Incident response playbook

2. **Community Features** (prioritized by community)
   - Marketplace/discovery (if requested)
   - Teams/collaboration (if requested)
   - Advanced auth (if needed)
   - Serverless optimization (if cost becomes issue)

3. **Ecosystem Integration**
   - Official Glama.ai partnership
   - Claude Desktop preset configs
   - VS Code extension
   - MCP specification compliance

**Success Metrics**:
- ✅ 1,000+ GitHub stars
- ✅ 500+ active deployments
- ✅ 50+ community PRs merged
- ✅ Featured in Claude announcements

---

## Feature Priority Reassessment

### Elevated to P0 (Critical for Demo)
| Feature | Old Priority | New Priority | Rationale |
|---------|--------------|--------------|-----------|
| Settings UI | Not planned | P0 | Required for users to paste API keys |
| Documentation | P2 | P0 | Critical for adoption and self-hosting |
| Error Messages | P1 | P0 | Bad UX kills demos |
| Frontend Polish | Not planned | P1 | Demo quality matters |

### Deprioritized (Community-Driven)
| Feature | Old Priority | New Priority | Rationale |
|---------|--------------|--------------|-----------|
| Cost Optimization | P1 | P2 | Users pay their own Fly.io costs |
| Teams/Enterprise | Planned | P3 | Not relevant for open-source demo |
| Marketplace | Phase 7 | Community | Can be community contribution |
| OAuth Flows | Phase 6 | P3 | Nice-to-have, not critical |

### Modified Scope
| Feature | Change | Rationale |
|---------|--------|-----------|
| Phase 5 (Serverless) | Optional | Still valuable for UX, but less critical for cost |
| Phase 6 (Advanced) | Selective | Focus on version pinning + GitHub repos only |
| Multi-tenant | Removed | Single-user demo, no auth needed initially |

---

## New Phases & Focus Areas

### Phase 0: Settings & Key Management (NEW)
**See detailed plan above**

### Phase 1.5: Frontend Polish (NEW)
**Duration**: 1-2 weeks
**Priority**: P1
**Goal**: Make demo look professional

**Checklist**:
- [ ] Responsive design (mobile-friendly)
- [ ] Loading states (skeletons, spinners)
- [ ] Empty states (no deployments yet)
- [ ] Error boundaries (graceful failures)
- [ ] Animations (smooth transitions)
- [ ] Dark mode support
- [ ] Accessibility (ARIA labels, keyboard nav)

### Phase 1.6: Documentation & Onboarding (NEW)
**Duration**: Ongoing (1 week initial push)
**Priority**: P0
**Goal**: Clear path from "interested" to "deployed"

**Deliverables**:
1. **README.md**
   - What is Catwalk-live?
   - Demo link
   - Quick start (5 minutes)
   - Features
   - Architecture diagram

2. **Self-Hosting Guide** (`docs/self-hosting.md`)
   - Prerequisites
   - Fly.io setup
   - Vercel deployment
   - Environment variables
   - Troubleshooting

3. **Contributing Guide** (`CONTRIBUTING.md`)
   - Development setup
   - Code style
   - PR process
   - Roadmap participation

4. **Architecture Docs** (`docs/architecture.md`)
   - System overview
   - Data flow
   - Security model
   - Extension points

5. **Video Walkthrough** (YouTube)
   - 5-minute demo
   - Setup tutorial
   - Use case examples

---

## Success Metrics (Revised)

### 3 Months (Q1 End)
- ✅ Vercel demo live and stable
- ✅ 95% deployment success rate
- ✅ Complete self-hosting docs
- ✅ 100+ GitHub stars
- ✅ 5+ community contributors

### 6 Months (Q2 End)
- ✅ 500+ GitHub stars
- ✅ 50+ active weekly users (self-hosted + demo)
- ✅ 20+ blog posts/tutorials about catwalk
- ✅ Active community (Discord/Discussions)
- ✅ Featured in MCP ecosystem lists

### 12 Months (Year End)
- ✅ 2,000+ GitHub stars
- ✅ 500+ active deployments
- ✅ 100+ community PRs merged
- ✅ Official integration with Claude/Anthropic docs
- ✅ Top 3 MCP deployment platforms

---

## Phase Dependencies

```
Phase 0 (Settings)
  ↓
Phase 1 (Validation) ✅
  ↓
Phase 2 (Health Monitoring)
  ↓
Phase 3 (Multi-Runtime)
  ↓
Phase 4 (Container Logs)
  ↓
Phase 1.5 (Frontend Polish)
  ↓
[Vercel Demo Launch]
  ↓
Phase 1.6 (Documentation)
  ↓
Community Growth

Phase 5 (Serverless) - Optional parallel track
Phase 6 (Advanced) - Selective features, community-driven
```

---

## Open-Source Specific Considerations

### What Makes a Great Open-Source Demo?

1. **Zero Barriers to Entry**
   - One-click Vercel deploy (with .env template)
   - Clear "Get Started" CTA
   - Works immediately (no complex setup)

2. **Transparent and Trustworthy**
   - All code visible
   - Security model documented
   - No hidden costs
   - Clear data handling policies

3. **Easy to Self-Host**
   - Docker compose option
   - Railway/Render deployment guides
   - Environment variable reference
   - Migration guides

4. **Community-Friendly**
   - Good first issues labeled
   - Contributing guide
   - Code of conduct
   - Responsive to PRs

5. **Well-Documented**
   - Architecture diagrams
   - API documentation
   - Deployment guides
   - Video tutorials

### Community Engagement Strategy

1. **Launch Plan**
   - Hacker News post (Show HN)
   - Reddit (r/LocalLLaMA, r/MachineLearning)
   - Twitter/X thread
   - MCP community Discord

2. **Content Strategy**
   - Technical blog posts
   - Video tutorials
   - Use case showcases
   - Comparison with alternatives

3. **Contributor Onboarding**
   - Good first issues
   - Pair programming sessions
   - Monthly contributor calls
   - Shoutouts and credits

4. **Feedback Loops**
   - GitHub Discussions
   - Discord server
   - User surveys
   - Feature voting

---

## Immediate Next Steps (First 2 Weeks)

### Week 1: Phase 0 - Settings Backend
- [ ] Create UserSettings model and migration
- [ ] Build Settings API endpoints
- [ ] Implement key validation logic
- [ ] Add encryption key generation
- [ ] Write tests

### Week 2: Phase 0 - Settings Frontend
- [ ] Create /settings page
- [ ] Build .env paste component
- [ ] Add individual key inputs
- [ ] Implement validation UI
- [ ] Write help text and docs links
- [ ] Test end-to-end flow

### Week 3: Documentation Sprint
- [ ] Write self-hosting guide
- [ ] Create Vercel deployment guide
- [ ] Record demo video
- [ ] Update README
- [ ] Test docs with fresh users

### Week 4: Phase 2 Kickoff
- [ ] Start health monitoring implementation
- [ ] (Parallel) Continue doc improvements based on feedback

---

## Key Decisions Summary

### What Changed?
1. **No monetization** → User provides API keys
2. **Vercel demo focus** → Settings UI is P0
3. **Open-source first** → Documentation elevated to P0
4. **Community-driven** → Enterprise features deprioritized

### What Stays the Same?
1. **Technical foundation** → Phases 1-4 still core
2. **Architecture** → Fly.io + FastAPI + Next.js unchanged
3. **MCP compliance** → Streamable HTTP transport
4. **Security model** → Credential encryption unchanged

### What's New?
1. **Phase 0**: Settings & Key Management
2. **Phase 1.5**: Frontend Polish
3. **Phase 1.6**: Documentation & Onboarding
4. **Community focus**: Discord, blog posts, tutorials
5. **Self-hosting guides**: Multiple deployment options

---

## Questions for Consideration

1. **Authentication**: Do we add auth (Clerk/Auth0) or stay single-user for demo?
   - **Recommendation**: Single-user for MVP, auth as community PR later

2. **Multi-tenant**: Support multiple users or keep simple?
   - **Recommendation**: Single-tenant for demo, multi-tenant fork possible

3. **Hosting costs**: Who pays for Vercel demo backend?
   - **Recommendation**: Free tier + sponsor OR user-pays model

4. **Feature requests**: How to prioritize community requests?
   - **Recommendation**: GitHub Discussions voting + quarterly reviews

---

## Conclusion

The open-source direction fundamentally changes priorities but strengthens the project's long-term viability. By focusing on:
- **Immediate usability** (Settings UI)
- **Developer experience** (Docs, polish)
- **Community growth** (Open-source best practices)

We create a platform that can thrive as a community project while showcasing the power of MCP deployment automation.

**Next Action**: Implement Phase 0 (Settings UI) as the highest priority blocking work.
