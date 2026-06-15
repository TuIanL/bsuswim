## Context

The current frontend is a Next.js 14 application with Tailwind CSS, a dark minimal landing page, and componentized sections for the 智泳云枢 product story. The source pickleball project is a Vite React application with a mature sports-analysis platform: app shell navigation, local route state, upload flow, task management, job status pages, video-first analysis workspace, reports, and training recommendations.

This change ports the reusable interaction model from the pickleball project into the swim project, not the pickleball domain model. The swim project should keep its black, high-contrast, engineering-oriented design language and translate platform concepts into lane-side dual-camera swim analysis, stitched side-view video, pose keypoints, body angles, stroke rhythm, and coach feedback.

## Goals / Non-Goals

**Goals:**

- Preserve the existing 智泳云枢 landing-page visual style while adding platform-style analysis views.
- Use the current Next.js app and Tailwind setup rather than migrating to Vite or Tailwind 4.
- Adapt reusable frontend patterns from the pickleball project: platform shell, route structure, upload form, job list, job detail states, visual workspace, report views, and training loop.
- Introduce swim-specific types, demo data, local persistence keys, stage labels, and copy.
- Keep the implementation backend-ready through an analysis-client boundary, while supporting local demo behavior without a backend.
- Make every new view responsive, keyboard-reachable, and visually aligned with the existing dark sports-tech system.

**Non-Goals:**

- Do not migrate pickleball backend algorithms, court calibration, court projection, rally navigation, shot taxonomy, or paddle/hardware sensor concepts.
- Do not build the actual swim pose-analysis algorithm in this frontend change.
- Do not replace the current landing page with the old pickleball bright green visual theme.
- Do not require live backend services for the initial platform demo.

## Decisions

### Keep Next.js As The Host Application

The swim project already uses Next.js app routing, Tailwind 3, and React 18. The migration should implement the new platform views inside this structure instead of copying the Vite runtime.

Alternative considered: move the swim frontend to Vite to match the pickleball project. This would make direct copying easier but would discard working Next.js configuration and introduce needless framework churn.

### Port Patterns, Not Domain Objects

The pickleball project's structure should inform component boundaries and page flows, while the data model should be rewritten for swim analysis. For example:

- match metadata becomes training-session metadata
- court calibration becomes capture setup or dual-camera source context
- player markers become swimmer keypoints, stroke phase labels, body-line overlays, and lane-side video status
- movement and diagnosis reports become swim posture, rhythm, symmetry, and coach feedback reports

Alternative considered: keep generic names from pickleball and relabel only visible copy. That would speed initial work but would leave misleading types, storage keys, and future API contracts.

### Use A Local Demo Analysis Client First

The initial implementation should include a typed client module that can create demo/local jobs, persist them to localStorage, and return swim report payloads. The client should be shaped so future backend endpoints can replace local behavior.

Alternative considered: build only static pages. That would be visually faster but would miss the key reusable value of the old project: task state, result routing, and workflow continuity.

### Preserve The Dark Design System Across Platform Views

The platform should reuse the existing black background, white typography, muted gray copy, thin dividers, compact radii, and uppercase English labels. Interactive work surfaces may use slightly elevated dark panels and status accents, but should not import the old bright green dashboard theme wholesale.

Alternative considered: copy the pickleball platform CSS. That would make the port visually recognizable from the old app, but it conflicts with the user's request to keep the current frontend design style.

### Separate Landing Surface From Analysis Workspace

The home route should remain brand-forward and explain the system. Analysis routes should be task-oriented and denser. Navigation should connect both without forcing the marketing sections into every task workflow.

Alternative considered: fold all platform widgets into the homepage. This would overload the first page and weaken both the product story and the repeated-use analysis workflow.

## Risks / Trade-offs

- [Risk] The port may become too broad for one implementation pass. -> Mitigation: implement the reusable shell, local demo job flow, and core workspace first, then deepen reports and backend integration.
- [Risk] Old pickleball terms may leak into user-facing copy or type names. -> Mitigation: create swim-specific content and types before wiring views, and search for pickleball/court/rally/serve terms before verification.
- [Risk] Dark platform views can become visually heavy or hard to scan. -> Mitigation: use restrained panel contrast, clear spacing, stable grids, and status accents instead of large card stacks.
- [Risk] Local demo jobs may be mistaken for algorithm-backed results. -> Mitigation: every demo result and unavailable algorithm module must label its source clearly.
- [Risk] Next.js server/client boundaries can complicate localStorage-heavy flows. -> Mitigation: keep interactive platform modules as client components and isolate browser-only APIs behind client-side utilities.

## Migration Plan

1. Add swim-specific data types, demo payloads, and analysis client utilities.
2. Add platform shell/navigation while preserving the existing landing page as the home surface.
3. Port and restyle upload, task list, job status, visual workspace, report, and training views into Next.js client components.
4. Wire routes or route-like state for the platform views.
5. Add landing-page entry points to the analysis workflow.
6. Verify build, lint/type checks where available, and browser layouts across desktop and mobile.

Rollback is straightforward because the change is additive: remove the new platform routes/components and restore the previous homepage-only navigation.

## Open Questions

- Which backend base URL and endpoint shape will the future swim algorithm service use?
- Should the initial implementation use multiple Next.js routes or a single client-routed platform surface?
- Which report types should appear first in the UI: posture diagnosis, stroke rhythm, symmetry, or a combined coach summary?
