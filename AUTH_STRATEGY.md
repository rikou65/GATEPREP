# GATEPREP — Drive & YouTube OAuth Strategy with Supabase Auth

## 1. Purpose

Define how Google Drive and YouTube OAuth authorization work after login identity
moves to Supabase Auth. Drive/YouTube access must remain functional, secure, and
independent of the login provider.

## 2. Core Principle

| Concern | Provider / Layer | Responsibility |
|---|---|---|
| Login identity | Supabase Auth | Verify user, issue JWT |
| App business logic | FastAPI | Orchestrate data and integrations |
| App data storage | MongoDB | Store users, questions, playlists, tokens |
| Drive file access | Google Drive OAuth tokens | Authorize Drive file access |
| YouTube data access | Google YouTube OAuth tokens | Authorize YouTube data access |

**Critical rule:** Supabase Google provider tokens are **never** used for Drive or
YouTube access. They may lack the correct scopes or refresh tokens.

## 3. Auth Boundaries

### 3.1 FastAPI Dependency: `get_current_user`

Resolves any authenticated request to an internal `user_id` without exposing
auth provider details to routes.

Accepted credentials:
- Legacy session cookie (temporary, during transition)
- Supabase JWT via `Authorization: Bearer ...`

Returns:

```python
CurrentUser(
    user_id="internal-uuid",
    email="user@example.com",
    auth_provider="supabase"
)
```

### 3.2 User Document in MongoDB

```python
class User(BaseModel):
    user_id: str
    auth_provider: Literal["supabase", "legacy_google"]
    supabase_user_id: str | None
    email: str
    name: str | None
    picture: str | None
    legacy_google_id: str | None
    email_verified: bool
    created_at: datetime
    updated_at: datetime
```

Indexes:
- `supabase_user_id` — unique, sparse
- `email` — unique, sparse
- `legacy_google_id` — sparse

## 4. Drive & YouTube OAuth Flow

### 4.1 Authorization Is Explicit

Drive and YouTube authorization are user-initiated actions, not login side
effects.

1. User logs in via Supabase (email/password or Google provider).
2. User clicks **Connect Google Drive** or **Connect YouTube** in Settings.
3. FastAPI generates a signed, single-use OAuth state record tied to `user_id`.
4. Browser redirects to Google OAuth consent screen.
5. Google redirects to FastAPI callback.
6. FastAPI resolves `user_id` from the state record, exchanges code for tokens,
   and stores them.
7. FastAPI redirects back to frontend Settings page.

### 4.2 Drive Authorization Flow

```
Frontend Settings
       |
       |-- POST /api/drive/connect-url
       |   Authorization: Bearer <supabase-token>
       |
       v
    FastAPI
       |
       |-- verify Supabase JWT -> user_id
       |-- create OAuth state record (state_id, user_id, expires_at)
       |-- build Google OAuth URL with state
       |
       |-- 200 { url: "https://accounts.google.com/o/oauth2/..." }
       |
       v
    Frontend redirects browser to Google
       |
       v
    Google consent screen
       |
       v
    Browser redirected to /api/drive/callback?state=...&code=...
       |
       v
    FastAPI
       |
       |-- resolve user_id from state record
       |-- exchange code for tokens
       |-- encrypt and store tokens by user_id
       |-- redirect to FRONTEND_URL/settings?drive=connected
```

### 4.3 YouTube Authorization Flow

Identical pattern via `/api/youtube/connect-url` and `/api/youtube/callback`.

### 4.4 Scopes

- **Drive:** `https://www.googleapis.com/auth/drive.file`
- **YouTube:** `https://www.googleapis.com/auth/youtube.readonly`

## 5. Token Storage

### 5.1 Drive Tokens Collection

