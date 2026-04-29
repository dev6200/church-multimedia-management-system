# Quickstart — Church Songlist Management

This guide gets a developer from a clean clone to a running stack with seeded
data and a passing test suite. It also documents the TDD inner loop and the
acceptance walk-through against the spec's user stories.

---

## 1. Prerequisites

- Docker + docker-compose (24+).
- Python 3.12 (only required if running backend tests outside the container).
- Node 20+ and `pnpm` (only required if running frontend tests outside the container).
- A Clerk **development** application:
  - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
  - `CLERK_SECRET_KEY`
  - Issuer URL (e.g., `https://<slug>.clerk.accounts.dev`)
  - At least one Google sign-in enabled.

---

## 2. Environment

Create `backend/.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://app:app@db:5432/app
CLERK_JWT_ISSUER=https://<your-slug>.clerk.accounts.dev
CLERK_JWKS_URL=https://<your-slug>.clerk.accounts.dev/.well-known/jwks.json
SUPER_ADMIN_EMAILS=you@example.org,music-director@parish.example.org
```

Create `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_BASE_URL=http://localhost:8083
```

> The `SUPER_ADMIN_EMAILS` allowlist drives FR-007: any matching email becomes
> a Super Admin on its first authenticated sign-in.

---

## 3. Bring the stack up

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

- Backend → http://localhost:8083 (FastAPI; OpenAPI at `/docs`).
- Frontend → http://localhost:3000 (Next.js).
- DB → `localhost:5432` (Postgres 16, user/db/password = `app`).

The Alembic migration creates schema, enables `pg_trgm`, and runs the seed step
populating the five Catholic Liturgical seasons (Advent, Christmas, Lent, Easter,
Ordinary Time — FR-020) and four optional-field definitions (PowerPoint link,
Sheet Music, YouTube link, Lyrics link — FR-021).

---

## 4. Run the test suites

The constitution mandates **TDD**: a feature or bug fix is not started until a
failing test exists.

### Backend

```bash
docker compose exec backend pytest                     # full suite
docker compose exec backend pytest tests/unit -q       # fast unit-only loop
docker compose exec backend pytest tests/integration   # SQLAlchemy + testcontainers
docker compose exec backend pytest tests/contract      # FastAPI HTTP contract
```

Coverage minimum: 100% pass for all tests (Constitution Workflow gate 3).

### Frontend

```bash
cd frontend
pnpm test            # vitest watch (unit + component)
pnpm test:run        # vitest one-shot for CI
pnpm e2e             # playwright; spins up the app via docker compose
```

### Lint / format / types (Workflow gates 1–2)

```bash
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec backend pyright           # or mypy
cd frontend && pnpm lint && pnpm typecheck && pnpm format:check
```

---

## 5. Acceptance walk-through (against spec user stories)

Each story below maps to its **Independent Test** in the spec and serves as a
manual smoke after each meaningful change.

### Story 1 — Browse, search, filter (P1, anonymous)

1. Without signing in, navigate to `http://localhost:3000/`.
2. Verify the catalog list renders with seeded songs (after Story 2 below seeds at least one song).
3. Type a partial title; results update within ~1s (SC-002).
4. Apply a Season filter; the list narrows (FR-024).
5. Click a song; detail view shows title, composers, populated optional links opening in a new tab (FR-025, FR-026).
6. Resize browser to 360×740 — no horizontal scroll, controls usable (FR-027, SC-007).

### Story 2 — Admin manages songs (P1)

1. Sign in via Clerk with an email **not** in `SUPER_ADMIN_EMAILS` → role = `USER`.
2. Have a Super Admin promote that user to `ADMIN` (or sign in directly with an allowlisted email — that account is `SUPER_ADMIN`, which inherits Admin powers).
3. Visit `/admin/songs/new`, create a song with only title + composer; verify it appears on `/`.
4. Edit the song to add tags + a YouTube link; reload `/` — updated values visible.
5. Attempt to create a duplicate (same title, same composer set, any case) → request rejected with `409 conflict_duplicate_song` and the conflicting song id is surfaced (FR-009).
6. As a `USER`-role account, attempt `POST /api/v1/admin/songs` directly → `403 Forbidden` (FR-004).

