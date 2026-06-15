## Why

The current swim frontend presents 智泳云枢 as a polished landing page, but it does not yet expose the richer video-analysis workflow needed for demos, task tracking, report review, and training feedback. The earlier pickleball project already contains a mature sports-analysis platform interaction model, so this change adapts those reusable product patterns into a swim-specific experience while preserving the current dark sports-tech visual identity.

## What Changes

- Add a swim-analysis platform shell that keeps the existing 智泳云枢 dark visual style and introduces app-style navigation for home, video analysis, reports, and training.
- Add a swim video analysis workflow adapted from the pickleball platform: upload training footage, capture swim-specific metadata, create demo/local analysis jobs, show task history, and route users into job status and result views.
- Add a swim visual-analysis workspace that reuses the video-first interaction model from the pickleball project but replaces court, rally, and shot concepts with lane-side dual-camera capture, stitched side-view playback, keypoint overlays, stroke rhythm, body angle, and symmetry cues.
- Add swim-focused report and training feedback views for posture diagnostics, stroke rhythm review, body-line issues, and coach-facing recommendations.
- Keep the existing landing-page sections and brand tone available as the home/marketing surface, with clear entry points into the new analysis platform.
- Do not migrate pickleball-specific algorithms, court calibration, rally semantics, shot taxonomy, or hardware-sweet-zone features.

## Capabilities

### New Capabilities

- `swim-analysis-platform-navigation`: Covers the platform shell, app-style navigation, route structure, and preservation of the current 智泳云枢 visual language while adding analysis-workflow entry points.
- `swim-video-analysis-job-flow`: Covers swim video upload, local/demo job creation, task management, job status states, and result routing.
- `swim-visual-analysis-workspace`: Covers the swim-specific video workspace, demo overlays, source clarity, and job-aware analysis states.
- `swim-interactive-performance-report`: Covers swim analysis reports, metrics, diagnostic evidence, and training recommendations.

### Modified Capabilities

- `zhiyong-yunshu-landing-page`: Extend the existing single-page website requirements so the homepage can link into the new platform workflow without abandoning the current dark, minimal sports-tech style.

## Impact

- Frontend architecture: expand the current Next.js app from a single landing route into a multi-view application using React state and/or Next routes.
- Components: add reusable platform shell, analysis task, upload, video workspace, report, and training components adapted from the pickleball project.
- Data model: introduce swim-specific demo data, analysis job types, metadata fields, stage labels, metrics, report schemas, and local persistence keys.
- Styling: keep Tailwind and the current black/white design system; selectively translate the pickleball platform's dense interaction patterns into the existing dark brand language.
- Backend/API: no required backend migration in this change; define an API-client boundary that can use local demo data now and later connect to a swim algorithm service.
- Verification: update local build and browser checks to cover the landing page and the new platform views on desktop and mobile.
