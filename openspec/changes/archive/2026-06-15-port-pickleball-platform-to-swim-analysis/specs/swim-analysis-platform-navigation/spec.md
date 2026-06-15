## ADDED Requirements

### Requirement: Dark platform shell
The frontend SHALL provide a platform shell for 智泳云枢 analysis workflows that preserves the existing dark sports-tech visual style.

#### Scenario: User opens a platform view
- **WHEN** a user opens any swim analysis platform view
- **THEN** the page uses black or near-black backgrounds, white primary text, muted secondary text, thin dividers, restrained status accents, and compact panel styling consistent with the existing homepage

#### Scenario: User navigates from platform back to home
- **WHEN** a user activates the 智泳云枢 brand control in the platform shell
- **THEN** the system returns to the brand/home surface without losing the platform visual language

### Requirement: App-style analysis navigation
The frontend SHALL provide app-style navigation for the swim analysis workflow while keeping the homepage entry points available.

#### Scenario: Desktop platform navigation
- **WHEN** the platform is viewed on a desktop viewport
- **THEN** the header exposes navigation to home, video analysis, reports, and training feedback with a clear active state

#### Scenario: Mobile platform navigation
- **WHEN** the platform is viewed on a mobile viewport
- **THEN** the navigation remains reachable through compact controls that do not overlap content or require horizontal page scrolling

### Requirement: Domain-safe migration boundary
The platform shell SHALL avoid user-facing pickleball domain concepts.

#### Scenario: User reviews platform navigation and labels
- **WHEN** the user reads navigation labels, section labels, and primary actions
- **THEN** the system uses swim-analysis language such as video analysis, training session, stroke, keypoints, posture, rhythm, and coach feedback instead of pickleball terms such as court, rally, serve, shot, or paddle

### Requirement: Stable platform layout
The platform SHALL provide stable responsive layout frames for repeated-use analysis workflows.

#### Scenario: User switches platform views
- **WHEN** the user moves between upload, task management, visual workspace, report, and training views
- **THEN** the main content remains within predictable responsive page bounds and controls do not resize or shift unexpectedly
