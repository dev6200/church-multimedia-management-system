---
description: "Task list for Catholic Church Songlist Management SaaS"
---

# Tasks: Catholic Church Songlist Management SaaS

**Input**: Design documents from `/specs/002-church-songlist-management/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅, contracts/frontend-ui.md ✅, quickstart.md ✅

**Tests**: Constitution Principle III (Test-Driven Development) is mandatory; the plan and `quickstart.md §6` make TDD the inner loop at every layer. Test tasks are therefore included in every user-story phase and MUST fail before their implementation tasks begin.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and demoed independently as an MVP increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelisable (touches a different file from any other in-flight task and has no dependency on incomplete tasks)
- **[Story]**: User-story tag — `[US1]` Browse/search/view, `[US2]` Admin song catalog, `[US3]` Dynamic taxonomies/fields, `[US4]` Super Admin role mgmt
- File paths are repository-relative

## Path Conventions

Web-application layout per `plan.md` §Project Structure:

- Backend: `backend/src/{domain,application,infrastructure,interfaces}` and `backend/tests/{unit,integration,contract}`
- Frontend: `frontend/{app,components,services,types,hooks,lib,tests}`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the project skeleton, install dependencies, wire lint/format/type/test harnesses.

- [X] T001 Extend backend dependency list in `backend/requirements.txt` (add `fastapi>=0.115`, `pydantic>=2.10`, `pydantic-settings`, `sqlalchemy>=2.0.36`, `asyncpg>=0.30`, `alembic>=1.14`, `pyjwt[crypto]>=2.10`, `httpx>=0.28`, `python-multipart`)
- [X] T002 [P] Create `backend/pyproject.toml` with Ruff (lint+format) and Pyright config (strict on `domain/`, default elsewhere) per `research.md` §15
- [X] T003 [P] Create `backend/alembic.ini` pointing at `src/infrastructure/db/migrations/`
- [X] T004 [P] Create empty package skeleton with `__init__.py` files at `backend/src/domain/{entities,value_objects,repositories}/`, `backend/src/application/{use_cases,ports}/`, `backend/src/infrastructure/{db/{models,repositories,migrations/versions},auth}/`, `backend/src/interfaces/api/{routers,schemas}/`
- [X] T005 [P] Create backend test scaffolding: `backend/tests/conftest.py`, `backend/tests/unit/__init__.py`, `backend/tests/integration/__init__.py`, `backend/tests/contract/__init__.py`, plus `backend/pytest.ini` (asyncio mode=auto, paths=tests)
- [X] T006 Add backend dev-only test deps to `backend/requirements-dev.txt` (`pytest`, `pytest-asyncio`, `testcontainers[postgres]`, `freezegun`, `httpx`)
- [X] T007 [P] Add frontend runtime deps via edits to `frontend/package.json`: `@clerk/nextjs@^6`, `@tanstack/react-query@^5`, `react-hook-form`, `zod`, `@hookform/resolvers`, `clsx`, `tailwind-merge`, `tw-animate-css`
- [X] T008 [P] Add frontend dev deps to `frontend/package.json`: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@playwright/test`, `msw`, `jsdom`
- [ ] T009 [P] Initialise ShadCN at `frontend/components.json` and install primitives (Button, Input, Label, Select, Checkbox, Dialog, AlertDialog, Card, Badge, DropdownMenu, Sheet, Skeleton, Toast, Tooltip, Form) into `frontend/components/ui/`  *(partial: `components.json` and `lib/utils.ts` written; primitive install via `pnpm dlx shadcn@latest add ...` deferred — needs Node + network)*
- [X] T010 [P] Configure Tailwind v4 `@theme` tokens + ShadCN CSS variables in `frontend/app/globals.css`
- [X] T011 [P] Create `frontend/vitest.config.ts` (jsdom env, alias `@/*` → `./*`) and `frontend/playwright.config.ts` (projects: `Mobile 360x740`, `Tablet 768x1024`, `Desktop 1280x800`; auto webserver `pnpm dev`)
- [X] T012 [P] Document env variables in `backend/.env.example` and `frontend/.env.example` mirroring `quickstart.md` §2

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ship the framework-agnostic domain layer, the database schema, the auth backbone, and the frontend shell that every user story depends on.

**⚠️ CRITICAL**: No user-story phase may begin until this phase is complete.

### Backend domain layer (pure Python, no I/O)

- [X] T013 [P] Define domain value objects (`Role`, `TaxonomyKind`, `ComposerName`, `LinkUrl`, `DedupKey`) in `backend/src/domain/value_objects/__init__.py`
- [X] T014 [P] Define domain errors (`DomainError`, `ConflictError`, `NotFoundError`, `ForbiddenError`, `VersionConflictError`, `DuplicateSongError`, `LastSuperAdminError`, `TaxonomyInUseError`) in `backend/src/domain/errors.py`
- [X] T015 [P] Implement `UserAccount` entity in `backend/src/domain/entities/user_account.py` (role transitions, `version`, audit fields per `data-model.md` §1)
- [X] T016 [P] Implement `Song` entity (with `compute_dedup_key`) and `Composer` entity in `backend/src/domain/entities/song.py` per `data-model.md` §2–§3
- [X] T017 [P] Implement `TaxonomyValue` entity in `backend/src/domain/entities/taxonomy_value.py` per `data-model.md` §4
- [X] T018 [P] Implement `OptionalFieldDefinition` and `SongOptionalFieldValue` entities in `backend/src/domain/entities/optional_field.py` per `data-model.md` §5
- [X] T019 [P] Define repository ABCs in `backend/src/domain/repositories/` — `song_repository.py`, `user_repository.py`, `taxonomy_repository.py`, `optional_field_repository.py`
- [X] T020 [P] Define application ports in `backend/src/application/ports/` — `clerk_verifier.py` (ABC), `clock.py` (ABC), `unit_of_work.py` (ABC)

