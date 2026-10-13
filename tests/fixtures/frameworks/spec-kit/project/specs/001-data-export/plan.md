# Export design

Implement owner-only downloads and optional password protection.

## Design decisions

- Verify report ownership before reading its rows.
- Limit exports to 100 rows.
- Encrypt protected files before sending them.

[Requirements](spec.md)
