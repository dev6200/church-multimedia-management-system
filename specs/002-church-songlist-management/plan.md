# Implementation Plan: Catholic Church Songlist Management SaaS

**Branch**: `002-church-songlist-management` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-church-songlist-management/spec.md`

**Note**: This document is the planning output of `/speckit.plan`. Phase 0 (`research.md`), Phase 1 (`data-model.md`, `contracts/`, `quickstart.md`) are complete. Task generation (`tasks.md`) is the responsibility of `/speckit.tasks`.

## Summary

Build a single-tenant SaaS that lets a Catholic parish publish and manage a song catalog. Three roles — **Super Admin**, **Admin**, **User** — are issued by Clerk (Google sign-in inside Clerk). Read access (browse, search, filter, song detail) is **public** (FR-031); write access is restricted to Admins; role management is restricted to Super Admins; the initial Super Admin(s) are seeded via an env-based email allowlist on first sign-in (FR-007). Songs require a title and at least one composer; uniqueness is enforced on the (title, composer set) pair case-insensitively as an unordered set (FR-009). Admins can dynamically manage three taxonomies (Seasons / Masses / Special Events) and a catalog of optional link fields, with deletes guarded by a confirm-and-detach flow (FR-019).

**Technical approach** — Clean / layered architecture in a FastAPI backend (Python 3.12, SQLAlchemy 2.x async, PostgreSQL 16 with `pg_trgm`), with all domain logic behind ABC interfaces to honour Constitution Principles I and II. Frontend is Next.js 16 App Router (React 19, Tailwind v4, ShadCN) following atomic design with dumb / presentational components by default. TDD is mandatory at every layer (Constitution III): pytest unit / integration / contract tests on the backend; Vitest + Testing Library + Playwright on the frontend. Optimistic concurrency uses an integer `version` per row plus an `If-Match` header (FR-030). Search uses trigram GIN indexes to satisfy SC-002 at 5,000 songs. Identity is delegated to Clerk; the backend verifies JWTs via JWKS.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript 5.x with React 19 (frontend)
**Primary Dependencies**:
- Backend: FastAPI ≥0.115, Pydantic ≥2.10, SQLAlchemy 2.x async, asyncpg ≥0.30, Alembic ≥1.14, PyJWT[crypto] ≥2.10, httpx ≥0.28, uvicorn[standard], gunicorn
- Frontend: Next.js 16.2.2 (App Router), React 19.2.4, Tailwind CSS v4, ShadCN UI primitives, `@clerk/nextjs` v6+, `@tanstack/react-query` v5, `react-hook-form` + `zod`
**Storage**: PostgreSQL 16 (containerised via existing `docker-compose.yml`) with the `pg_trgm` extension. Schema managed by Alembic.
**Testing**:
- Backend: `pytest`, `pytest-asyncio`, `httpx` AsyncClient, `testcontainers-python` for Postgres, `freezegun`. Three tiers — `tests/unit/` (in-memory fakes of repository ABCs), `tests/integration/` (real Postgres, real Alembic), `tests/contract/` (full FastAPI app, Clerk verifier overridden via `app.dependency_overrides`).
- Frontend: `vitest` + `@testing-library/react`, `msw` for mocked network, `@playwright/test` for E2E (Clerk testing tokens, mobile viewport assertions).
**Target Platform**: Linux server (containerised) for backend + Postgres; modern evergreen browsers (mobile + desktop, viewport 320px upward) for frontend.
**Project Type**: Web application (backend + frontend). Already mirrored by the repo: `backend/` (FastAPI) and `frontend/` (Next.js).
**Performance Goals**:
- Backend p95 list/search < 200ms server-time at 5,000 songs (well under SC-002's 1s budget).
- Frontend LCP < 2.5s on 4G mobile profile for the catalog list page (Constitution IV).
**Constraints**:
- Mobile responsive 320px–desktop, no horizontal scroll, ≥44px tap targets (FR-027, SC-007).
- Public read endpoints reachable without auth (FR-031).
- Sub-1s search latency at 5,000 songs (SC-002).
- Optimistic concurrency rather than locks (FR-030); deletions of in-use taxonomy / optional-field values gated by confirm-and-detach (FR-019).
- Last-Super-Admin invariant (FR-006) enforced at the application service boundary.
**Scale/Scope**: Single-tenant single-parish v1; ≤5,000 songs; ≤a few thousand registered users (per spec Assumptions).

All NEEDS CLARIFICATION items have been resolved during `/speckit.clarify` (5 Q&As recorded in `spec.md`) and Phase 0 (`research.md`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (see end of document).*

The constitution at `.specify/memory/constitution.md` (v1.1.0) defines five core principles plus framework best practices and four workflow gates. This plan is checked against each below.

| # | Principle / Gate | Status | Notes |
|---|---|---|---|
| I | Code Quality & Maintainability (SOLID, Clean Code, consistent layout) | ✅ Pass | Clean layered architecture (domain / application / infrastructure / interfaces) gives a single, well-known place for every concern. Atomic-design tiers on the frontend are the same idea. Naming and folder layout enforced by the layout cheat-sheet in `quickstart.md`. |
| II | Decoupling & Flexibility (interfaces, composition over inheritance) | ✅ Pass | Repository ABCs in `domain/repositories/`, Clerk verifier and Clock as application **ports** (ABCs), `ApiClient` interfaces on the frontend (`services/api/contracts.ts`). All wired via `Depends()` (BE) or constructor injection (FE). No required inheritance hierarchies. |
| III | Test-Driven Development (failing test before code) | ✅ Pass | Three-tier backend test plan (unit/integration/contract) and Vitest + Playwright on the frontend, both designed for fast inner loops with in-memory fakes that satisfy the same ABCs as production code. `quickstart.md` §6 documents the TDD inner loop verbatim. |
| IV | UX Consistency & Performance (Core Web Vitals, efficient queries) | ✅ Pass | RSC on the public read path keeps client JS lean for LCP < 2.5s; trigram index meets SC-002; ShadCN + Tailwind tokens give a single, consistent UX surface. |
| V | Security by Design (no logged secrets, env vars, OWASP) | ✅ Pass | Identity delegated to Clerk (no first-party password storage, FR-001). All secrets in env (`SUPER_ADMIN_EMAILS`, `CLERK_*`, `DATABASE_URL`). RBAC enforced server-side at every privileged endpoint (FR-004). External link rendering uses `rel="noopener noreferrer"`. |
| FW-1 | Frontend (Next.js) best practices — App Router, Server Components, separation of UI vs business logic | ✅ Pass | App Router is the only routing model used; Server Components default, Client only where interactive; data fetching lives in route segments and `services/api/`, not in atoms/molecules. |
| FW-2 | Backend (FastAPI) — Pydantic, DI, REST, versioning | ✅ Pass | Pydantic v2 DTOs in `interfaces/api/schemas/`; all dependencies wired via `Depends()`; routes grouped under `/api/v1/...`; OpenAPI in `contracts/openapi.yaml` is the source of truth. |
| WF-1 | Linting / formatting | ✅ Pass | Ruff (BE) and ESLint + Prettier (FE) configured; tracked in `quickstart.md` §4. |
| WF-2 | Type safety | ✅ Pass | Pyright/MyPy on BE (strict on domain layer); TypeScript `strict: true` on FE. |
| WF-3 | Automated tests | ✅ Pass | Three-tier BE + Vitest/Playwright FE; mandatory for merge. |
| WF-4 | Code review | ☑ Process | Out of plan scope; remains a PR-time gate. |

Result: **No violations**, no entries required in the Complexity Tracking table below.

## Project Structure

### Documentation (this feature)

```text
specs/002-church-songlist-management/
├── plan.md                  # This file
├── spec.md                  # Feature spec (already authored)
├── research.md              # Phase 0 — tech decisions
├── data-model.md            # Phase 1 — entities, relationships, validation
├── contracts/
│   ├── openapi.yaml         # Phase 1 — backend HTTP contract
│   └── frontend-ui.md       # Phase 1 — frontend route/component/type contract
├── quickstart.md            # Phase 1 — bring-up + acceptance walk-through
├── checklists/
│   └── requirements.md      # Spec-quality checklist (already authored)
└── tasks.md                 # Phase 2 (NOT created here — produced by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── Dockerfile               # already present
├── requirements.txt         # extended during implementation (see research §3)
├── alembic.ini              # added during implementation
├── pyproject.toml           # added; carries Ruff + Pyright config
├── src/
│   ├── domain/
│   │   ├── entities/        # Song, UserAccount, TaxonomyValue, Composer, OptionalFieldDefinition, OptionalFieldValue
│   │   ├── value_objects/   # LinkUrl, ComposerName, DedupKey, Role, TaxonomyKind
│   │   └── repositories/    # SongRepository, UserRepository, TaxonomyRepository, OptionalFieldRepository (all ABCs)
│   ├── application/
│   │   ├── use_cases/       # CreateSong, UpdateSong, DeleteSong, ListSongs, GetSong,
│   │   │                    # CreateTaxonomyValue, RenameTaxonomyValue, DeleteTaxonomyValueWithDetach,
│   │   │                    # CreateOptionalField, RenameOptionalField, DeleteOptionalFieldWithDetach,
│   │   │                    # PromoteUser, DemoteUser, ProvisionUserOnFirstSignIn
│   │   ├── ports/           # ClerkVerifier (ABC), Clock (ABC), UnitOfWork (ABC)
│   │   └── errors.py        # DomainError, ConflictError, NotFoundError, ForbiddenError, LastSuperAdminError
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models/      # SQLAlchemy ORM
│   │   │   ├── repositories/  # concrete impls of domain ABCs
│   │   │   ├── unit_of_work.py
│   │   │   └── migrations/  # Alembic env + versions/
│   │   ├── auth/
│   │   │   └── clerk_jwks_verifier.py
│   │   └── config.py        # pydantic-settings
│   └── interfaces/
│       └── api/
│           ├── main.py      # FastAPI app
│           ├── deps.py      # Depends() factories
│           ├── routers/
│           │   ├── songs_public.py
│           │   ├── songs_admin.py
│           │   ├── taxonomies.py
│           │   ├── optional_fields.py
│           │   ├── users_super_admin.py
│           │   └── auth_me.py
│           └── schemas/     # Pydantic v2 request/response models
└── tests/
    ├── conftest.py
    ├── unit/                # in-memory fakes of repository ABCs
    ├── integration/         # SQLAlchemy + testcontainers Postgres
    └── contract/            # full app via httpx.AsyncClient

