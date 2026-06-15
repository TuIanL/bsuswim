## Context

The repository currently contains a swim pose engineering skeleton for MMPose-based analysis and does not include a web frontend. 智泳云枢 is a physical-plus-AI training system: a lane-side cart carries two cameras, one above water and one underwater; an operator pushes the cart alongside the swimmer; captured video is transmitted to compute equipment for stitching and pose analysis.

The frontend should communicate this system clearly to coaches, school teams, sports science evaluators, and competition reviewers. It should feel like a professional sports-technology product site, not a generic SaaS landing page or consumer camera shop.

## Goals / Non-Goals

**Goals:**

- Create an isolated `frontend/` Next.js 14 application using TypeScript and Tailwind CSS.
- Build a complete single-page website for 智泳云枢.
- Use a dark, minimal, high-contrast sports-tech visual system with uppercase English display text and Chinese explanatory copy.
- Make the first viewport immediately communicate the brand, mobile dual-camera capture system, and AI swim-motion analysis value.
- Provide page sections that explain workflow, features, specifications, analysis outputs, scenarios, FAQ, and conversion CTA.
- Keep content and assets easy to replace when real product photos/videos are available.

**Non-Goals:**

- Do not integrate live pose inference, uploaded videos, dashboards, authentication, or backend APIs.
- Do not implement ecommerce checkout, payment, or actual preorder flows.
- Do not alter existing Python/MMPose training or data-processing code.
- Do not require real product media at first; placeholders are acceptable when styled as intentional product mockups.

## Decisions

1. **Place frontend in `frontend/`**

   The website will live in an isolated Next.js project under `frontend/` so Node dependencies, package scripts, and Tailwind configuration do not collide with the existing Python environment.

   Alternative considered: placing app files at the repository root. This would make frontend commands shorter but would mix package metadata with the training project skeleton.

2. **Use Next.js App Router with mostly server components**

   The page can be rendered as a static marketing page. Interactive pieces such as mobile navigation and FAQ accordion can be small client components, while the rest can remain simple React components.

   Alternative considered: Vite + React. Vite is lighter, but the user requested Next.js 14 and the App Router gives a conventional project shape for future product pages.

3. **Use Tailwind theme tokens for the visual system**

   Brand colors, letter spacing, font family, and border radius constraints will be centralized in `tailwind.config.ts` and `globals.css`. Components should use these tokens rather than ad hoc colors.

   Alternative considered: bespoke CSS modules for each section. That would work, but Tailwind is faster for a single-page responsive site and matches the requested stack.

4. **Use structured sections rather than one large page component**

   The page will compose named components such as `Navbar`, `Hero`, `SystemFlow`, `Features`, `Specs`, `AnalysisOutputs`, `Testimonials`, `ActionVideo`, `FAQ`, `CTA`, and `Footer`.

   Alternative considered: putting all markup in `app/page.tsx`. That is quicker initially but makes content tuning and future section replacement harder.

5. **Represent product media with deliberate placeholders**

   Until real cart, camera, pool, or demo videos exist in the repo, the implementation can use stylized dark product panels, CSS/canvas-like visual treatments, local placeholders, or safe external placeholders. Media containers must preserve final layout dimensions and be easy to swap.

   Alternative considered: searching for stock swimming photos. Stock photos risk misrepresenting the real hardware and can make the site feel less like an original product.

## Risks / Trade-offs

- **Risk: The site looks like a generic sports gadget rather than 智泳云枢.** -> Mitigate by foregrounding the lane-side cart, dual-camera capture, stitched side-view video, and AI pose-analysis workflow in the hero and system-flow sections.
- **Risk: Placeholder media weakens credibility.** -> Mitigate by making placeholders technical and schematic rather than pretending they are real product photography.
- **Risk: Chinese brand name with uppercase English styling feels inconsistent.** -> Mitigate by using 智泳云枢 as the primary brand mark and uppercase English for eyebrow labels, section headings, and technical categories.
- **Risk: Overusing dark monochrome creates a flat page.** -> Mitigate with restrained contrast, thin dividers, video/product frames, swim-lane line motifs, and measured accent glow on interactive states.
- **Risk: Mobile layout becomes text-heavy.** -> Mitigate by prioritizing concise section copy, single-column stacking, stable media aspect ratios, and compact navigation.

## Migration Plan

1. Scaffold the `frontend/` application.
2. Add Tailwind/global styling and shared content data.
3. Build page sections incrementally.
4. Run lint/build checks.
5. Start the local dev server and verify desktop and mobile layouts in the browser.

Rollback is straightforward: remove or ignore the `frontend/` directory because no existing backend or training code is modified.

## Open Questions

- What final English support name should accompany 智泳云枢: `SMARTSWIM AXIS`, `SWIMCLOUD AXIS`, or another name?
- Will the first version use real pool/cart media, a generated technical mockup, or a purely schematic visual?
- Should CTA copy target competition/demo review (`REQUEST DEMO`) or customer acquisition (`BOOK A FIELD TEST`)?
