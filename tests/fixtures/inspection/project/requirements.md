# Export service

Requirements for the inspected service modules.

## Owner and row limit

The export function must reject a caller who is not the owner and return at most 100 rows.

## Downloadable file

An owner must receive the bounded rows as a downloadable comma-separated file.

## Password protection

When a password is supplied to the export function, the returned export must be encrypted.

## Audit view

The service modules must expose a function that returns an administrator's export audit history.

## Remote storage

The configured storage adapter must encrypt stored exports at rest. The adapter is supplied externally; its implementation is not included here.
