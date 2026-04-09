# Password Reset Runbook

## Common failure modes

1. Email provider throttling can delay delivery of password reset emails.
2. Expired or incorrectly signed reset tokens can happen after auth-service clock drift or stale signing secrets.
3. Mobile web clients may fail if they submit an outdated CSRF token after a long-lived session.
4. Spam filtering can impact enterprise recipients when domain reputation drops.

## Triage

- Check email provider event logs for deferred or bounced sends.
- Validate auth-service clock synchronization and token TTL settings.
- Review recent deploys affecting auth, session middleware, or email templates.
- Compare failures by platform, tenant, and browser family.