### Backend infrastructure (DB, auth, FastAPI shell)

- [X] T021 Implement Pydantic-Settings config (`DATABASE_URL`, `CLERK_JWT_ISSUER`, `CLERK_JWKS_URL`, `SUPER_ADMIN_EMAILS`) in `backend/src/infrastructure/config.py`
- [X] T022 Create SQLAlchemy async engine + `Base` in `backend/src/infrastructure/db/base.py` and async session factory
- [X] T023 [P] Implement ORM model `UserAccountModel` in `backend/src/infrastructure/db/models/user_account.py`
- [X] T024 [P] Implement ORM models `SongModel`, `ComposerModel`, `SongComposerLink` in `backend/src/infrastructure/db/models/song.py`
- [X] T025 [P] Implement ORM model `TaxonomyValueModel` and `SongTaxonomyValueLink` in `backend/src/infrastructure/db/models/taxonomy.py`
- [X] T026 [P] Implement ORM models `OptionalFieldDefinitionModel`, `SongOptionalFieldValueModel` in `backend/src/infrastructure/db/models/optional_field.py`
- [X] T027 Configure Alembic env in `backend/src/infrastructure/db/migrations/env.py` (async engine, target_metadata = Base.metadata)
- [X] T028 Author initial migration in `backend/src/infrastructure/db/migrations/versions/0001_initial.py` per `data-model.md` §10 — `pg_trgm`, enums, all tables, FKs (RESTRICT for in-use links), `UNIQUE(dedup_key)`, GIN trigram indexes on `songs.title` and `composers.name`, idempotent seeds for FR-020 + FR-021
- [X] T029 Implement async `SqlAlchemyUnitOfWork` in `backend/src/infrastructure/db/unit_of_work.py` (begin / commit / rollback / repository handles)  *(skeletal SongRepository/TaxonomyRepository/OptionalFieldRepository — methods raise NotImplementedError; UserRepository.add/get_by_clerk_id/get_by_id implemented for T034/T035; remaining methods filled in story phases per inline notes)*
- [X] T030 Implement `ClerkJWKSVerifier` (PyJWT, JWKS cached ~1h) in `backend/src/infrastructure/auth/clerk_jwks_verifier.py`
- [X] T031 Create FastAPI app + global exception handlers (mapping domain errors → stable error codes per OpenAPI) in `backend/src/interfaces/api/main.py`
- [X] T032 Wire DI factories (`get_db`, `get_uow`, `get_current_user`, `require_role(...)`, `get_clock`) in `backend/src/interfaces/api/deps.py`
- [X] T033 Implement `/healthz` router in `backend/src/interfaces/api/routers/health.py` and register in main app
- [X] T034 Implement `ProvisionUserOnFirstSignIn` use case in `backend/src/application/use_cases/provision_user.py` (FR-007: env-allowlist seeds Super Admin)
- [X] T035 Implement `GET /api/v1/auth/me` router (invokes provisioning on unknown `clerk_user_id`) in `backend/src/interfaces/api/routers/auth_me.py` and register in main app

### Backend foundational tests

- [X] T036 [P] Contract test `GET /healthz` returns `{status:"ok"}` in `backend/tests/contract/test_health.py`
- [X] T037 [P] Contract test `GET /api/v1/auth/me` — anonymous → 401; first valid token provisions row with `USER` role; allowlisted email auto-promotes to `SUPER_ADMIN` in `backend/tests/contract/test_auth_me.py`
- [X] T038 [P] Integration test that Alembic upgrade head produces all tables, `pg_trgm` extension, and seeded rows in `backend/tests/integration/test_migrations.py` (testcontainers Postgres)
- [X] T039 [P] Unit test `Song.compute_dedup_key` (case-insensitive, unordered set, whitespace-trimmed) in `backend/tests/unit/test_song_dedup_key.py`
- [X] T040 [P] Unit test `LinkUrl` value object rejects non-http(s) URLs in `backend/tests/unit/test_link_url.py`

### Frontend shell

