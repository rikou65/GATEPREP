# Contributing to GATE Study OS

First off — thanks for taking the time to contribute. This project is opinionated about a few things and relaxed about most. This document tells you which is which.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting set up](#getting-set-up)
- [Project conventions](#project-conventions)
- [Branching & commits](#branching--commits)
- [Pull request checklist](#pull-request-checklist)
- [Testing](#testing)
- [Architectural rules of thumb](#architectural-rules-of-thumb)
- [Reporting bugs](#reporting-bugs)
- [Proposing features](#proposing-features)

---

## Code of Conduct

Be kind. Assume good faith. Critique code, not people. That's the whole policy.

---

## Getting set up

See [`README.md`](./README.md#local-development) for the quick start. Two extra things contributors should do:

1. **Read [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md)** — it explains what's being built, in what order, and why. If your PR conflicts with the active phase, talk to the maintainer first.
2. **Read [`memory/PRD.md`](./memory/PRD.md)** — the living product spec. It's the source of truth for *what* the product is.

Recommended tooling:
- Python **3.11+** with `venv` or `uv`
- Node **20+** with `yarn` (do **not** use `npm` — CRA toolchain breakage)
- A MongoDB instance (local Docker is fine: `docker run -d -p 27017:27017 mongo:7`)
- VS Code with the official Python, ESLint, and Tailwind CSS IntelliSense extensions

---

## Project conventions

### Frontend (React)

- **Components:** functional only, no class components.
- **Exports:** *named* exports for components (`export const QuestionViewer = ...`), *default* exports for pages (`export default function DashboardPage()`).
- **Styling:** Tailwind utility-first. Reach for `@apply` only when a class string crosses ~8 utilities or appears in 3+ places.
- **Components library:** use the existing shadcn primitives in `frontend/src/components/ui/` before adding new dependencies.
- **Forms:** `react-hook-form` + `zod` resolvers. No raw `useState` form blobs in new code.
- **Icons:** `lucide-react` only. No emoji-as-icons. No FontAwesome unless coordinated.
- **API calls:** import the shared axios instance from `lib/api.js` — it already wires auth and base URL.
- **Routing:** `react-router-dom` v7. Use `<Outlet>` for nested layouts.
- **Test IDs:** **every interactive element gets a `data-testid`**, kebab-case, describing the function not the style:
  ```jsx
  <Button data-testid="question-submit-button" onClick={onSubmit}>Submit</Button>
  ```

### Backend (FastAPI)

- **Schemas:** Pydantic v2, defined at the top of the route module or in `schemas/` (post-refactor).
- **Route handlers:** thin. Business logic lives in helpers/services. If a handler is > 30 lines, extract.
- **Timestamps:** always `datetime.now(timezone.utc)`. Never `datetime.utcnow()` (deprecated, naive).
- **ObjectId:** never returned raw. Convert to `str` in response models.
- **Multi-tenancy:** every database query that touches a user-owned collection **must** filter by `user_id`. No exceptions. Code review will reject otherwise.
- **Errors:** raise `HTTPException` with explicit status + detail. Don't return `{"error": "..."}` from a 200.
- **Env vars:** read via `os.environ.get('FOO')`. Never hardcode defaults for secrets/URLs — let it fail fast.

### Both

- **No dead code.** Don't leave commented-out blocks "in case we need them". Git remembers.
- **No backwards-compat shims** for code that hasn't shipped externally yet. Just change it.
- **No over-engineering.** Helpers for one-time logic, abstractions for hypothetical futures — both rejected.

---

## Branching & commits

### Branches
- `main` — always deployable.
- `feat/<short-slug>` — new features.
- `fix/<short-slug>` — bug fixes.
- `refactor/<short-slug>` — internal restructures with no behaviour change.
- `chore/<short-slug>` — deps, tooling, docs.

### Commits — Conventional Commits

```
<type>(<optional-scope>): <imperative summary>

<optional body explaining *why*, not *what*>
```

Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `style`, `test`, `chore`.

Examples:
- `feat(ocr): extract questions from PDF via Gemini`
- `fix(pdf-viewer): prevent re-download on modal reopen`
- `refactor(server): split drive routes into services/drive.py`
- `docs: add IMPLEMENTATION_PLAN.md`

Keep the summary ≤ 72 chars, imperative ("add" not "added"), no trailing period.

---

## Pull request checklist

Before opening a PR:

- [ ] Branch is up to date with `main` (rebase, don't merge).
- [ ] All new code follows the conventions above.
- [ ] Tests added/updated for any behaviour change.
- [ ] `pytest` passes locally: `cd backend && pytest -v`.
- [ ] Frontend lints clean: `cd frontend && yarn lint` (if configured) or no new warnings in `yarn start`.
- [ ] If UI changed → screenshot in the PR description.
- [ ] If new env var introduced → added to both `.env.example` files **and** to the env table in `README.md`.
- [ ] If auth credentials changed → `memory/test_credentials.md` updated.
- [ ] `PRD.md` / `CHANGELOG.md` updated if applicable.
- [ ] Works in **Chrome, Firefox, and Brave** (Brave is our third-party-cookie canary — Drive features must be tested there).

PR description template:

```markdown
## What
One-sentence summary.

## Why
The user-facing or technical motivation.

## How
Bullet points of the approach. Mention any non-obvious decisions.

## Screenshots
(if UI)

## Testing
What you tested and how.

## Checklist
- [ ] Tests pass
- [ ] Docs updated
- [ ] Tested in Brave (if Drive-related)
```

---

## Testing

### Backend

```bash
cd backend
pytest -v                          # full suite
pytest -v tests/test_gate_os_backend.py::test_attempt_records  # single test
pytest -v -k "drive"               # by keyword
pytest --cov=. --cov-report=html   # coverage (output in htmlcov/)
```

Write tests in `backend/tests/`. Pattern: one test file per route module. Use `pytest` fixtures for db setup and authenticated client.

### Frontend

For now, no Jest unit suite. We rely on:
1. The screenshot/e2e testing tooling for flows.
2. Manual QA across Chrome, Firefox, Brave.

If you add component tests, use `@testing-library/react` — colocated as `Component.test.jsx`.

### What to test
- **Always:** new API endpoints (happy path + at least one error path).
- **Always:** complex business logic (scoring, scheduling, duplicate detection).
- **Sometimes:** UI components — only if they encode non-trivial logic (forms with validation, the canvas PDF viewer).
- **Never:** trivial CRUD that's already covered by Pydantic + the route framework.

---

## Architectural rules of thumb

These are the patterns that keep this codebase boring (in a good way):

1. **`/api` prefix on every backend route.** Non-negotiable — the Kubernetes ingress depends on it.
2. **`REACT_APP_BACKEND_URL` for every frontend → backend call.** No hardcoded URLs, ever.
3. **Drive files belong to the user.** We use `drive.file` scope. Never request broader scopes.
4. **PYQs and Questions are separate collections.** Don't unify them. See README → Engineering Notes for the reasoning.
5. **No combined "subject completion %".** Per-topic Solved/Remaining/Accuracy only.
6. **Solutions render inline, never in a modal.**
7. **The PDF viewer uses `pdfjs-dist` on a canvas.** Don't replace it with a Drive iframe; Brave will break it.
8. **The PDF modal uses a React Portal.** Don't change the mount point.
9. **`is None` is the correct PEP-8 idiom.** The linter occasionally flags it. Ignore the linter, follow PEP-8.
10. **`server.py` stays monolithic until ~2k LOC.** See `IMPLEMENTATION_PLAN.md` § Phase 9.

---

## Reporting bugs

Open an issue with:

- **Environment:** Browser + OS, frontend host, backend host.
- **Steps to reproduce:** numbered, deterministic.
- **Expected vs actual:** what should happen vs what does.
- **Screenshots / video:** if visual.
- **Console + network logs:** for frontend issues.
- **Backend logs:** for 5xx errors — `tail -n 100 /var/log/supervisor/backend.*.log` in the dev pod.
- **Reproducible on Brave?** Important for Drive-related issues.

---

## Proposing features

1. Skim [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) — it may already be on the roadmap.
2. Open an issue titled `[Feature] <one-line summary>`.
3. Include:
   - **User story:** "As a <user>, I want <action>, so that <outcome>."
   - **Why it matters:** signal, not vibes.
   - **Out-of-scope:** what you're explicitly not asking for.
   - **Rough sketch:** screens, API shape, anything visual helps.
4. Wait for a 👍 from the maintainer before starting work — saves you from building something we won't merge.

---

## Questions?

Open a Discussion or ping the maintainer. The worst question is the one you didn't ask while you were stuck for two hours.

Happy hacking. 🎯
