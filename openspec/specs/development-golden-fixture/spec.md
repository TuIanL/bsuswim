# development-golden-fixture Specification

## Purpose

定义开发阶段 golden fixture 的可验证清单、完整性校验、显式帧映射、只读 baseline 和可重复 mutation 机制。

## Requirements

### Requirement: Golden fixture SHALL have a complete verifiable manifest
The development fixture MUST include a version, profile name, source files, expected contract files, mutation recipes, SHA-256 values, and frame mapping metadata. Every referenced path MUST exist when the fixture is loaded.

#### Scenario: Complete fixture is loaded
- **WHEN** the loader reads a complete kinematics_golden_v1 directory
- **THEN** it validates every referenced file and returns the fixture metadata without generating or modifying files

#### Scenario: Manifest references a missing file
- **WHEN** a manifest references a missing source, expected, or mutation file
- **THEN** fixture loading fails with an actionable error naming the missing path

### Requirement: Fixture integrity SHALL be checked before analysis
The loader MUST verify the declared SHA-256 for each immutable source and expected file before a golden test starts. A hash mismatch MUST fail the test and MUST NOT trigger a synthetic fallback.

#### Scenario: Source file hash changes
- **WHEN** a source video or annotation hash differs from the manifest
- **THEN** the fixture contract fails before any analysis task is created

#### Scenario: Fixture is unavailable in CI
- **WHEN** the configured fixture source cannot be downloaded or mounted
- **THEN** the job reports an explicit fixture infrastructure failure and does not report the golden test as passed

### Requirement: Frame mapping SHALL represent the observed source data
The manifest MUST use affine mapping only when all mapped intervals satisfy the declared constant offset and stride. If the observed annotation sequence contains gaps or non-constant intervals, the manifest MUST use explicit entries or a mapping representation that expresses those gaps.

#### Scenario: Constant affine mapping is valid
- **WHEN** every annotation-to-source interval matches the declared affine offset and stride
- **THEN** the loader accepts the affine mapping and marks its verification status according to the manifest

#### Scenario: Non-constant mapping is declared affine
- **WHEN** the observed intervals contain a gap or a different stride than declared
- **THEN** the fixture contract fails and reports the first inconsistent frame pair

### Requirement: Baselines SHALL be read-only during normal tests
Golden expected contracts and synthetic report baselines MUST NOT be modified by pytest, Vitest, or CI test execution. Baseline changes MUST go through an explicit candidate generation and approval command.

#### Scenario: Normal test execution completes
- **WHEN** the fixture and contract tests run
- **THEN** baseline files retain their original content and modification time

#### Scenario: Developer approves a new baseline
- **WHEN** a developer runs the explicit approval command with a change identifier or reason
- **THEN** the command writes the approved baseline and emits a structured diff of the changed contracts

### Requirement: Mutation recipes SHALL be deterministic
A mutation recipe MUST describe a reproducible transformation from the baseline annotation and MUST include the affected joint/event and frame scope. The test runner MUST generate the mutated input without maintaining an unrelated hand-edited duplicate XML.

#### Scenario: Missing-joint mutation is applied
- **WHEN** the missing-right-wrist recipe is applied to the baseline
- **THEN** every selected frame has the expected missing visibility state and all unrelated joints remain unchanged