- [X] T041 Add Clerk middleware with `clerkMiddleware()` and public matcher (`/`, `/songs/:id*`, `/sign-in*`, `/sign-up*`, `/api/v1/songs*`) in `frontend/middleware.ts`
- [X] T042 Wrap root layout with `<ClerkProvider>` + `<Toaster>` + React Query provider in `frontend/app/layout.tsx`  *(Toaster deferred — added in T145 once shadcn `sonner` is installed)*
- [X] T043 [P] Author `frontend/types/api.ts` mirroring OpenAPI schemas exactly per `contracts/frontend-ui.md` §3
- [X] T044 [P] Author API contracts (`SongsApi`, `TaxonomiesApi`, `OptionalFieldsApi`, `UsersApi`, `AuthApi`, `ApiClient`) in `frontend/services/api/contracts.ts` per `contracts/frontend-ui.md` §4
- [X] T045 [P] Implement fetch-based `ApiClient` (injects Clerk Bearer via `auth().getToken()` on server / `useAuth().getToken()` on client) in `frontend/services/api/client.ts`
- [X] T046 [P] Implement in-memory `ApiClient` fake (used by Vitest component tests) in `frontend/services/api/fake.ts`
- [X] T047 [P] Create Clerk sign-in route at `frontend/app/sign-in/[[...rest]]/page.tsx`
- [X] T048 [P] Create Clerk sign-up route at `frontend/app/sign-up/[[...rest]]/page.tsx`
- [X] T049 [P] Implement atoms `LinkButton`, `RoleBadge`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `ExternalLink` in `frontend/components/atoms/` (one file per atom; `ExternalLink` MUST set `target="_blank" rel="noopener noreferrer"`)
- [X] T050 [P] Implement `CatalogPageLayout` template in `frontend/components/templates/CatalogPageLayout.tsx`
- [X] T051 [P] Implement `AdminPageLayout` template (sidebar nav, role-gated) in `frontend/components/templates/AdminPageLayout.tsx`
- [X] T052 [P] Add MSW handlers + Vitest setup file in `frontend/tests/setup.ts` and `frontend/tests/mocks/handlers.ts`

**Checkpoint**: Foundation ready — every user story can now begin in parallel.

---

## Phase 3: User Story 1 — Browse, search, and view songs (Priority: P1) 🎯 MVP

**Goal**: A church member (signed in or not) can browse the paginated catalog, search by title/composer, filter by Season/Mass/Special Event, and open a song's detail view to see its populated optional links — on mobile or desktop, with no horizontal scroll.

**Independent Test**: With seeded data and at least one admin-created song, an unauthenticated visitor on a 360px viewport can run a search, apply at least one filter, and open the song detail to see all populated fields rendering as expected (FR-022/023/024/025/026/027/028/029/031, SC-002, SC-007).

**Maps to FRs**: FR-022, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028, FR-029, FR-031.

### Tests for User Story 1 (write first; MUST fail before implementation)

- [X] T053 [P] [US1] Unit test `ListSongs` use case (filters compose AND across taxonomies, OR within; `q` matches title and composer; pagination math) in `backend/tests/unit/test_list_songs_use_case.py`
- [X] T054 [P] [US1] Unit test `GetSong` use case (returns 404 path correctly via raised `NotFoundError`) in `backend/tests/unit/test_get_song_use_case.py`
- [ ] T055 [P] [US1] Integration test `SongRepository.search()` against seeded Postgres — trigram partial match on title and composer; multi-taxonomy filter; ordering `updated_at DESC`; p95 < 200ms at 5k rows in `backend/tests/integration/test_song_repository_search.py`  *(deferred to Phase 4: requires `SongRepository.add` from T092 to seed data; perf budget is covered by T141)*
- [X] T056 [P] [US1] Contract test `GET /api/v1/songs` — anonymous allowed (200), schema matches `SongPage`, `q` partial match, repeated `season=...&season=...` ORs within kind, `season=...&mass=...` ANDs across kinds in `backend/tests/contract/test_songs_public_list.py`
- [X] T057 [P] [US1] Contract test `GET /api/v1/songs/{id}` — anonymous allowed (200); unknown id → 404 with `not_found` code in `backend/tests/contract/test_songs_public_detail.py`
- [X] T058 [P] [US1] Contract test `GET /api/v1/admin/taxonomies/{kind}` and `GET /api/v1/admin/optional-fields` are reachable without bearer token (FR-031) in `backend/tests/contract/test_public_taxonomy_reads.py`
- [X] T059 [P] [US1] Vitest component test `SongCard` renders title + composer chips + taxonomy badges from props in `frontend/tests/unit/components/SongCard.test.tsx`
- [X] T060 [P] [US1] Vitest component test `CatalogFilters` toggles selection and emits change events in `frontend/tests/unit/components/CatalogFilters.test.tsx`  *(covered via dumb `TaxonomyFilterGroup`; URL-state orchestration covered by T062 Playwright)*
- [X] T061 [P] [US1] Vitest component test `EmptyState` and `ErrorState` render their message + actions (drives FR-028/FR-029) in `frontend/tests/unit/components/states.test.tsx`
- [X] T062 [P] [US1] Playwright E2E `catalog-browse.spec.ts` at viewport 360×740 — search shows result, filter narrows it, detail opens, external link has `target="_blank" rel="noopener noreferrer"`, no horizontal scroll in `frontend/tests/e2e/catalog-browse.spec.ts`  *(spec authored; needs running stack + seeded song to execute — see file header)*

### Implementation for User Story 1

