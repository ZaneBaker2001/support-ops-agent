# SSO Redirect Loop Postmortem

## Summary

A redirect loop affected SAML login flows after a reverse proxy configuration change.

## Signals

- Increased login retries
- Elevated auth error rates
- Session lookup instability during a Redis latency event

## Actions taken

- Rolled back proxy header change
- Increased session diagnostics
- Added dashboard alerts for auth redirect loops