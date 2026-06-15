## 1. Frontend Project Setup

- [x] 1.1 Create a standalone `frontend/` Next.js 14 project with TypeScript, Tailwind CSS, App Router, and package scripts for development, linting, and building.
- [x] 1.2 Configure `tailwind.config.ts` with brand colors, Inter/system font stack, extended letter spacing, minimal radius defaults, and content paths.
- [x] 1.3 Configure `app/globals.css` with dark body styling, selection colors, scrollbar styling, base typography, and reusable layout utilities where appropriate.
- [x] 1.4 Add metadata in `app/layout.tsx` for 智泳云枢 and the swim-motion analysis product positioning.

## 2. Content and Section Architecture

- [x] 2.1 Create shared content data for navigation links, workflow steps, features, specifications, analysis outputs, testimonials, FAQ items, and footer links.
- [x] 2.2 Create reusable primitives for section wrappers, uppercase labels, CTA buttons, media frames, and thin divider treatments.
- [x] 2.3 Compose `app/page.tsx` from named section components instead of placing the full page in one file.

## 3. Core Page Sections

- [x] 3.1 Implement the fixed responsive `Navbar` with desktop links, CTA button, scroll-aware backdrop styling, and mobile hamburger menu.
- [x] 3.2 Implement the hero section with 智泳云枢 branding, sports-tech headline, dual-camera capture positioning, two CTA buttons, and a technical product/media visual.
- [x] 3.3 Implement the workflow section showing lane-side cart operation, above-water and underwater capture, stitching, transmission, pose recognition, and training feedback.
- [x] 3.4 Implement the feature cards for dual-view capture, lane-side motion tracking, and AI pose analysis.
- [x] 3.5 Implement the technical specifications section with a product/media frame and separated specification rows.
- [x] 3.6 Implement the analysis outputs section covering pose keypoints, body angles, stroke rhythm, symmetry cues, side-view playback, and review support.

## 4. Supporting Sections and Interactions

- [x] 4.1 Implement testimonials/trust section for coaches, teams, or sports research users.
- [x] 4.2 Implement the action-video section with a stable 16:9 placeholder frame and concise highlights.
- [x] 4.3 Implement an accessible FAQ accordion with smooth expand/collapse behavior.
- [x] 4.4 Implement the bottom CTA section and footer with product, support, social, and subscription-style content.

## 5. Responsiveness and Verification

- [x] 5.1 Verify mobile and desktop layouts for text overflow, section spacing, fixed navigation behavior, media aspect ratios, and footer wrapping.
- [x] 5.2 Run frontend lint and production build checks.
- [x] 5.3 Start the local development server and inspect the page in a browser.
- [x] 5.4 Update tasks or design notes if real media assets, final English naming, or CTA wording are decided during implementation.
