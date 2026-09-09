## ADDED Requirements

### Requirement: Video and annotation uploads SHALL have independent configurable limits
The backend MUST expose separate finite configuration values for video and annotation upload sizes. The values MUST be overridable through development environment configuration and MUST be applied to the actual streamed bytes, not only the client-provided MIME type or filename.

#### Scenario: Video upload is within the configured limit
- **WHEN** the streamed video size is less than or equal to the configured video limit
- **THEN** the upload completes normally and the stored file is finalized

#### Scenario: Video upload exceeds the configured limit
- **WHEN** the streamed video size exceeds the configured video limit
- **THEN** the server stops reading, removes the partial file, and returns HTTP 413 with a stable `UPLOAD_TOO_LARGE` error code

### Requirement: Annotation upload limits SHALL apply before ingestion
The annotation limit MUST be enforced while saving the upload and before parser or ingestion work begins. A rejected annotation MUST NOT create a persistent annotation record or leave an orphaned partial file.

#### Scenario: Oversized annotation is submitted
- **WHEN** an annotation upload exceeds the configured annotation limit
- **THEN** the API returns HTTP 413, no parser is invoked, and no partial storage object remains

### Requirement: Upload limit behavior SHALL be covered by tests
Backend tests MUST cover below-limit, exact-limit, above-limit, and cleanup cases for both video and annotation uploads. Error responses MUST expose the configured limit or a stable field that allows the frontend to explain the rejection.

#### Scenario: Exact boundary upload is submitted
- **WHEN** the streamed size equals the configured limit
- **THEN** the upload is accepted and its checksum/storage metadata are persisted

#### Scenario: Partial upload is rejected
- **WHEN** a stream crosses the configured limit after writing one or more chunks
- **THEN** the partial file is absent after the request completes and the response is deterministic