```python
class DriveToken(BaseModel):
    user_id: str
    refresh_token: str        # encrypted
    access_token: str | None  # encrypted, or null and generated on demand
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

### 5.2 YouTube Tokens Collection

Same shape, stored separately.

### 5.3 Encryption

All stored Google tokens are encrypted at rest using Fernet:

```
TOKEN_ENCRYPTION_KEY=<32-byte-base64-fernet-key>
```

Access tokens may be generated on demand and discarded rather than stored. If
stored, they must also be encrypted.

### 5.4 No Client Secrets in Token Documents

Google `client_id` and `client_secret` are application-level credentials. They
live **only** in environment variables and `app/core/config.py`. They are
**never** stored per-user.

## 6. OAuth Callback Identity Resolution

**Rule:** OAuth callbacks resolve `user_id` from the signed OAuth `state`
record, **not** from a Supabase JWT.

Reason: Google redirects the browser to the callback. The browser request cannot
reliably include an `Authorization: Bearer ...` header. The state record created
during `/connect-url` is the secure, single-use, expiring token that binds the
callback to the internal `user_id`.

## 7. Connection Status

### 7.1 Endpoints

- `GET /api/drive/status` → `{ connected: bool, sync_needed: bool }`
- `GET /api/youtube/status` → `{ connected: bool }`

### 7.2 Settings UI

- Supabase account info
- Drive: status + Connect / Disconnect
- YouTube: status + Connect / Disconnect
- Logout

Disconnect removes the token document for the current user. App data is
preserved.

## 8. User Migration from Legacy Google Login

### 8.1 Auto-Link by Verified Email

On first Supabase login:

1. Supabase returns `supabase_user_id` and `email`.
2. FastAPI only auto-links if Supabase reports the email as **verified**.
3. If a matching user exists by email:
   - Attach `supabase_user_id`
   - Set `auth_provider = "supabase"`
   - Preserve `user_id`
   - Preserve Drive/YouTube tokens
4. If no match:
   - Create new user with fresh `user_id`

### 8.2 Legacy Fallback

Keep legacy Google login routes temporarily:
- `GET /api/auth/google-url`
- `GET /api/auth/callback`
- `POST /api/auth/session`
- `GET /api/auth/me`

They resolve to the same internal `user_id`.

Remove legacy routes only after:
- Supabase login verified in production
- Existing users migrated
- Drive/YouTube connections verified after Supabase login

## 9. Dual-Auth Session Strategy

During transition, `get_current_user` accepts both:

```python
async def get_current_user(
    legacy_session: str | None = Cookie(None, alias="session"),
    authorization: str | None = Header(None),
) -> CurrentUser:
    if legacy_session:
        return await resolve_legacy_session(legacy_session)
    if authorization and authorization.startswith("Bearer "):
        return await resolve_supabase_jwt(authorization.removeprefix("Bearer "))
    raise HTTPException(401)
```

Both paths return `CurrentUser(user_id=..., email=..., auth_provider=...)`.

## 10. Dev Login

- Dev-login remains available **only** when `ENVIRONMENT=development`.
- It returns an internal `user_id` through the same `get_current_user` interface.
- It is **disabled in production**.

## 11. Frontend Auth Flow

1. Frontend logs in via Supabase client.
2. Supabase manages session refresh, password reset, email verification, logout.
3. Frontend sends Supabase access token in `Authorization: Bearer ...` on every
   FastAPI call.
4. FastAPI verifies token and resolves to internal `user_id`.

## 12. Security Considerations

- Never use Supabase Google provider tokens for Drive/YouTube.
- Encrypt all stored Google tokens.
- OAuth callbacks identify users via signed state records only.
- State records are single-use and expire quickly.
- Rate-limit auth endpoints by IP and user_id.
- Production cookies must be secure / samesite.
- Never expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend.
- Auto-link legacy users only on verified Supabase emails.

## 13. Environment Variables

### Frontend

```env
VITE_BACKEND_URL=http://localhost:8001
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

### Backend

```env
# MongoDB
MONGO_URL=mongodb://localhost:27017
DB_NAME=gateprep

# Supabase
SUPABASE_URL=
SUPABASE_JWT_SECRET=         # for symmetric JWT verification
SUPABASE_JWKS_URL=           # for JWKS verification
SUPABASE_SERVICE_ROLE_KEY=   # only for backend admin Supabase API calls

# Google OAuth
GOOGLE_DRIVE_CLIENT_ID=
GOOGLE_DRIVE_CLIENT_SECRET=
GOOGLE_DRIVE_REDIRECT_URI=http://localhost:8001/api/drive/callback
GOOGLE_YOUTUBE_CLIENT_ID=
GOOGLE_YOUTUBE_CLIENT_SECRET=
GOOGLE_YOUTUBE_REDIRECT_URI=http://localhost:8001/api/youtube/callback

# Token Encryption
TOKEN_ENCRYPTION_KEY=

# Legacy + General
JWT_SECRET=                  # legacy only; remove after Supabase fully replaces auth
FRONTEND_URL=http://localhost:3000
YOUTUBE_API_KEY=
MISTRAL_API_KEY=
ENVIRONMENT=development
```

## 14. Regression Test Checklist

- [ ] Legacy session cookie still authenticates
- [x] Supabase JWT authenticates
- [x] Drive `/connect-url` works with Supabase token
- [x] Drive callback resolves user from state, not JWT
- [ ] Drive refresh token is encrypted
- [x] YouTube `/connect-url` works with Supabase token
- [x] YouTube callback resolves user from state, not JWT
- [ ] YouTube refresh token is encrypted
- [x] Supabase email/password user can connect Drive/YouTube
- [x] Supabase Google provider user can connect Drive/YouTube
- [x] Legacy user auto-linked by verified email keeps same `user_id` and tokens
- [ ] Unverified Supabase email does not auto-link
- [ ] Disconnect removes only current user's token document
- [x] Resource streaming still works
- [x] YouTube playlist import still works
- [ ] Dev-login only works in development