frontend/
├── Dockerfile               # already present
├── package.json             # already present (next 16.2.2, react 19, tailwind v4)
├── components.json          # added by `shadcn init`
├── middleware.ts            # added — clerkMiddleware route gating
├── app/
│   ├── layout.tsx           # wrapped in <ClerkProvider>
│   ├── globals.css          # Tailwind v4 @theme tokens + ShadCN CSS vars
│   ├── page.tsx             # Catalog list (RSC)
│   ├── songs/[id]/page.tsx  # Song detail (RSC)
│   ├── admin/
│   │   ├── page.tsx
│   │   ├── songs/new/page.tsx
│   │   ├── songs/[id]/edit/page.tsx
│   │   ├── taxonomies/[kind]/page.tsx
│   │   └── optional-fields/page.tsx
│   ├── super-admin/users/page.tsx
│   ├── sign-in/[[...rest]]/page.tsx
│   └── sign-up/[[...rest]]/page.tsx
├── components/
│   ├── ui/                  # ShadCN primitives
│   ├── atoms/
│   ├── molecules/
│   ├── organisms/
│   └── templates/
├── services/
│   └── api/
│       ├── contracts.ts     # interfaces (ApiClient, SongsApi, TaxonomiesApi, ...)
│       ├── client.ts        # fetch impl that injects Clerk Bearer
│       └── fake.ts          # in-memory impl for component tests
├── hooks/
├── lib/                     # cn(), format helpers
├── types/
│   └── api.ts               # types mirroring OpenAPI
├── tests/
│   ├── unit/                # vitest component / hook tests
│   └── e2e/                 # Playwright suites per user story
└── public/
```

**Structure Decision**: Web-application layout. The repository already has `backend/` (FastAPI) and `frontend/` (Next.js) directories — those are kept and extended. Backend gains a `src/` package implementing the four-layer clean architecture from `research.md` §2. Frontend gains the atomic-design tiers under `components/` (already scaffolded), the typed `services/api/` interface layer, and Clerk middleware. All paths above are project-relative; documents in `specs/` are also project-relative.

## Phase 0 — Outline & Research

Complete. Output: [`research.md`](./research.md). Eighteen decision blocks cover language, architecture, dependencies, storage, search, uniqueness, concurrency, auth, Super Admin bootstrap, frontend stack and architecture, data layer, testing, lint/format/types, performance constraints, project type, and scale.

## Phase 1 — Design & Contracts

Complete.

- **Data model** → [`data-model.md`](./data-model.md). Six entities (UserAccount, Song, Composer, TaxonomyValue, OptionalFieldDefinition, OptionalFieldValue) with three association tables, full validation rules tied to FRs, "detach" semantics for FR-019, and a deterministic Alembic migration ordering.
- **Backend contract** → [`contracts/openapi.yaml`](./contracts/openapi.yaml). OpenAPI 3.1 for every endpoint touched by FR-001 through FR-031, with a stable error-code vocabulary and explicit `If-Match` headers on every mutating endpoint.
- **Frontend UI contract** → [`contracts/frontend-ui.md`](./contracts/frontend-ui.md). Route map, atomic-design component map (atoms / molecules / organisms / templates), TypeScript type contract that mirrors the OpenAPI schema, and the `ApiClient` family of interfaces consumed by both production and test code.
- **Quickstart** → [`quickstart.md`](./quickstart.md). Bring-up, env vars, test commands, and an acceptance walk-through against each user story (1–4).
- **Agent context update**: the `<!-- SPECKIT START -->` block in `CLAUDE.md` is updated to point to this plan (see step performed by `/speckit.plan`).

## Constitution Check (post-design re-evaluation)

Re-checked after Phase 1 artefacts were produced. No new violations introduced; the design strictly composes the principles already cited above:

- Repository ABCs and the `ApiClient` family materialise Principle II as concrete TypeScript interfaces and Python ABCs.
- Three test tiers and the in-memory fakes give Principle III a sharp inner loop.
- The OpenAPI contract is the single source of truth shared by backend Pydantic schemas and frontend `types/api.ts` — Principle I (consistency) and FW-2 (Pydantic / versioning) jointly satisfied.
- All admin routes are server-gated; public routes are explicitly enumerated under "Catalog (public read)" — Principle V continues to hold.

Result: **No violations**, no Complexity Tracking entries required.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*N/A — no violations.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
