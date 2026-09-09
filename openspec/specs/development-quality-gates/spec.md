# development-quality-gates Specification

## Purpose

定义开发阶段后端测试可重复性、CI 核心质量门禁、浏览器 E2E 基础设施错误分类和 fast/full 检查命令。

## Requirements

### Requirement: Backend tests SHALL be independent of the caller working directory
The backend project MUST declare its test root, import path, and supported markers in project configuration. The documented test command MUST work from the repository root and from the backend directory.

#### Scenario: Backend tests run from repository root
- **WHEN** a developer runs the documented backend test command from the repository root
- **THEN** tests import app successfully and execute without relying on an implicit cd backend

#### Scenario: Backend tests run from backend directory
- **WHEN** the same test command is run from backend/
- **THEN** it produces the same test discovery and import behavior

### Requirement: CI SHALL execute the core development checks
The pull-request quality job MUST run backend tests, frontend Vitest, frontend type-check/build, fixture contract tests, and OpenSpec strict validation. Each check MUST produce a non-zero exit code on failure.

#### Scenario: Frontend test regression is introduced
- **WHEN** a frontend Vitest test fails
- **THEN** CI fails even if npm run build succeeds

#### Scenario: Invalid OpenSpec is introduced
- **WHEN** strict specification validation reports an error
- **THEN** the quality job fails and preserves the validator output in the job log

### Requirement: Browser E2E infrastructure failures SHALL be explicit
The Chromium/Playwright job MUST distinguish product assertion failures from missing fixture, browser, FFmpeg, database, or service startup failures. A missing dependency MUST NOT be reported as a passed E2E.

#### Scenario: Chromium is unavailable
- **WHEN** the browser cannot start
- **THEN** the job reports an infrastructure failure with the missing dependency and exits non-zero for the E2E job

#### Scenario: Product assertion fails
- **WHEN** the browser starts but page count or semantic markers are incorrect
- **THEN** the job reports a product test failure with the failing assertion

### Requirement: Test commands SHALL be documented and composable
The repository MUST document separate fast checks and full golden checks, including their working directory, required services, environment variables, and marker selection. Fast checks MUST not silently imply that browser PDF E2E has run.

#### Scenario: Developer runs fast checks
- **WHEN** a developer invokes the documented fast command
- **THEN** backend tests, frontend tests/build, and specification validation run without requiring the large video fixture

#### Scenario: Developer runs full golden checks
- **WHEN** a developer invokes the documented golden command with fixture and browser dependencies available
- **THEN** fixture contract, backend golden contract, and full-stack browser/PDF E2E run in the documented order
