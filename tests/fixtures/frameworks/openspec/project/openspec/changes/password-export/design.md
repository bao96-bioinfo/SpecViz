# Export design

Encrypt an export when its owner provides a password.

## Design decisions

- Keep the existing access check.
- Encrypt the file before sending it to the owner.
- Do not log passwords.

## Sources

[Export rules](specs/data-export/spec.md)
