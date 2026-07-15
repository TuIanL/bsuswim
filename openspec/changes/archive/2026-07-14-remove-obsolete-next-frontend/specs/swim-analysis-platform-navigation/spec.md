## MODIFIED Requirements

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
