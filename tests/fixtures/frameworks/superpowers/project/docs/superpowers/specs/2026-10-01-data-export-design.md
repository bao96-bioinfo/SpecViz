# Data export design

Provide owner-only report downloads with optional password protection.

## Goals

- Export no more than 100 rows.
- Preserve existing access controls.

## Decisions

Encrypt protected files before delivery and never log passwords.
