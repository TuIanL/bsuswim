## MODIFIED Requirements

### Requirement: Branded single-page structure
The frontend SHALL provide a responsive single-page website for 智泳云枢 that presents the system as a mobile dual-camera swim-motion capture and AI pose-analysis product, and SHALL provide clear entry points into the swim analysis platform workflow when that workflow is available.

#### Scenario: Visitor opens the homepage
- **WHEN** a visitor loads the frontend homepage
- **THEN** the page presents the 智泳云枢 brand and a complete single-page landing experience with navigation, hero, system workflow, features, specifications, analysis outputs, trust/testimonials, video showcase, FAQ, CTA, footer sections, and an obvious path into video analysis

### Requirement: Fixed responsive navigation
The frontend SHALL include a fixed top navigation bar with the 智泳云枢 brand, centered section links on desktop, a right-side analysis CTA, scroll-aware translucent background styling, and a mobile hamburger menu.

#### Scenario: Desktop navigation
- **WHEN** the homepage is viewed on a desktop viewport
- **THEN** the navigation displays the brand on the left, section links in the center, and a CTA button that can open the swim video analysis workflow on the right

#### Scenario: Mobile navigation
- **WHEN** the homepage is viewed on a mobile viewport
- **THEN** the navigation replaces centered links with a hamburger menu that can reveal the section links and keeps the analysis workflow entry reachable without layout overlap
