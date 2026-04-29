# Phase 0 Research: Catholic Church Songlist Management SaaS

**Feature**: `002-church-songlist-management`
**Date**: 2026-04-28
**Status**: Complete — all NEEDS CLARIFICATION resolved

This document consolidates the technical decisions that resolve every NEEDS CLARIFICATION raised in the Technical Context section of `plan.md`. Each entry follows the format **Decision / Rationale / Alternatives considered**.

---

## 1. Backend language & runtime

- **Decision**: Python 3.12 (matches existing `backend/Dockerfile` `python:3.12-slim`).
- **Rationale**: Already pinned by the repository; supports modern type hints (`X | None`), `match` statements, and is a current LTS-class CPython.
- **Alternatives considered**: Python 3.11 (older, no benefit), Python 3.13 (less mature ecosystem support for SQLAlchemy 2.x async + Clerk libs as of 2026-04).

## 2. Backend architecture

- **Decision**: Layered Clean Architecture with four explicit layers:
  - `domain/` — pure-Python entities, value objects, repository **ABCs** (interfaces). No FastAPI / SQLAlchemy / Pydantic imports.
  - `application/` — use cases (one class per business operation), DTOs, port interfaces (Clerk verifier port, clock port).
  - `infrastructure/` — SQLAlchemy 2.x async repositories, Clerk JWKS verifier, Alembic migrations, Unit-of-Work.
  - `interfaces/api/` — FastAPI routers, Pydantic request/response schemas, dependency wiring (`Depends(...)` factories).
- **Rationale**: The constitution mandates SOLID + Clean Code (Principle I) and interface-driven decoupling (Principle II). This layout keeps the domain layer framework-agnostic so use-case unit tests need no I/O — directly enabling TDD per Principle III. Mirrors the patterns in *Cosmic Python* (Percival & Gregory) and the widely-cited `zhanymkanov/fastapi-best-practices`.
- **Alternatives considered**: Vertical-slice / feature-folder layout (rejected — bleeds ORM types into routers, harder to swap implementations); Django-style fat-models (rejected — couples domain to ORM, breaks ABC substitution).

## 3. Backend primary dependencies

- **Decision**:
  - `fastapi>=0.115`
  - `pydantic>=2.10` (strict v2; v1 compat off)
  - `sqlalchemy>=2.0.36` (async-first, 2.x style)
  - `asyncpg>=0.30`
  - `alembic>=1.14`
  - `pyjwt[crypto]>=2.10` (Clerk JWT verification)
  - `httpx>=0.28` (JWKS fetch + outbound calls)
  - `python-jose` — **not** used (PyJWT preferred for active maintenance).
  - Existing: `uvicorn[standard]>=0.30`, `gunicorn>=22`, `psycopg[binary]>=3.2` (kept for tooling/migrations; runtime path uses asyncpg).
- **Rationale**: Production-stable versions with async support; PyJWT is lighter than the official `clerk-backend-api` SDK and fully covers JWKS verification.
- **Alternatives considered**: `clerk-backend-api` SDK (rejected — heavier surface, less control over caching), SQLModel (rejected — couples persistence to API schema, harms layering).

## 4. Storage

- **Decision**: PostgreSQL 16 (already provisioned in `docker-compose.yml`) with the `pg_trgm` extension enabled by Alembic migration.
- **Rationale**: Spec assumption (line 191) recommends a relational DB because the dynamic taxonomies, optional-field definitions, and "in-use" deletion rules (FR-019) depend on referential-integrity guarantees. Postgres also gives us trigram search to satisfy SC-002 (sub-1s search at 5k songs). NoSQL would push integrity into the application layer — strictly more complex.
- **Alternatives considered**: MongoDB (rejected — no FK enforcement, harder reference-count for FR-019), SQLite (rejected — single-writer, not suitable for production), DynamoDB (rejected — taxonomy joins awkward).

## 5. Search strategy (FR-023, SC-002)

