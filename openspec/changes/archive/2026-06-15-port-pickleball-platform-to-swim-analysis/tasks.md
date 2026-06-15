## 1. Swim Platform Foundation

- [x] 1.1 Audit the pickleball frontend components and identify the reusable interaction pieces to port into the Next.js swim frontend.
- [x] 1.2 Create swim-specific TypeScript types for analysis jobs, upload metadata, stages, visual layers, reports, diagnostics, metrics, and training recommendations.
- [x] 1.3 Create swim-specific demo data for training sessions, job summaries, visual overlays, report metrics, diagnostics, and training recommendations.
- [x] 1.4 Implement an analysis client boundary that supports local demo jobs and can later be extended for backend upload, polling, and report retrieval.
- [x] 1.5 Add localStorage keys and helpers for swim demo jobs without reusing pickleball storage names.

## 2. Platform Shell And Navigation

- [x] 2.1 Add a dark 智泳云枢 platform shell with desktop and mobile navigation for home, video analysis, reports, and training.
- [x] 2.2 Decide and implement the routing approach for platform views within the existing Next.js app.
- [x] 2.3 Ensure platform labels and actions use swim-analysis terminology and do not expose pickleball/court/rally/serve language.
- [x] 2.4 Preserve responsive layout bounds, header behavior, and active navigation states across platform views.

## 3. Swim Video Analysis Job Flow

- [x] 3.1 Build the swim video analysis entry view with file selection, session metadata, capture mode, and validation states.
- [x] 3.2 Implement demo/local analysis job creation from the upload form and route the user to task management or job status.
- [x] 3.3 Build the analysis task management view with job status, metadata, progress, updated time, and result actions.
- [x] 3.4 Build the job status/detail view for queued, processing, completed, failed, canceled, unavailable, and not-found states.
- [x] 3.5 Add swim-specific stage labels for upload, synchronization, stitching, frame sampling, pose detection, stroke segmentation, metrics, visualization, and report generation.

## 4. Swim Visual Analysis Workspace

- [x] 4.1 Port the video-first workspace pattern into a swim-specific visual analysis component.
- [x] 4.2 Replace pickleball visual concepts with lane-side direction, dual-camera capture, stitched side-view indicators, keypoints, body angles, stroke phases, rhythm ticks, and symmetry cues.
- [x] 4.3 Add layer/source states for demo, loading, available, unavailable, and limited outputs.
- [x] 4.4 Add job-aware result actions from the workspace to reports, training, task management, and details.
- [x] 4.5 Verify the workspace remains video-dominant on desktop and stacks cleanly on mobile.

## 5. Reports And Training Feedback

- [x] 5.1 Build swim report views showing session context, source clarity, summary metrics, key findings, and limited-data states.
- [x] 5.2 Add posture diagnostic cards for body line, breathing timing, hand entry, catch, kick rhythm, hip rotation, and related coach suggestions.
- [x] 5.3 Add rhythm and symmetry metrics with readable trend/progress presentation.
- [x] 5.4 Build the training feedback view with recommended drills, linked issues, practice tasks, target outcomes, and progress toward next goals.
- [x] 5.5 Ensure report and training views follow the same dark platform design language as the homepage.

## 6. Homepage Integration

- [x] 6.1 Update homepage navigation and CTA controls so users can enter the video analysis workflow.
- [x] 6.2 Keep the existing landing sections, copy hierarchy, and dark minimal visual style intact.
- [x] 6.3 Add platform-aware links from analysis output or CTA sections without turning the homepage into a dashboard.

## 7. Verification

- [x] 7.1 Search the frontend for leaked pickleball-specific terms and replace any user-facing leftovers.
- [x] 7.2 Run the available frontend lint/type/build checks and fix regressions.
- [x] 7.3 Start the local frontend and verify homepage, upload, task management, job status, visual workspace, report, and training views.
- [x] 7.4 Use browser screenshots or visual inspection on desktop and mobile to confirm text does not overlap and the dark design system is preserved.
- [x] 7.5 Confirm demo/local workflow works without backend services and clearly labels sample results.
