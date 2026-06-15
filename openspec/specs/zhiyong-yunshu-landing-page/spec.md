# zhiyong-yunshu-landing-page Specification

## Purpose
TBD - created by archiving change add-zhiyong-yunshu-frontend. Update Purpose after archive.
## Requirements
### Requirement: Branded single-page structure
The frontend SHALL provide a responsive single-page website for 智泳云枢 that presents the system as a mobile dual-camera swim-motion capture and AI pose-analysis product, and SHALL provide clear entry points into the swim analysis platform workflow when that workflow is available.

#### Scenario: Visitor opens the homepage
- **WHEN** a visitor loads the frontend homepage
- **THEN** the page presents the 智泳云枢 brand and a complete single-page landing experience with navigation, hero, system workflow, features, specifications, analysis outputs, trust/testimonials, video showcase, FAQ, CTA, footer sections, and an obvious path into video analysis

### Requirement: Sports-tech visual style
The frontend SHALL use a dark, minimal sports-technology visual style with black background, white primary text, muted gray secondary text, thin dividers, minimal border radius, and uppercase English display labels.

#### Scenario: Page is visually inspected
- **WHEN** the homepage is viewed on desktop or mobile
- **THEN** the dominant visual system uses black/dark backgrounds, high-contrast typography, restrained white/gray accents, and no rounded card-heavy or colorful marketing layout

### Requirement: Fixed responsive navigation
The frontend SHALL include a fixed top navigation bar with the 智泳云枢 brand, centered section links on desktop, a right-side analysis CTA, scroll-aware translucent background styling, and a mobile hamburger menu.

#### Scenario: Desktop navigation
- **WHEN** the homepage is viewed on a desktop viewport
- **THEN** the navigation displays the brand on the left, section links in the center, and a CTA button that can open the swim video analysis workflow on the right

#### Scenario: Mobile navigation
- **WHEN** the homepage is viewed on a mobile viewport
- **THEN** the navigation replaces centered links with a hamburger menu that can reveal the section links and keeps the analysis workflow entry reachable without layout overlap

### Requirement: Hero explains the product in the first viewport
The frontend SHALL use the hero section to communicate 智泳云枢, the lane-side mobile capture cart, above-water and underwater dual-camera capture, stitched side-view swim video, and AI pose-analysis value.

#### Scenario: Visitor reads the hero
- **WHEN** a visitor views the first viewport
- **THEN** they can understand that 智泳云枢 captures swimmers from above and below the water using a mobile lane-side system and turns the footage into analyzable motion data

### Requirement: System workflow section
The frontend SHALL include a workflow section that explains the capture-to-analysis pipeline from lane-side cart operation through dual-camera recording, video stitching, data transmission, pose recognition, and coach-facing feedback.

#### Scenario: Visitor reviews workflow
- **WHEN** a visitor reaches the workflow section
- **THEN** the page shows the ordered system flow from mobile capture to AI analysis and training feedback

### Requirement: Feature and specification sections
The frontend SHALL include feature cards and technical specifications that describe dual-view capture, lane-side motion tracking, AI pose analysis, capture views, video output, deployment context, compute equipment, and target users.

#### Scenario: Visitor compares system capabilities
- **WHEN** a visitor reviews the features and specifications
- **THEN** they can identify the main hardware/software capabilities and understand the system is intended for coaches, teams, and sports research contexts

### Requirement: Analysis output section
The frontend SHALL describe the intended analysis outputs, including pose keypoints, body angles, stroke rhythm, symmetry cues, side-view playback, and training review support.

#### Scenario: Visitor evaluates analysis value
- **WHEN** a visitor reads the analysis output section
- **THEN** they can understand what kinds of swim-technique information the system is meant to surface from captured video

### Requirement: FAQ accordion
The frontend SHALL include a FAQ accordion with smooth expand/collapse behavior covering deployment, waterproof capture, operator workflow, compute-device connection, supported analysis, and future media replacement.

#### Scenario: Visitor expands a FAQ item
- **WHEN** a visitor selects a FAQ question
- **THEN** the answer expands smoothly and presents readable muted text without disrupting the surrounding layout

### Requirement: Responsive and accessible interaction basics
The frontend SHALL support mobile-first responsive layouts, keyboard-reachable interactive controls, readable color contrast, stable media aspect ratios, and text that does not overflow or overlap its containers.

#### Scenario: Layout is checked across viewport sizes
- **WHEN** the homepage is viewed on mobile and desktop viewports
- **THEN** navigation, buttons, cards, media placeholders, FAQ content, and footer content remain readable and do not overlap

### Requirement: Local verification
The frontend SHALL provide scripts that allow developers to run linting, create a production build, and start a local development server for browser verification.

#### Scenario: Developer verifies the frontend
- **WHEN** a developer runs the documented frontend scripts
- **THEN** the app can be linted, built, and previewed locally without requiring backend services