- **Decision**: `pg_trgm` extension with GIN indexes on `lower(title)` and on the composer association via a normalised `composer_display` column (or `array_to_string(composers, ' ')`), queried with `ILIKE '%term%'`.
- **Rationale**: At ≤5,000 rows trigram returns sub-millisecond; supports the partial-match requirement (FR-023) and arbitrary leading wildcards naturally. Full-text `tsvector` is the wrong tool for substring search and would require per-language lexemes (problematic for hymn Latin/foreign composers).
- **Alternatives considered**: `tsvector` FTS (rejected — substring weakness), plain ILIKE without index (rejected — degrades past a few thousand rows), external search engine like Meilisearch (rejected — operational overhead unjustified at this scale).

## 6. Composer-set uniqueness enforcement (FR-009)

- **Decision**: Songs hold a generated, persisted `dedup_key TEXT` column = SHA-256 of `lower(trim(title)) || '|' || sorted_distinct(lower(trim(composer_name))).join(',')`. Computed in the **domain entity** before persistence (so the domain owns the rule). A `UNIQUE INDEX` is enforced at the DB level. Composers themselves live in a `song_composers` child table for display and query.
- **Rationale**: Postgres unique constraints cannot directly express "unordered set equality" across a child table. A normalised hash column gives O(1) DB-enforced uniqueness, survives composer reordering, and is naturally case/whitespace-insensitive — directly satisfying FR-009's "case-insensitive, composer set compared as an unordered set".
- **Alternatives considered**: `EXCLUDE` constraint with `array_agg` (rejected — requires triggers, fragile); application-only check (rejected — race conditions under concurrent inserts).

## 7. Concurrency control (FR-030)

- **Decision**: Integer `version` column on `songs` (and on `taxonomy_values`, `optional_field_definitions`). Updates use `UPDATE ... WHERE id=:id AND version=:expected RETURNING version`; zero-rows-affected → `HTTP 409 Conflict`. Client sends the expected version in the `If-Match` header (RFC 7232).
- **Rationale**: Monotonic integer is unambiguous; immune to clock skew and sub-millisecond write collisions that defeat `updated_at`-based ETags. Maps trivially to SQLAlchemy `version_id_col` if desired.
- **Alternatives considered**: `updated_at` + `If-Match` (rejected — sub-second collisions and TZ precision risk); pessimistic row locks (rejected — degrades read concurrency for an event that happens rarely).

## 8. Authentication & identity provider

- **Decision**: Clerk (resolved by `/speckit.clarify`) with Google sign-in enabled inside Clerk. Frontend uses `@clerk/nextjs` v6+ with `clerkMiddleware()` in `middleware.ts` and `<ClerkProvider>` wrapping `app/layout.tsx`. Backend verifies Clerk JWTs via JWKS (cached ~1h, PyJWT) — wired as a FastAPI dependency `Depends(get_current_user)` returning a frozen `CurrentUser` value object.
- **Rationale**: Spec FR-001 mandates Clerk; `@clerk/nextjs` v6 is the only path supported on App Router and is compatible with Next.js 16. JWKS-based JWT verification keeps the backend stateless and avoids round-tripping to Clerk on every request.
- **Alternatives considered**: NextAuth/Auth.js (rejected — more wiring across a separate FastAPI), Clerk session cookies forwarded cross-origin (rejected — CORS/SameSite friction; Bearer is cleaner for a decoupled backend).

## 9. Super Admin bootstrap (FR-007)

