# GATEPREP Backend Architecture Rules

## Layer Dependency Rules

```
endpoints -> services, schemas, api/deps
services   -> repositories, schemas, core, integrations
repositories -> core/db only
integrations -> external APIs only
bootstrap  -> startup seed/migration orchestration
schemas    -> no app logic
core       -> no domain imports
```

## Hard Bans

- No `db.collection` calls in routes or services
- No endpoint imports from `app.repositories.*` or `app.integrations.*`
- No endpoint access to `request.app.state.db`
- No business rules in repositories
- No route-local schemas unless temporary during migration
- No user-owned query without `user_id`
- No duplicated ID/time/auth/config helpers
- No legacy `/api/admin/*` routes
- No `is_admin`
- No `difficulty`

## Auth Rule

Auth provider details must stay behind auth services/integrations.
No route should know whether auth is legacy Google or Supabase.
Drive and YouTube OAuth are separate integration flows and must not depend on
Supabase provider tokens.

## Directory Layout

```
app/
  main.py
  api/
    deps.py          — get_current_user, rate limiter
    providers.py     — Depends-wired service/repo providers
    responses.py     — ok(), err()
    endpoints/       — one per domain
  core/
    config.py        — Pydantic Settings
    db.py            — Motor client + db handle
    security.py      — intentionally no password implementation while Supabase owns email auth
    time.py          — now_utc(), iso()
    ids.py           — new_id()
    constants.py     — app-wide constants
    logging.py       — structured logger
  schemas/           — canonical Pydantic models
  services/          — business logic (orchestration)
  repositories/      — MongoDB access only
  integrations/      — external API clients
  bootstrap/         — startup seed data and migrations
```

## Frontend Data Rule

Frontend pages should not grow new ad hoc `api.get/post` calls. Add or reuse:

```
api/endpoints/*      — request wrappers
features/*/hooks/*   — React Query hooks and invalidation
types/api.ts         — shared response/entity types during incremental TypeScript migration
```

Question Bank and PYQs keep their existing UX and data model while their calls
move behind endpoint wrappers/hooks incrementally.
