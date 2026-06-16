## MODIFIED Requirements

### Requirement: App-style analysis navigation
The frontend SHALL provide app-style navigation for the swim analysis workflow and Vue business workflow while keeping the homepage entry points available.

#### Scenario: Desktop platform navigation
- **WHEN** the Vue platform is viewed on a desktop viewport
- **THEN** the shell exposes navigation to athletes, test sessions, multi-camera upload, visual workspace, reports, and training feedback with a clear active state

#### Scenario: Mobile platform navigation
- **WHEN** the Vue platform is viewed on a mobile viewport
- **THEN** the navigation remains reachable through compact controls that do not overlap content or require horizontal page scrolling

#### Scenario: User returns from business workflow to analysis output
- **WHEN** a user completes or opens a training session with uploaded videos
- **THEN** the navigation provides stable entry points to the visual workspace and report surfaces for the related analysis context

### Requirement: Stable platform layout
The platform SHALL provide stable responsive layout frames for repeated-use analysis and business workflows.

#### Scenario: User switches platform views
- **WHEN** the user moves between login, register, athlete list, athlete profile, session creation, multi-camera upload, task management, visual workspace, report, and training views
- **THEN** the main content remains within predictable responsive page bounds and controls do not resize or shift unexpectedly

#### Scenario: User uses dense business tables and forms
- **WHEN** the user filters athlete tables, edits session forms, or uploads videos on desktop and mobile viewports
- **THEN** labels, controls, table actions, and status indicators remain readable without incoherent overlap
