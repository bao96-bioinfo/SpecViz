# Export changes

Requested password protection for report exports.

## MODIFIED Requirements

### Requirement: Export report
The system SHALL allow report owners to export up to 100 rows as a comma-separated file and request optional password protection.

#### Scenario: Download a protected report
- **WHEN** the owner requests password protection
- **THEN** the exported file is encrypted and contains at most 100 rows
