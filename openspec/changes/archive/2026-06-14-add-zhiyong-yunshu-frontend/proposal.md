## Why

The project needs a public-facing product website for 智泳云枢 that can explain the hardware capture workflow, AI pose analysis value, and training scenarios to coaches, teams, and evaluators. The current repository is focused on the swim pose engineering skeleton and has no frontend experience for presenting the system.

## What Changes

- Add a standalone Next.js 14 + TypeScript + Tailwind CSS frontend under `frontend/`.
- Create a responsive single-page product website for 智泳云枢 with a black, minimal, sports-tech visual direction.
- Present the system story around lane-side mobile capture, above-water and underwater dual cameras, stitched side-view video, transmission to compute equipment, and AI pose analysis.
- Include the expected page sections: fixed navigation, hero, system flow, core features, technical specifications, analysis outputs, trust/testimonials, action video placeholder, FAQ, CTA, and footer.
- Configure global Tailwind theme tokens for the dark brand palette, uppercase typographic style, spacing, and minimal-radius controls.

## Capabilities

### New Capabilities

- `zhiyong-yunshu-landing-page`: Defines the branded single-page website experience, required content sections, responsive behavior, and visual style for 智泳云枢.

### Modified Capabilities

- None.

## Impact

- Adds a new `frontend/` application without changing the existing Python/MMPose project structure.
- Adds Node/Next.js dependencies for the frontend only.
- Does not introduce backend APIs, data persistence, authentication, or model inference integration in this change.
- No breaking changes to existing training, annotation, weights, or output workflows.
