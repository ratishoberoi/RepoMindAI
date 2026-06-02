# RepoMindAI UX Audit

Date: 2026-06-02

Scope: live local frontend at `http://127.0.0.1:3000` backed by the FastAPI API at `http://127.0.0.1:8000`, using completed repository analysis data from the local store. This audit focused only on visual quality, usability, responsiveness, spacing, typography, overflow, and accessibility-adjacent interaction issues. No product features were added.

## Screenshots Captured

Before screenshots:

- `ux-review/before/executive.webp`
- `ux-review/before/architecture.webp`
- `ux-review/before/timeline.webp`
- `ux-review/before/portfolio.webp`
- `ux-review/before/knowledge.webp`
- `ux-review/before/security.webp`
- `ux-review/before/pr-risk.webp`
- `ux-review/before/drift.webp`
- `ux-review/before/diligence.webp`
- `ux-review/before/reports.webp`
- `ux-review/before/chat.webp`
- `ux-review/before/admin.webp`
- `ux-review/before/mobile-executive.webp`
- `ux-review/before/mobile-knowledge.webp`
- `ux-review/before/mobile-reports.webp`
- `ux-review/before/mobile-chat.webp`

After screenshots:

- `ux-review/after/executive.webp`
- `ux-review/after/architecture.webp`
- `ux-review/after/timeline.webp`
- `ux-review/after/portfolio.webp`
- `ux-review/after/knowledge.webp`
- `ux-review/after/security.webp`
- `ux-review/after/pr-risk.webp`
- `ux-review/after/drift.webp`
- `ux-review/after/diligence.webp`
- `ux-review/after/reports.webp`
- `ux-review/after/chat.webp`
- `ux-review/after/admin.webp`
- `ux-review/after/mobile-executive.webp`
- `ux-review/after/mobile-knowledge.webp`
- `ux-review/after/mobile-reports.webp`
- `ux-review/after/mobile-chat.webp`

Raw DOM audit evidence:

- `ux-review/before/audit.json`
- `ux-review/after/audit.json`

## Automated Audit Summary

| Area | Before | After |
| --- | ---: | ---: |
| Desktop small targets | 53 | 1 |
| Desktop unmanaged clipped text | 234 | 4 |
| Mobile small targets | 20 | 1 |
| Mobile unmanaged clipped text | 0 | 0 |
| Page-level horizontal overflow | 0 | 0 |
| Tiny font findings below 10px | 0 | 0 |

Remaining automated findings are the React Flow attribution link in graph canvases. It is not RepoMindAI content and does not overlap or clip application UI.

## Issues Found

### Mobile Repository Rail Consumed the First Screen

Before:

- On mobile, the repository sidebar used full viewport height and rendered long repository groups before the actual product surface.
- Users had to scroll through the rail before seeing Executive, Knowledge Graph, Reports, or Chat content.

Fix:

- Limited the rail height on mobile with an internal scroll region.
- Preserved full-height behavior on desktop.

Files:

- `frontend/components/repomind/RepositoryRail.tsx`

### Mobile Navigation Was Too Tall

Before:

- The primary navigation collapsed into a single-column list on mobile.
- This created excessive vertical distance before the active feature content.

Fix:

- Changed navigation to three columns on mobile, four on small screens, six on medium screens, and twelve on wide screens.
- Added stable minimum height and line wrapping for long labels.

Files:

- `frontend/components/RepoMindDashboard.tsx`

### Navigation Labels Were Clipped on Desktop

Before:

- Several nav items clipped combined label/eyebrow text at 1440px with the repository rail visible.
- Examples: `Architecture / flows`, `Knowledge / graph`, `Diligence / board pack`.

Fix:

- Reduced horizontal padding slightly.
- Added breakable labels and tighter line height.
- Preserved a stable button height so hover/focus states do not shift the layout.

Files:

- `frontend/components/RepoMindDashboard.tsx`

### Command Bar Could Compress on Narrow Layouts

Before:

- The command search and KPI chips competed for width.
- KPI labels could become cramped as the content column narrowed.

Fix:

- Reworked the command bar grid with `minmax` constraints.
- Made KPI chips responsive and truncation-safe.

Files:

- `frontend/components/RepoMindDashboard.tsx`

### Executive Overview Cards Were Over-Dense

Before:

- Four KPI cards were forced into a row inside the middle hero column.
- Labels such as `Architecture Health` and `Investment Readiness` clipped at common desktop widths.

Fix:

- Kept two columns until extra-wide layouts.
- Kept four columns only at `2xl`, where there is enough room.

Files:

- `frontend/components/repomind/ExecutiveOverview.tsx`

### Knowledge Graph Hero Metrics Were Too Cramped

Before:

- Five graph metric cards were forced too early.
- `Dependencies` clipped in the hero metric row.

Fix:

- Relaxed the metric grid to two, three, then five columns across breakpoints.
- Added breakable metric labels.
- Slightly widened the graph score column on desktop.

Files:

- `frontend/components/repomind/KnowledgeGraphPanel.tsx`

### Graph Canvas Was Too Tall on Mobile

Before:

- The graph canvas used the same large height on all viewports.
- On mobile it pushed the node inspector and legend too far down.

Fix:

- Added responsive graph canvas heights: shorter on mobile, larger on tablet/desktop.

Files:

- `frontend/components/repomind/KnowledgeGraphPanel.tsx`

### PR Risk Cards Were Over-Dense

Before:

- Risk, regression, GitHub evidence, dependency, API, and security panels used three columns too early.
- Metric details clipped when sentence-length evidence appeared.

Fix:

- Moved dense three-column sections to extra-wide layouts.
- Kept narrower layouts readable on common desktop widths.

Files:

- `frontend/components/repomind/RiskAndDriftCenter.tsx`

### Report and Chat Tap Targets Were Too Small

Before:

- `Open raw artifact` link and chat suggestion chips fell below comfortable tap-target height.

Fix:

- Added minimum height to the report link and suggestion chips.

Files:

- `frontend/components/repomind/ReportsCenter.tsx`
- `frontend/components/repomind/ChatExperience.tsx`

## Before vs After

| Surface | Before | After | Result |
| --- | --- | --- | --- |
| Executive | `ux-review/before/executive.webp` | `ux-review/after/executive.webp` | KPI cards no longer clip; nav is more stable. |
| Knowledge Graph | `ux-review/before/knowledge.webp` | `ux-review/after/knowledge.webp` | Hero metrics and canvas are more readable. |
| PR Risk | `ux-review/before/pr-risk.webp` | `ux-review/after/pr-risk.webp` | Risk cards no longer force cramped columns. |
| Reports | `ux-review/before/reports.webp` | `ux-review/after/reports.webp` | Report action target improved. |
| Mobile Knowledge | `ux-review/before/mobile-knowledge.webp` | `ux-review/after/mobile-knowledge.webp` | Content appears much earlier; rail and nav no longer dominate the page. |
| Mobile Chat | `ux-review/before/mobile-chat.webp` | `ux-review/after/mobile-chat.webp` | Suggestion targets and vertical flow improved. |

## Residual Risks

- React Flow attribution remains a small external link inside graph canvases. It is not overlapping product content.
- The repository rail can still contain many repeated local benchmark repositories. It is now scroll-constrained, but a future data cleanup or grouping policy would reduce visual noise further.
- The UI remains optimized primarily for desktop review workflows. Mobile is usable after this pass, but graph-heavy workflows are still naturally better on larger screens.