- **Decision**: Lazy "seed-on-first-login": a `UserProvisioningService` use case is invoked the first time a Clerk JWT for an unknown `clerk_user_id` is presented. It creates a `UserAccount` row; if the verified email appears in the `SUPER_ADMIN_EMAILS` env-var allowlist, the account's role is set to `SUPER_ADMIN`, otherwise `USER`.
- **Rationale**: No webhook surface to harden; deterministic and idempotent; a single code path covers every newly authenticated user. Clerk webhooks would add a public endpoint that needs signature verification — strictly more moving parts for the same outcome.
- **Alternatives considered**: Clerk `user.created` webhook (rejected — extra surface), manual SQL seeding at deploy (rejected — couples deploys to user list changes, contradicts FR-005's spirit).

## 10. Frontend framework & version

- **Decision**: Next.js 16.2.2 with the App Router (already pinned). React 19.2.4. TypeScript 5+.
- **Rationale**: Already installed. Next 16 standardises async dynamic APIs (`params`, `searchParams`, `cookies()`, `headers()` all return Promises — synchronous access throws), Server Components by default, and Turbopack as the default bundler. Server Components are the right fit for catalog browse pages (data fetched on the server, fast LCP per Constitution IV).
- **Alternatives considered**: Pages Router (rejected — legacy), Remix / TanStack Start (rejected — repo is already on Next).

## 11. Frontend styling & component library

- **Decision**: Tailwind CSS v4 (already installed) with CSS-first config (`@theme inline { ... }` block in `app/globals.css`). ShadCN UI primitives installed via `pnpm dlx shadcn@latest init` and `add` commands; output lives in `components/ui/`. `tw-animate-css` replaces the deprecated `tailwindcss-animate` plugin.
- **Rationale**: Tailwind v4 dropped `tailwind.config.ts` in favour of CSS variables. ShadCN's CLI fully supports v4 + Next 16 and writes a working `components.json`. ShadCN is the user's stated preference and gives us accessible, copy-into-repo primitives that we can wrap (not edit) inside our atomic-design layer.
- **Alternatives considered**: Mantine / Chakra (rejected — runtime CSS-in-JS, conflicts with Tailwind); Radix-only (rejected — ShadCN is essentially Radix + Tailwind glue, gives us better starting point).

## 12. Frontend architecture (Atomic Design)

- **Decision**: Five tiers, all components TypeScript-typed, dumb/presentational by default:
  - `components/ui/` — ShadCN primitives (do not edit; wrap them).
  - `components/atoms/` — single-purpose presentational pieces (Button wrappers, Badge, Icon). No data fetching. `"use client"` only when interactive.
  - `components/molecules/` — small composed widgets (SearchInput with clear button, FilterChip, SongCard). Receive all data via props.
  - `components/organisms/` — feature-level compositions (CatalogList, SongDetail, SongForm). May be Server Components when read-only; Client when they own form/local state.
  - `components/templates/` — layout shells (CatalogPageLayout, AdminPageLayout) — page-level composition without data.
  - Page-level data fetching lives in `app/**/page.tsx` (Server Component) and is passed down as props — keeping atoms/molecules pure and reusable.
- **Rationale**: Constitution Principle I (consistent structure) + user input ("favour dumb components for reuse"). Server Components for read flows hit the LCP target (Constitution IV).
- **Alternatives considered**: Feature-folder ("by domain") layout (rejected — fights the user's stated atomic-design preference); placing data fetching in molecules (rejected — couples presentation to server I/O, kills reusability).

## 13. Frontend data layer

- **Decision**: Server Components fetch via the `fetch` API (no extra client). Client Components use TanStack Query (`@tanstack/react-query` v5) for mutations (admin write actions) and any client-side reads that need optimistic updates / cache invalidation. A small typed API client in `services/api/` exposes typed functions per endpoint and is consumed both from RSC and from TanStack Query mutation functions — preserving a single contract.
- **Rationale**: RSC handles the public catalog browse path with zero client JS for data; TanStack Query handles admin forms cleanly with server-state caching and optimistic updates. Single typed client avoids drift between server and client paths.
- **Alternatives considered**: SWR (rejected — TanStack Query has stronger mutation primitives), Redux/Zustand (rejected — overkill, this is server state not app state), bare `fetch` everywhere (rejected — re-implements caching/invalidation poorly).

## 14. Testing stack

- **Decision**:
  - **Backend**: `pytest`, `pytest-asyncio`, `httpx` (TestClient async), `testcontainers-python` for Postgres, `freezegun` for time. Three tiers:
    - `tests/unit/` — domain + use cases against in-memory fakes implementing repository ABCs. Fast.
    - `tests/integration/` — SQLAlchemy repos + Alembic migrations against a real Postgres via testcontainers. Covers uniqueness, indexes, trigram queries.
    - `tests/contract/` — full FastAPI app via `httpx.AsyncClient`, with Clerk verifier overridden through `app.dependency_overrides`. Covers HTTP contracts, status codes, schemas, RBAC.
  - **Frontend**: `vitest` + `@testing-library/react` for unit/component tests, `@playwright/test` for E2E (including Clerk testing tokens and mobile-viewport assertions for FR-027 / SC-007), `msw` for network mocks in component tests.
- **Rationale**: Aligns with Constitution III (TDD mandatory). Three-tier backend split mirrors clean-architecture layers — fast unit feedback for business rules, slower integration only where a real DB matters. Vitest + Playwright is the Next 16 community default and avoids Jest/Turbopack ESM friction.
- **Alternatives considered**: Jest (rejected — slower, ESM friction), Cypress (rejected — Playwright has better RSC streaming + parallelism support), pytest-only without testcontainers (rejected — local Postgres setup adds friction; testcontainers makes CI deterministic).

## 15. Linting / formatting / type checking

- **Decision**:
  - **Backend**: Ruff (lint + format) configured in `pyproject.toml`; Pyright (or MyPy) in strict mode for the domain layer, normal for others.
  - **Frontend**: ESLint 9 (already present, flat config), `eslint-config-next`, Prettier, TypeScript strict mode.
- **Rationale**: Constitution Workflow gates require Ruff + Black/format for backend and ESLint/Prettier for frontend. Ruff supersedes Black for both. Strict typing in domain layer enforces interface contracts.
- **Alternatives considered**: Black + isort + flake8 (rejected — Ruff is faster and replaces all three).

## 16. Performance constraints

- **Decision**:
  - Backend p95 list/search < 200ms server-time at 5k songs (well under 1s in SC-002 budget).
  - Frontend LCP < 2.5s (Constitution IV) for the catalog list page on a 4G mobile profile.
  - Catalog list page uses RSC + cache-control headers; song detail uses RSC.
- **Rationale**: Direct restatement of constitution + spec. Achievable with trigram index + RSC for the read path.
- **Alternatives considered**: None (these are constraints, not options).

## 17. Project type

- **Decision**: Web application (separate `backend/` and `frontend/` packages), already mirrored by the repository.
- **Rationale**: Existing layout + clear backend/frontend split required by FastAPI + Next.js separation.
- **Alternatives considered**: Monorepo with shared TS types (rejected for v1 — backend is Python; would require codegen pipeline).

## 18. Scale / scope

- **Decision**: ≤5,000 songs, ≤a few thousand registered users, single-tenant single-parish deployment for v1 (per spec Assumptions).
- **Rationale**: Direct restatement; informs index selection and rules out engineering for sharding/multi-tenancy.
- **Alternatives considered**: None.

---

## Summary table

| Area | Decision |
|---|---|
| Backend language | Python 3.12 |
| Backend framework | FastAPI ≥0.115 |
| Backend architecture | Clean / layered (domain → application → infrastructure → interfaces/api) |
| ORM | SQLAlchemy 2.x async + Alembic |
| Database | PostgreSQL 16 + pg_trgm |
| Search | Trigram (`pg_trgm` GIN) |
| Concurrency | Integer `version` + `If-Match` → 409 |
| Uniqueness | Generated `dedup_key` SHA-256 + UNIQUE INDEX |
| Auth | Clerk (Google sign-in) + JWKS verification (PyJWT) |
| Super Admin bootstrap | Email-allowlist seeded on first sign-in |
| Frontend | Next.js 16.2.2 App Router + React 19 + Tailwind v4 + ShadCN |
| Frontend architecture | Atomic design (atoms / molecules / organisms / templates) over `components/ui/` ShadCN primitives |
| Frontend data | RSC fetch + TanStack Query for client mutations |
| Backend tests | pytest (unit / integration via testcontainers / contract via httpx) |
| Frontend tests | Vitest + Testing Library + Playwright + MSW |
| Lint/format/types | Ruff + Pyright (BE); ESLint + Prettier + TS strict (FE) |

All NEEDS CLARIFICATION items are resolved. Phase 1 may proceed.
