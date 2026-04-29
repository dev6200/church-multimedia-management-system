# Church Songlist Management

A single-tenant SaaS for a Catholic parish to publish and manage its song
catalog. Built as four user stories:

1. **Browse, search, and view** — anyone (signed in or not) can search the
   catalog by title or composer, filter by Season / Mass / Special Event, and
   open a song detail page on any device width from 320px upward.
2. **Admin manages the song catalog** — Admins create, edit, and delete songs.
   Title and at least one composer are required; uniqueness is enforced on the
   (title, composer set) pair, case-insensitive.
3. **Admin manages dynamic taxonomies and optional fields** — Admins add /
   rename / remove Seasons, Masses, Special Events, and the optional link
   fields a song may carry, without developer involvement. Removals of
   in-use values go through a confirm-and-detach dialog.
4. **Super Admin manages user roles** — Super Admins promote a User to Admin
   or demote an Admin back to User. Initial Super Admins are seeded by an
   email allowlist on first sign-in; the system never accepts a transition
   that would leave zero Super Admins.

Identity is delegated to **Clerk** (Google sign-in enabled inside Clerk). The
backend verifies Clerk JWTs via JWKS.

## Repository layout

- [backend/](backend/) — FastAPI + SQLAlchemy 2.x async + Alembic. Clean /
  layered architecture: `domain/` (pure-Python entities + value objects +
  repository ABCs) → `application/` (use cases + ports) → `infrastructure/`
  (SQL repositories, Alembic migrations, Clerk JWKS verifier) →
  `interfaces/api/` (FastAPI routers + Pydantic schemas).
- [frontend/](frontend/) — Next.js 16 App Router + React 19 + Tailwind v4 +
  ShadCN. Atomic-design tiers under `components/`; typed `services/api/`
  layer; Clerk middleware for auth.
- [specs/002-church-songlist-management/](specs/002-church-songlist-management/)
  — feature spec, plan, research, data model, OpenAPI contract,
  frontend-UI contract, quickstart, and the dependency-ordered task list.

## Quick start

See [the full quickstart guide](specs/002-church-songlist-management/quickstart.md)
for environment setup, bring-up, test commands, the TDD inner loop, and the
acceptance walk-through against each user story.

```bash
# 1. Configure environment
cp backend/.env.example backend/.env       # then fill in DATABASE_URL, CLERK_*, SUPER_ADMIN_EMAILS
cp frontend/.env.example frontend/.env.local  # then fill in NEXT_PUBLIC_CLERK_*, CLERK_SECRET_KEY

# 2. Bring up the stack (DB + backend + frontend)
docker compose up -d --build
docker compose exec backend alembic upgrade head

# 3. Open the catalog
# Backend: http://localhost:8083 (OpenAPI at /docs)
# Frontend: http://localhost:3000
```

## Running tests

```bash
# Backend — three tiers
docker compose exec backend pytest tests/unit -q
docker compose exec backend pytest tests/contract
docker compose exec backend pytest tests/integration   # requires Docker for testcontainers Postgres

# Frontend
cd frontend
pnpm test:run        # vitest one-shot
pnpm e2e             # Playwright (mobile / tablet / desktop projects)
```

## Project status

The implementation tracks the
[task plan](specs/002-church-songlist-management/tasks.md). Phases 1–7 ship
the full feature surface; integration tests requiring testcontainers Postgres
(T055, T084, T085, T108, T126, T141) are deferred to first execution against
a real database.
