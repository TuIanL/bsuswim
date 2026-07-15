# swim-analysis-platform-navigation Specification

## Purpose
The official Vue frontend SHALL provide a platform shell and app-style navigation for 智泳云枢 analysis workflows, operating entirely inside the Vue application without requiring a separately deployed marketing frontend.

## Requirements
### Requirement: Dark platform shell
The official Vue frontend SHALL provide a platform shell for 智泳云枢 analysis workflows that uses the maintained dark sports-technology visual style.

The shell SHALL identify the 智泳云枢 brand as the analysis platform and SHALL not depend on a separately deployed marketing frontend.

#### Scenario: User opens a platform view
- **WHEN** a user opens any swim analysis platform view
- **THEN** the page uses black or near-black backgrounds, white primary text, muted secondary text, thin dividers, restrained status accents and compact panel styling

#### Scenario: Unauthenticated user opens the Web root
- **WHEN** an unauthenticated user opens `/` in API mode
- **THEN** the existing authentication guard may redirect the user to `/login`
- **AND** no second frontend application is used

### Requirement: App-style analysis navigation
The official Vue frontend SHALL provide app-style navigation for athletes, test sessions, multi-camera upload, analysis tasks, visual workspaces and reports.

The navigation SHALL operate entirely inside the Vue application without requiring a separate marketing frontend.

#### Scenario: Desktop platform navigation
- **WHEN** the Vue platform is viewed on a desktop viewport
- **THEN** the shell exposes navigation to athletes, test sessions, analysis tasks, visual workspaces and reports with a clear active state

#### Scenario: Mobile platform navigation
- **WHEN** the Vue platform is viewed on a mobile viewport
- **THEN** navigation remains reachable through compact controls that do not overlap content or require horizontal page scrolling

#### Scenario: Authenticated user opens the Web root
- **WHEN** an authenticated user opens `/`
- **THEN** the Vue router directs the user to the current business-platform entry
- **AND** the retired Next.js landing page is not required

#### Scenario: User returns from business workflow to analysis output
- **WHEN** a user completes or opens a training session with uploaded videos
- **THEN** the Vue application provides stable entry points to the visual workspace and report surfaces for the related analysis context

### Requirement: Domain-safe migration boundary
The platform shell SHALL avoid user-facing pickleball domain concepts.

#### Scenario: User reviews platform navigation and labels
- **WHEN** the user reads navigation labels, section labels, and primary actions
- **THEN** the system uses swim-analysis language such as video analysis, training session, stroke, keypoints, posture, rhythm, and coach feedback instead of pickleball terms such as court, rally, serve, shot, or paddle

### Requirement: Stable platform layout
The platform SHALL provide stable responsive layout frames for repeated-use analysis and business workflows.

#### Scenario: User switches platform views
- **WHEN** the user moves between login, register, athlete list, athlete profile, session creation, multi-camera upload, task management, visual workspace, report, and training views
- **THEN** the main content remains within predictable responsive page bounds and controls do not resize or shift unexpectedly

#### Scenario: User uses dense business tables and forms
- **WHEN** the user filters athlete tables, edits session forms, or uploads videos on desktop and mobile viewports
- **THEN** labels, controls, table actions, and status indicators remain readable without incoherent overlap