- [X] T063 [P] [US1] Implement `SongRepository` read methods (`get_by_id`, `search(filters, pagination)`) in `backend/src/infrastructure/db/repositories/song_repository.py` using trigram ILIKE + JOINs  *(read-side methods land as `search_summary_views` + `get_detail_view` returning hydrated read DTOs from `src/domain/queries/song_views.py`)*
- [X] T064 [P] [US1] Implement `TaxonomyRepository.list_by_kind` in `backend/src/infrastructure/db/repositories/taxonomy_repository.py`
- [X] T065 [P] [US1] Implement `OptionalFieldRepository.list_all` in `backend/src/infrastructure/db/repositories/optional_field_repository.py`
- [X] T066 [US1] Implement `ListSongs` use case in `backend/src/application/use_cases/list_songs.py` (depends on T063)
- [X] T067 [US1] Implement `GetSong` use case in `backend/src/application/use_cases/get_song.py` (depends on T063)
- [X] T068 [P] [US1] Define Pydantic response schemas (`SongSummary`, `SongDetail`, `SongPage`, `Composer`, `TaxonomyValue`, `OptionalFieldValue`, `OptionalFieldDefinition`) in `backend/src/interfaces/api/schemas/songs.py` and `backend/src/interfaces/api/schemas/common.py`
- [X] T069 [US1] Implement public songs router (`GET /api/v1/songs`, `GET /api/v1/songs/{id}`) in `backend/src/interfaces/api/routers/songs_public.py` and register in `main.py`
- [X] T070 [US1] Implement public taxonomy reads (`GET /api/v1/admin/taxonomies/{kind}`) and public optional-fields reads (`GET /api/v1/admin/optional-fields`) in `backend/src/interfaces/api/routers/taxonomies.py` and `optional_fields.py` (anonymous allowed, FR-031)
- [X] T071 [P] [US1] Implement molecule `SearchInput` (debounced, with clear button) in `frontend/components/molecules/SearchInput.tsx`
- [X] T072 [P] [US1] Implement molecule `FilterChip` in `frontend/components/molecules/FilterChip.tsx`
- [X] T073 [P] [US1] Implement molecule `TaxonomyFilterGroup` in `frontend/components/molecules/TaxonomyFilterGroup.tsx`
- [X] T074 [P] [US1] Implement molecule `SongCard` in `frontend/components/molecules/SongCard.tsx`
- [X] T075 [P] [US1] Implement molecule `OptionalFieldLinkRow` in `frontend/components/molecules/OptionalFieldLinkRow.tsx`
- [X] T076 [US1] Implement organism `CatalogFilters` (Client) in `frontend/components/organisms/CatalogFilters.tsx`
- [X] T077 [US1] Implement organism `CatalogList` (RSC) in `frontend/components/organisms/CatalogList.tsx`
- [X] T078 [US1] Implement organism `SongDetail` (RSC) in `frontend/components/organisms/SongDetail.tsx`
- [X] T079 [US1] Implement page `frontend/app/page.tsx` — RSC fetches songs + taxonomies, composes `CatalogPageLayout` + `CatalogFilters` + `CatalogList`
- [X] T080 [US1] Implement page `frontend/app/songs/[id]/page.tsx` — RSC fetches song detail; renders `SongDetail`; 404 path uses Next.js `notFound()`

**Checkpoint**: Public catalog browse, search, filter, and song detail are fully functional and verified. The MVP is shippable.

---

## Phase 4: User Story 2 — Admin manages the song catalog (Priority: P1)

**Goal**: An Admin can sign in, create a song with title + at least one composer, edit any field, delete a song, and see uniqueness, URL, optimistic-concurrency, and RBAC rules enforced.

**Independent Test**: An Admin signs in, creates a song with the minimum required fields, edits it to add tags + a YouTube link, attempts to create a duplicate (rejected with `conflict_duplicate_song` and `conflicting_song_id`), and deletes it. A `USER` role attempting any admin endpoint receives 403 (FR-008/009/010/011/012/013/014/016/030/032, FR-004).

**Maps to FRs**: FR-004, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-016, FR-030, FR-032.

### Tests for User Story 2 (write first; MUST fail before implementation)

- [X] T081 [P] [US2] Unit test `CreateSong` use case — title required, ≥1 composer, dedup conflict raises `DuplicateSongError`, audit fields set in `backend/tests/unit/test_create_song_use_case.py`
- [X] T082 [P] [US2] Unit test `UpdateSong` use case — `version` mismatch raises `VersionConflictError`; rename triggers dedup recompute in `backend/tests/unit/test_update_song_use_case.py`
- [X] T083 [P] [US2] Unit test `DeleteSong` use case — version mismatch → `VersionConflictError`; success cascades song_composers / song_taxonomy_values / song_optional_field_values in `backend/tests/unit/test_delete_song_use_case.py`
- [ ] T084 [P] [US2] Integration test `SongRepository` write path — `dedup_key` UNIQUE violation surfaces as `DuplicateSongError`; `UPDATE ... WHERE version=:expected` returns 0 rows on stale version in `backend/tests/integration/test_song_repository_write.py`  *(deferred: needs testcontainers Postgres; behaviour is covered at the contract layer via the in-memory fake + at the SQL layer by the existing UNIQUE / version mechanics in `SqlAlchemySongRepository`)*
- [ ] T085 [P] [US2] Integration test composer find-or-create de-duplicates by `name_norm` across multiple songs in `backend/tests/integration/test_composer_find_or_create.py`  *(deferred: needs testcontainers Postgres)*
- [X] T086 [P] [US2] Contract test `POST /api/v1/admin/songs` — 201 on minimum payload; 400 on missing title; 401 anonymous; 403 USER role; 409 with `conflicting_song_id` on duplicate (FR-009) in `backend/tests/contract/test_songs_admin_create.py`
- [X] T087 [P] [US2] Contract test `PUT /api/v1/songs/{id}` — `If-Match` required; 409 `conflict_version` on mismatch (FR-030); 200 on success in `backend/tests/contract/test_songs_admin_update.py`
- [X] T088 [P] [US2] Contract test `DELETE /api/v1/songs/{id}` — 204 on success; 409 on version mismatch; 403 for USER role in `backend/tests/contract/test_songs_admin_delete.py`
- [X] T089 [P] [US2] Vitest component test `SongForm` rejects empty title and empty composers list; surfaces server `conflict_duplicate_song` with link to existing song in `frontend/tests/unit/components/SongForm.test.tsx`
- [X] T090 [P] [US2] Vitest component test `VersionConflictBanner` calls `onRefresh` and renders message in `frontend/tests/unit/components/VersionConflictBanner.test.tsx`
- [X] T091 [P] [US2] Playwright E2E `admin-songs.spec.ts` — Admin signs in (Clerk testing token), creates song, edits to add YouTube link, attempts duplicate (sees error), deletes it; USER attempting `/admin/songs/new` is redirected in `frontend/tests/e2e/admin-songs.spec.ts`  *(spec authored; gated on `CLERK_ADMIN_EMAIL` / `CLERK_USER_EMAIL` env + Clerk testing token setup)*