### Story 3 — Admin manages taxonomies + optional-field definitions (P2)

1. As Admin, visit `/admin/taxonomies/seasons`; add "Christ the King".
2. Tag an existing song with the new value; confirm public filter shows it.
3. Attempt to delete a Season currently used by ≥1 songs → `GET .../usage` returns count, UI shows confirm-and-detach dialog. Confirm detach. The Season is removed from songs but songs remain (FR-019).
4. Rename "PowerPoint link" → "Slides link". Existing values preserved on song detail under the new label (edge case in spec).

### Story 4 — Super Admin manages roles (P3)

1. Sign in as a Super Admin.
2. Visit `/super-admin/users`; promote a `USER` to `ADMIN`.
3. Sign in as that user (separate browser); confirm Admin actions now work.
4. Demote them back; refused Admin requests return `403`.
5. Try to demote yourself when you are the only Super Admin → request rejected with `400 last_super_admin` (FR-006). The UI's `RoleSelect` disables the action.

---

## 6. TDD inner loop (developer flow)

For every requirement (e.g., FR-009 unique title+composer-set):

1. **Write the failing test** at the appropriate layer:
   - Domain rule → `tests/unit/domain/test_song.py`
   - Repository SQL → `tests/integration/test_song_repository.py`
   - HTTP contract → `tests/contract/test_songs_api.py`
2. Run the suite; confirm the new test fails for the expected reason.
3. Implement the minimum code in the right layer to make it pass.
4. Refactor (preserve all green).
5. Re-run lint, format, type-check; commit.

Frontend follows the same loop with Vitest (component) and Playwright (E2E).

---

## 7. Layout cheat-sheet

```text
backend/
├── src/                         (created during implementation)
│   ├── domain/
│   │   ├── entities/            # Song, UserAccount, TaxonomyValue, ...
│   │   ├── value_objects/       # LinkUrl, ComposerName, DedupKey
│   │   └── repositories/        # ABCs (SongRepository, ...)
│   ├── application/
│   │   ├── use_cases/           # CreateSong, UpdateSong, PromoteUser, ...
│   │   └── ports/               # ClerkVerifier (ABC), Clock (ABC)
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models/          # SQLAlchemy ORM models
│   │   │   ├── repositories/    # SQLAlchemy implementations of ABCs
│   │   │   ├── unit_of_work.py
│   │   │   └── migrations/      # Alembic
│   │   ├── auth/                # PyJWT JWKS verifier impl
│   │   └── config.py            # pydantic-settings
│   └── interfaces/api/
│       ├── routers/             # FastAPI routers grouped by resource
│       ├── schemas/             # Pydantic request/response models
│       ├── deps.py              # Depends() factories
│       └── main.py              # app = FastAPI(...)
└── tests/
    ├── unit/
    ├── integration/
    └── contract/

frontend/
├── app/                         # Next.js App Router routes
│   ├── page.tsx                 # Catalog list
│   ├── songs/[id]/page.tsx      # Song detail
│   ├── admin/...                # Admin routes
│   └── super-admin/...          # Super Admin routes
├── components/
│   ├── ui/                      # ShadCN primitives
│   ├── atoms/
│   ├── molecules/
│   ├── organisms/
│   └── templates/
├── services/
│   └── api/                     # ApiClient interfaces + fetch impl + fake
├── hooks/
├── lib/
└── types/
    └── api.ts                   # Mirrors OpenAPI schemas
```

---

## 8. Common troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 unauthorized` on every admin call | Bearer token not attached | Ensure frontend awaits `getToken()` and forwards it |
| `409 conflict_version` after editing | Stale `version` in form | The `VersionConflictBanner` triggers refetch — accept and retry |
| `409 conflict_taxonomy_in_use` on delete | Detach not requested | Pass `?detach=true` after user confirms |
| Song create rejected unexpectedly | Same `dedup_key` as existing | Inspect the `conflicting_song_id` returned in the 409 body |
| Search slow / scans table | `pg_trgm` extension or GIN index missing | Re-run Alembic; verify in `\d+ songs` |
| Test DB conflicts with dev DB | testcontainers not used | Run integration tests via `pytest tests/integration` (containerised) |
