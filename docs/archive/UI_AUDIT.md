# UI Audit

Date: 2026-05-23

Scope: full frontend pass across Overview, Architecture, Dependencies, Security, Reports, and Chat.

## Screenshots

| Surface | Evidence |
|---|---|
| Dashboard overview | `screenshots/dashboard-overview.png` |
| Architecture view | `screenshots/architecture-view.png` |
| Dependency view | `screenshots/dependency-view.png` |
| Security view | `screenshots/security-view.png` |
| Repository chat | `screenshots/repository-chat.png` |

## Findings And Fixes

| Area | Issue | Fix | Status |
|---|---|---|---|
| Tailwind/static assets | Standalone Next server did not serve static assets until `.next/static` was copied into `.next/standalone/.next/static`. | Added the production run step to README and used it for screenshot validation. | PASS |
| Architecture layout | React Flow fit occurred before async ELK layout, causing right-side nodes to clip. | Added post-layout `fitView` through `useReactFlow`. | PASS |
| Architecture abstraction | High-level architecture previously looked like implementation/file debugging. | Added Executive, Service, Module, and Implementation views with separate explanations, impact, critical services, and risk analysis. | PASS |
| Dependency graph | ELK compressed dependency nodes into a tiny unreadable strip. | Kept dependency view in a manual layered layout and reserved ELK/Dagre for architecture layouts. | PASS |
| Mermaid rendering | Chat Mermaid diagram overflowed the panel and appeared cropped. | Changed Mermaid SVG styling to fit the panel width. | PASS |
| Chat answer format | Answers rendered as raw plain text with literal Markdown markers. | Added section cards and bullet rendering for Direct Answer, Architecture Impact, Critical Files, Risks, Improvements, and Citations. | PASS |
| Visual hierarchy | Architecture page needed a stronger hero surface. | Added view briefs, service icons, hover cards, animated edges, minimap, fullscreen, search, and focus controls. | PASS |
| Dark mode | Main app surfaces now consistently use dark glass panels, subdued borders, and high-contrast foreground text. | Verified in screenshots. | PASS |
| Hydration | No hydration warnings observed during Playwright screenshot generation. | Build and browser rendering completed. | PASS |

## Quality Bar

| Check | Result |
|---|---|
| Build passes | PASS |
| No unstyled production screenshot | PASS |
| Architecture labels overlap | PASS |
| Architecture requires scrolling to understand | PASS |
| Dependency graph hairball | PASS |
| Chat Mermaid renders visually | PASS |
| Answer starts with direct answer, no reasoning preamble | PASS |

## Remaining UX Gaps

- The left repository list can become long when many benchmark runs exist. It is usable, but a future polish pass should add grouping or recent/favorite filters.
- The architecture canvas is strong on desktop. Mobile can use the same controls, but the ideal showcase viewport is desktop.
- Full visual regression tests are not yet checked into the repo; screenshots were generated manually with Playwright.

## Final UI Assessment

Current UI score: **8.4 / 10**

The product now reads as a polished local AI engineering platform rather than a prototype. The strongest surfaces are Architecture and Chat. The remaining polish work is mostly around long-history repository management and automated browser regression coverage.
