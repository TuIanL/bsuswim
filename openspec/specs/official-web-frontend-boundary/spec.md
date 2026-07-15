# official-web-frontend-boundary Specification

## Purpose
The repository SHALL define `frontend-vue/` as the only official Web application for 智泳云枢. The removed Next.js frontend SHALL remain recoverable through Git history and archived OpenSpec records.

## Requirements

### Requirement: Single canonical Web application

The repository SHALL define `frontend-vue/` as the only official Web application for 智泳云枢.

The repository SHALL NOT contain another active root-level Web application that duplicates the Vue platform workflow.

#### Scenario: Developer identifies the official frontend

- **WHEN** a developer reviews the repository structure or maintained documentation
- **THEN** `frontend-vue/` is identified as the only supported Web application
- **AND** no second active frontend is presented as an alternative implementation

#### Scenario: Developer searches the active repository

- **WHEN** a developer searches active source directories
- **THEN** there is no tracked `frontend/` Next.js application
- **AND** historical references may remain only in archived specifications or migration history

### Requirement: Canonical frontend development commands

All maintained Web development, build, preview and deployment instructions SHALL target `frontend-vue/`.

#### Scenario: Developer starts the Web application

- **WHEN** a developer follows the README or local development guide
- **THEN** the documented commands enter `frontend-vue/`
- **AND** run the Vue/Vite development server
- **AND** do not require Next.js or React dependencies

#### Scenario: Developer creates a production build

- **WHEN** a developer runs the documented production build
- **THEN** the system runs the `frontend-vue` build
- **AND** TypeScript validation and Vite bundling complete successfully

### Requirement: Repository automation uses the canonical frontend

Startup scripts, CI workflows and deployment configuration SHALL reference only the canonical Vue frontend unless an explicitly separate future application has its own approved capability.

#### Scenario: Repository automation is inspected

- **WHEN** startup, CI, container or deployment configuration is inspected
- **THEN** no active command enters the removed `frontend/` directory
- **AND** no active command runs `next dev`, `next build` or `next start`

### Requirement: Obsolete frontend artifacts are not retained as active code

The removed Next.js frontend SHALL remain recoverable through Git history and archived OpenSpec records, but SHALL NOT be copied into another active repository directory.

#### Scenario: Legacy source is needed for reference

- **WHEN** a developer needs to inspect the previous Next.js implementation
- **THEN** they use Git history or archived OpenSpec documents
- **AND** the repository does not contain a maintained `legacy` or `archive` copy of its source tree

### Requirement: Maintained documentation matches the active architecture

README and maintained documentation SHALL describe the single Vue frontend and SHALL NOT instruct developers to preserve or run the retired Next.js prototype.

#### Scenario: New developer follows project documentation

- **WHEN** a new developer follows the repository documentation
- **THEN** they install and run only the dependencies in `frontend-vue/`
- **AND** all documentation links use repository-relative paths
- **AND** they are not directed to the retired frontend
