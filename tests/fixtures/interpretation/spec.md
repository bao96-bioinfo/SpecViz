# Secure report export

## Goals

People can export their reports without exposing another person's data.

## Rules

- Never include another person's report, even if its identifier is supplied.
- An export must finish within 30 seconds, except encrypted exports, which may take up to 90 seconds.
- Reject inputs larger than 10 megabytes before starting export creation.
- Password protection is optional. If chosen, a password must contain at least 12 characters.
- When input is invalid, explain the problem and do not create a partial download.
- Role-based access control is described as RBAC in supporting notes; expand it in explanatory labels.

## Open question

Should encrypted exports expire after one day? This has not been decided.