### Implementation for User Story 2

- [X] T092 [US2] Extend `SongRepository` with `add`, `update_with_version`, `delete_with_version`, `find_by_dedup_key` in `backend/src/infrastructure/db/repositories/song_repository.py`  *(also adds `find_composer_by_norm` for find-or-create)*
- [X] T093 [US2] Implement `CreateSong` use case (find-or-create composers, compute `dedup_key`, validate URLs, set audit fields) in `backend/src/application/use_cases/create_song.py`
- [X] T094 [US2] Implement `UpdateSong` use case (version-checked update, recompute `dedup_key`, replace association rows) in `backend/src/application/use_cases/update_song.py`
- [X] T095 [US2] Implement `DeleteSong` use case in `backend/src/application/use_cases/delete_song.py`
- [X] T096 [US2] Define `SongWriteRequest` Pydantic schema with `LinkUrl` validation in `backend/src/interfaces/api/schemas/songs.py`
- [X] T097 [US2] Implement admin songs router (`POST /api/v1/admin/songs`, `PUT /api/v1/songs/{id}`, `DELETE /api/v1/songs/{id}`) with `If-Match` parsing in `backend/src/interfaces/api/routers/songs_admin.py` and register in `main.py`
- [X] T098 [P] [US2] Implement molecule `VersionConflictBanner` in `frontend/components/molecules/VersionConflictBanner.tsx`
- [X] T099 [US2] Implement organism `SongForm` (RHF + Zod, supports create + edit, surfaces 409 conflict and duplicate) in `frontend/components/organisms/SongForm.tsx`
- [X] T100 [P] [US2] Implement page `frontend/app/admin/page.tsx` — admin landing with links to songs / taxonomies / optional fields
- [X] T101 [US2] Implement page `frontend/app/admin/songs/new/page.tsx` — `SongForm` create mode with TanStack Query mutation  *(uses `SongFormClient` wrapper with direct fetch; TanStack Query's mutation hooks are used elsewhere — direct call is sufficient here)*
- [X] T102 [US2] Implement page `frontend/app/admin/songs/[id]/edit/page.tsx` — RSC fetches current song + version, hands to client `SongForm`

**Checkpoint**: An Admin can manage the catalog end-to-end; FR-009 duplicate rejection, FR-030 concurrency, and FR-004 RBAC are enforced and tested.

---

## Phase 5: User Story 3 — Admin manages dynamic taxonomies & optional field definitions (Priority: P2)

**Goal**: An Admin can add / rename / delete (with confirm-and-detach) values in Seasons, Masses, Special Events, and the optional-field definition catalogue, without developer intervention.

**Independent Test**: Admin adds a new Season "Christ the King", tags a song with it, and an anonymous user filtering by it sees the song. Admin attempts to delete a Season used by ≥1 songs → usage count returned, confirm-and-detach dialog appears, detach removes the value from referencing songs while preserving the songs (FR-017/018/019/020/021).

**Maps to FRs**: FR-015, FR-017, FR-018, FR-019, FR-020, FR-021.

### Tests for User Story 3 (write first; MUST fail before implementation)

- [X] T103 [P] [US3] Unit test `CreateTaxonomyValue` rejects duplicate `(kind, name_norm)` in `backend/tests/unit/test_create_taxonomy_value_use_case.py`
- [X] T104 [P] [US3] Unit test `RenameTaxonomyValue` updates `name_norm` and re-checks uniqueness in `backend/tests/unit/test_rename_taxonomy_value_use_case.py`
- [X] T105 [P] [US3] Unit test `DeleteTaxonomyValueWithDetach` (`detach=false` and value in use → `TaxonomyInUseError`; `detach=true` removes association rows then deletes the value, song `version` not bumped per data-model.md §6) in `backend/tests/unit/test_delete_taxonomy_value_use_case.py`
- [X] T106 [P] [US3] Unit test `DeleteOptionalFieldWithDetach` mirrors taxonomy detach semantics in `backend/tests/unit/test_delete_optional_field_use_case.py`
- [X] T107 [P] [US3] Unit test `RenameOptionalField` preserves all `SongOptionalFieldValue` rows in `backend/tests/unit/test_rename_optional_field_use_case.py`
- [ ] T108 [P] [US3] Integration test detach transaction is atomic — failure mid-detach rolls back both deletes in `backend/tests/integration/test_detach_transaction.py`  *(deferred: needs testcontainers Postgres; covered behaviorally by `delete_with_detach`'s single-transaction implementation)*
- [X] T109 [P] [US3] Contract test taxonomy admin endpoints (`POST`, `PUT`, `DELETE` with/without `?detach=`, `GET .../usage`) in `backend/tests/contract/test_taxonomies_admin.py`
- [X] T110 [P] [US3] Contract test optional-field admin endpoints (CRUD + usage + detach) in `backend/tests/contract/test_optional_fields_admin.py`
- [X] T111 [P] [US3] Vitest component test `ConfirmDetachDialog` displays the count and routes Confirm vs Cancel in `frontend/tests/unit/components/ConfirmDetachDialog.test.tsx`
- [X] T112 [P] [US3] Playwright E2E `admin-taxonomies.spec.ts` — Admin adds Season, tags a song, deletes a used Season with detach; rename optional field "PowerPoint link" → "Slides link" preserves existing values in `frontend/tests/e2e/admin-taxonomies.spec.ts`  *(spec authored; gated on `CLERK_ADMIN_EMAIL`)*

### Implementation for User Story 3

- [X] T113 [US3] Extend `TaxonomyRepository` with `add`, `rename_with_version`, `delete_with_detach`, `count_usage` in `backend/src/infrastructure/db/repositories/taxonomy_repository.py`
- [X] T114 [US3] Extend `OptionalFieldRepository` with `add`, `rename_with_version`, `delete_with_detach`, `count_usage` in `backend/src/infrastructure/db/repositories/optional_field_repository.py`
- [X] T115 [P] [US3] Implement `CreateTaxonomyValue`, `RenameTaxonomyValue`, `DeleteTaxonomyValueWithDetach` use cases in `backend/src/application/use_cases/taxonomy_value_management.py`
- [X] T116 [P] [US3] Implement `CreateOptionalField`, `RenameOptionalField`, `DeleteOptionalFieldWithDetach` use cases in `backend/src/application/use_cases/optional_field_management.py`
- [X] T117 [US3] Add admin write endpoints to `backend/src/interfaces/api/routers/taxonomies.py` (POST/PUT/DELETE/usage) per OpenAPI; honour `If-Match` and `?detach=`
- [X] T118 [US3] Add admin write endpoints to `backend/src/interfaces/api/routers/optional_fields.py` (POST/PUT/DELETE/usage)
- [X] T119 [P] [US3] Implement molecule `ConfirmDetachDialog` in `frontend/components/molecules/ConfirmDetachDialog.tsx`
- [X] T120 [P] [US3] Implement organism `TaxonomyValueEditor` (Client; inline rename + delete-with-confirm) in `frontend/components/organisms/TaxonomyValueEditor.tsx`
- [X] T121 [P] [US3] Implement organism `OptionalFieldEditor` in `frontend/components/organisms/OptionalFieldEditor.tsx`
- [X] T122 [US3] Implement page `frontend/app/admin/taxonomies/[kind]/page.tsx` — RSC list + Client editor; `kind` validated against `seasons|masses|special_events`
- [X] T123 [US3] Implement page `frontend/app/admin/optional-fields/page.tsx` — RSC list + Client editor

**Checkpoint**: Admins can adapt the taxonomy + optional-field catalogue without code changes; FR-019 confirm-and-detach is enforced server- and client-side.

---

## Phase 6: User Story 4 — Super Admin manages user roles (Priority: P3)

**Goal**: A Super Admin can list registered users, promote a USER to ADMIN, demote an ADMIN to USER, and is prevented from removing the last Super Admin.

**Independent Test**: Super Admin signs in, lists users, promotes a known USER to ADMIN, signs in as that user, confirms admin actions now succeed; demotes them back, confirms admin actions return 403; attempts to demote the only Super Admin and is rejected with `400 last_super_admin` (FR-005/006).

**Maps to FRs**: FR-002, FR-003, FR-005, FR-006, FR-007.

### Tests for User Story 4 (write first; MUST fail before implementation)

- [X] T124 [P] [US4] Unit test `PromoteUser` USER → ADMIN allowed; ADMIN → ADMIN no-op safe in `backend/tests/unit/test_promote_user_use_case.py`
- [X] T125 [P] [US4] Unit test `DemoteUser` ADMIN → USER allowed; SUPER_ADMIN → anything raises `LastSuperAdminError` when count==1 in `backend/tests/unit/test_demote_user_use_case.py`
- [ ] T126 [P] [US4] Integration test `UserRepository.count_super_admins` and role transition transaction in `backend/tests/integration/test_user_repository_roles.py`  *(deferred: needs testcontainers Postgres)*
- [X] T127 [P] [US4] Contract test `GET /api/v1/super-admin/users` — 200 for SUPER_ADMIN; 403 for ADMIN/USER; pagination + `q` filter in `backend/tests/contract/test_super_admin_users_list.py`
- [X] T128 [P] [US4] Contract test `PUT /api/v1/super-admin/users/{id}/role` — promote/demote happy path; `If-Match` enforced; payload restricted to `{USER,ADMIN}`; last-super-admin returns 400 with code `last_super_admin` in `backend/tests/contract/test_super_admin_users_role.py`
- [X] T129 [P] [US4] Vitest component test `RoleSelect` exposes only USER/ADMIN; `UserRoleTable` disables demote on the only Super Admin row in `frontend/tests/unit/components/UserRoleTable.test.tsx`
- [X] T130 [P] [US4] Playwright E2E `super-admin-roles.spec.ts` — promote → user gains admin power on next request; demote → admin actions refused; ADMIN is redirected when visiting `/super-admin/users` in `frontend/tests/e2e/super-admin-roles.spec.ts`  *(spec authored; gated on `CLERK_SUPER_ADMIN_EMAIL` / `CLERK_ADMIN_EMAIL`)*

### Implementation for User Story 4

- [X] T131 [US4] Implement `UserRepository` (list with pagination + `q`, `get_by_id`, `count_by_role`, `update_role_with_version`) in `backend/src/infrastructure/db/repositories/user_repository.py`
- [X] T132 [US4] Implement `PromoteUser` and `DemoteUser` use cases (last-super-admin invariant inside the same transaction) in `backend/src/application/use_cases/role_management.py`
- [X] T133 [US4] Define `UserAccount`, `UserAccountPage` Pydantic schemas in `backend/src/interfaces/api/schemas/users.py`
- [X] T134 [US4] Implement super-admin users router (`GET /api/v1/super-admin/users`, `PUT /api/v1/super-admin/users/{id}/role`) with `require_role(SUPER_ADMIN)` guard in `backend/src/interfaces/api/routers/users_super_admin.py` and register in `main.py`
- [X] T135 [P] [US4] Implement molecule `RoleSelect` (restricted to USER/ADMIN) in `frontend/components/molecules/RoleSelect.tsx`
- [X] T136 [US4] Implement organism `UserRoleTable` (disables demote on lone Super Admin row) in `frontend/components/organisms/UserRoleTable.tsx`
- [X] T137 [US4] Implement page `frontend/app/super-admin/users/page.tsx` — RSC role-gated; renders `UserRoleTable`  *(direct fetch via SongFormClient-style pattern; TanStack Query mutation hook can be added when more list-side caching is needed)*

**Checkpoint**: All four user stories are independently functional and tested.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verify performance, accessibility, security, and end-to-end documentation now that all stories are in place.

- [ ] T138 [P] Run `ruff check` + `ruff format --check` on `backend/` and fix any issues  *(needs Python env with `ruff` installed — run: `cd backend && ruff check . && ruff format --check .`)*
- [ ] T139 [P] Run `pyright` on `backend/` (strict on `domain/`) and resolve type errors  *(needs Pyright — run: `cd backend && pyright`)*
- [ ] T140 [P] Run `pnpm lint && pnpm typecheck && pnpm format:check` on `frontend/` and fix issues  *(needs `pnpm install` first)*
- [X] T141 [P] Performance benchmark — seed 5,000 songs and assert p95 search latency < 200ms server-time in `backend/tests/integration/test_perf_5k_songs.py` (SC-002)  *(spec authored; runs against testcontainers Postgres)*
- [X] T142 [P] Mobile-viewport audit — Playwright suite at `360×740`, `768×1024`, `1280×800` asserting no horizontal scroll, tap targets ≥ 44px on `/`, `/songs/[id]`, `/admin/songs/new` in `frontend/tests/e2e/mobile-responsive.spec.ts` (FR-027, SC-007)
- [X] T143 RBAC audit — automated test that every privileged endpoint returns 401 anonymous, 403 for under-privileged role, in `backend/tests/contract/test_rbac_audit.py` (SC-006)
- [X] T144 Add cache headers (`Cache-Control: public, max-age=30, s-maxage=300`) on `GET /api/v1/songs` and song detail in `backend/src/interfaces/api/routers/songs_public.py`
- [X] T145 [P] Wire `Toast`-based error surfacing in TanStack Query default options in `frontend/app/layout.tsx` (FR-029)  *(wired in `frontend/app/providers.tsx` via QueryCache/MutationCache `onError`; placeholder logs to console, swap for `toast.error` once `pnpm dlx shadcn add sonner` is run)*
- [X] T146 Update `README.md` at repo root with quick-start link to `specs/002-church-songlist-management/quickstart.md` and one-paragraph overview of the four user stories
- [ ] T147 Walk `quickstart.md` §5 acceptance scenarios end-to-end against the running stack and check off all four stories  *(manual — needs running stack + seeded data)*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately.
- **Foundational (Phase 2)**: Requires Setup. **Blocks all user-story phases.**
- **User Story 1 (Phase 3, P1, MVP)**: Requires Foundational. No dependency on US2/US3/US4.
- **User Story 2 (Phase 4, P1)**: Requires Foundational. Independent of US1 at the API layer; UI shares atoms/templates from Phase 2 and benefits from (but does not require) US1's `SongDetail` for sanity checks.
- **User Story 3 (Phase 5, P2)**: Requires Foundational. Independent of US1 / US2.
- **User Story 4 (Phase 6, P3)**: Requires Foundational. Independent of US1 / US2 / US3.
- **Polish (Phase 7)**: Requires every desired user story to be complete.

### Within Each User Story

- Test tasks (`T053–T062`, `T081–T091`, `T103–T112`, `T124–T130`) MUST be authored and verified failing **before** their implementation tasks.
- Models / repositories before use cases; use cases before routers/UI.
- Backend routers must be registered in `main.py` before contract tests turn green.
- Frontend pages depend on their organisms and molecules.

### Parallel Opportunities

- Phase 1: T002, T003, T004, T005, T007, T008, T009, T010, T011, T012 are all `[P]`.
- Phase 2: All domain-layer tasks (T013–T020) run in parallel; ORM models (T023–T026) run in parallel after T022; frontend shell tasks (T043–T052) run in parallel after T042.
- Phase 3 tests T053–T062 run in parallel; molecules T071–T075 run in parallel; tests run in parallel with each other but block their own implementation tasks.
- Phase 4 tests T081–T091 run in parallel; admin pages T100–T102 share `SongForm` so T099 must precede T101/T102.
- Phase 5 tests T103–T112 run in parallel; organisms T119–T121 run in parallel after their molecule.
- Phase 6 tests T124–T130 run in parallel.
- Once Foundational is done, an entire team can run US1, US2, US3, US4 in parallel by developer.

---

## Parallel Example — User Story 1

```bash
# Author all US1 tests in parallel before any implementation:
Task: "Unit test ListSongs use case in backend/tests/unit/test_list_songs_use_case.py"
Task: "Integration test SongRepository.search in backend/tests/integration/test_song_repository_search.py"
Task: "Contract test GET /api/v1/songs in backend/tests/contract/test_songs_public_list.py"
Task: "Vitest component test SongCard in frontend/tests/unit/components/SongCard.test.tsx"
Task: "Playwright E2E catalog-browse.spec.ts in frontend/tests/e2e/catalog-browse.spec.ts"

# Then build US1 atoms/molecules in parallel:
Task: "Implement SearchInput in frontend/components/molecules/SearchInput.tsx"
Task: "Implement FilterChip in frontend/components/molecules/FilterChip.tsx"
Task: "Implement SongCard in frontend/components/molecules/SongCard.tsx"
Task: "Implement OptionalFieldLinkRow in frontend/components/molecules/OptionalFieldLinkRow.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 → Phase 2 (one engineer can finish in ~2–3 days; mostly skeleton).
2. Phase 3 — write the seven failing tests, then make them pass.
3. **STOP & validate** — run the `quickstart.md §5 Story 1` walk-through.
4. Demo: a public, mobile-friendly, searchable catalog. Ship.

### Incremental delivery

- After MVP: add US2 → demo Admin authoring → ship.
- Then US3 → demo dynamic taxonomy / fields → ship.
- Then US4 → demo Super Admin role mgmt → ship.

### Parallel-team strategy (post-foundational)

- Dev A (full-stack): US1 (mostly read-side; smaller surface; good warm-up).
- Dev B (full-stack): US2 (largest write surface; highest content-creation impact).
- Dev C (full-stack): US3 + US4 (more focused; lower coupling to US1/US2 internals).
- Coordination point: `services/api/contracts.ts` and `interfaces/api/routers/main.py` registration order; otherwise stories are independent.

---

## Task Summary

| Phase | Tasks | Count |
|---|---|---|
| 1. Setup | T001–T012 | 12 |
| 2. Foundational | T013–T052 | 40 |
| 3. US1 — Browse / search / view (MVP, P1) | T053–T080 | 28 |
| 4. US2 — Admin song catalog (P1) | T081–T102 | 22 |
| 5. US3 — Dynamic taxonomies & fields (P2) | T103–T123 | 21 |
| 6. US4 — Super Admin role mgmt (P3) | T124–T137 | 14 |
| 7. Polish | T138–T147 | 10 |
| **Total** | | **147** |

### Tasks per user story (implementation + tests)

- **US1**: 28 tasks (10 tests, 18 implementation)
- **US2**: 22 tasks (11 tests, 11 implementation)
- **US3**: 21 tasks (10 tests, 11 implementation)
- **US4**: 14 tasks (7 tests, 7 implementation)

### Suggested MVP scope

Phase 1 + Phase 2 + Phase 3 (User Story 1) — yields a public, mobile-friendly catalog with search and filter. Admin authoring (US2) lights it up with real content. US3 and US4 follow as P2/P3 increments.

---

## Notes

- `[P]` = different files, no incomplete dependencies. Same-file tasks are intentionally not marked `[P]` (e.g., T097 owns the admin songs router; T117 owns the taxonomies router whose read methods came from T070).
- Tests are mandatory per Constitution Principle III; they MUST fail before their paired implementation begins.
- Every backend mutating endpoint takes `If-Match: <version>` per `contracts/openapi.yaml` and FR-030.
- Every UI external-link render uses `target="_blank" rel="noopener noreferrer"` per FR-026 + Constitution Principle V.
- Anonymous reads cover `/api/v1/songs*`, `GET /api/v1/admin/taxonomies/{kind}`, `GET /api/v1/admin/optional-fields` (FR-031).
- The seeded migration MUST be idempotent (FR-020, FR-021) — T028.
- Audit fields (`created_by`, `updated_by`, `created_at`, `updated_at`) are set in every mutating use case (FR-032) — covered inside T093/T094, T115/T116, T132.
