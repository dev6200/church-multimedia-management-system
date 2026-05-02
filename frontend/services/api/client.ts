// Concrete ApiClient — fetch wrapper that injects the Clerk Bearer token via
// `auth().getToken()` (server) or `useAuth().getToken()` (client). Per the
// frontend-ui contract §4 a single typed client is shared between RSC and
// client paths.
import { ApiError, type ApiErrorBody } from "@/types/api";
import {
  type ApiClient,
  type AuthApi,
  type OptionalFieldsApi,
  type SongsApi,
  type SongWriteInput,
  type TaxonomiesApi,
  type UsersApi,
  TAXONOMY_KIND_TO_SLUG,
} from "./contracts";
import type {
  OptionalFieldDefinition,
  Page,
  Role,
  SongDetail,
  SongSummary,
  TaxonomyKind,
  TaxonomyValue,
  UserAccount,
} from "@/types/api";

export type TokenProvider = () => Promise<string | null>;

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<
    string,
    string | number | boolean | string[] | undefined | null
  >;
  ifMatch?: number;
  expectNoContent?: boolean;
}

export class FetchApiClient implements ApiClient {
  readonly songs: SongsApi;
  readonly taxonomies: TaxonomiesApi;
  readonly optionalFields: OptionalFieldsApi;
  readonly users: UsersApi;
  readonly auth: AuthApi;

  constructor(
    private readonly baseUrl: string,
    private readonly tokenProvider: TokenProvider
  ) {
    this.songs = this._songsApi();
    this.taxonomies = this._taxonomiesApi();
    this.optionalFields = this._optionalFieldsApi();
    this.users = this._usersApi();
    this.auth = this._authApi();
  }

  // ------------------------------------------------------------- core fetch
  private async request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const url = new URL(path, this.baseUrl);
    if (opts.query) {
      for (const [key, value] of Object.entries(opts.query)) {
        if (value === undefined || value === null) continue;
        if (Array.isArray(value)) {
          for (const v of value) url.searchParams.append(key, String(v));
        } else {
          url.searchParams.set(key, String(value));
        }
      }
    }
    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (opts.ifMatch !== undefined) headers["If-Match"] = String(opts.ifMatch);
    const token = await this.tokenProvider();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(url.toString(), {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      cache: "no-store",
    });

    if (response.status === 204 || opts.expectNoContent) {
      if (!response.ok) await this._throwApiError(response);
      return undefined as T;
    }
    if (!response.ok) await this._throwApiError(response);
    return (await response.json()) as T;
  }

  private async _throwApiError(response: Response): Promise<never> {
    const status = response.status;
    let body: ApiErrorBody | { detail?: ApiErrorBody["error"] } | null = null;
    try {
      body = (await response.json()) as
        | ApiErrorBody
        | { detail?: ApiErrorBody["error"] };
    } catch {
      // body wasn't JSON — fall through with null
    }
    // Backend wraps domain errors in `{ error: {code, message, ...} }`,
    // FastAPI HTTPException uses `{ detail: {code, message, ...} }` — accept
    // both shapes.
    const errEnvelope =
      body && "error" in body
        ? body.error
        : body && "detail" in body && body.detail
          ? body.detail
          : null;
    const code = errEnvelope?.code ?? "unknown_error";
    const message = errEnvelope?.message ?? response.statusText ?? "Unknown error";
    const details =
      errEnvelope && typeof errEnvelope === "object"
        ? Object.fromEntries(
            Object.entries(errEnvelope).filter(([k]) => k !== "code" && k !== "message")
          )
        : undefined;
    throw new ApiError(status, code, message, details);
  }

  // ------------------------------------------------------------- Songs API
  private _songsApi(): SongsApi {
    return {
      list: ({ q, season, mass, specialEvent, page, pageSize }) =>
        this.request<Page<SongSummary>>("/api/v1/songs", {
          query: {
            q,
            season,
            mass,
            special_event: specialEvent,
            page,
            page_size: pageSize,
          },
        }),
      get: (id) =>
        this.request<SongDetail>(`/api/v1/songs/${encodeURIComponent(id)}`),
      create: (input: SongWriteInput) =>
        this.request<SongDetail>("/api/v1/admin/songs", {
          method: "POST",
          body: input,
        }),
      update: (id, version, input: SongWriteInput) =>
        this.request<SongDetail>(`/api/v1/songs/${encodeURIComponent(id)}`, {
          method: "PUT",
          ifMatch: version,
          body: input,
        }),
      delete: (id, version) =>
        this.request<void>(`/api/v1/songs/${encodeURIComponent(id)}`, {
          method: "DELETE",
          ifMatch: version,
          expectNoContent: true,
        }),
    };
  }

  // ------------------------------------------------------------- Taxonomies
  private _taxonomiesApi(): TaxonomiesApi {
    return {
      list: (kind: TaxonomyKind) => {
        const slug = TAXONOMY_KIND_TO_SLUG[kind];
        return this.request<TaxonomyValue[]>(`/api/v1/admin/taxonomies/${slug}`);
      },
      create: (kind, name) => {
        const slug = TAXONOMY_KIND_TO_SLUG[kind];
        return this.request<TaxonomyValue>(`/api/v1/admin/taxonomies/${slug}`, {
          method: "POST",
          body: { name },
        });
      },
      rename: (kind, id, version, name) => {
        const slug = TAXONOMY_KIND_TO_SLUG[kind];
        return this.request<TaxonomyValue>(
          `/api/v1/admin/taxonomies/${slug}/${encodeURIComponent(id)}`,
          { method: "PUT", ifMatch: version, body: { name } }
        );
      },
      usage: (kind, id) => {
        const slug = TAXONOMY_KIND_TO_SLUG[kind];
        return this.request<{ usage_count: number }>(
          `/api/v1/admin/taxonomies/${slug}/${encodeURIComponent(id)}/usage`
        );
      },
      delete: (kind, id, version, detach) => {
        const slug = TAXONOMY_KIND_TO_SLUG[kind];
        return this.request<void>(
          `/api/v1/admin/taxonomies/${slug}/${encodeURIComponent(id)}`,
          {
            method: "DELETE",
            ifMatch: version,
            query: { detach: detach },
            expectNoContent: true,
          }
        );
      },
    };
  }

  // ------------------------------------------------------------- Optional fields
  private _optionalFieldsApi(): OptionalFieldsApi {
    return {
      list: () =>
        this.request<OptionalFieldDefinition[]>("/api/v1/admin/optional-fields"),
      create: (label) =>
        this.request<OptionalFieldDefinition>("/api/v1/admin/optional-fields", {
          method: "POST",
          body: { label },
        }),
      rename: (id, version, label) =>
        this.request<OptionalFieldDefinition>(
          `/api/v1/admin/optional-fields/${encodeURIComponent(id)}`,
          { method: "PUT", ifMatch: version, body: { label } }
        ),
      usage: (id) =>
        this.request<{ usage_count: number }>(
          `/api/v1/admin/optional-fields/${encodeURIComponent(id)}/usage`
        ),
      delete: (id, version, detach) =>
        this.request<void>(
          `/api/v1/admin/optional-fields/${encodeURIComponent(id)}`,
          {
            method: "DELETE",
            ifMatch: version,
            query: { detach: detach },
            expectNoContent: true,
          }
        ),
    };
  }

  // ------------------------------------------------------------- Users
  private _usersApi(): UsersApi {
    return {
      list: ({ q, page, pageSize }) =>
        this.request<Page<UserAccount>>("/api/v1/super-admin/users", {
          query: { q, page, page_size: pageSize },
        }),
      setRole: (id, version, role: Exclude<Role, "SUPER_ADMIN">) =>
        this.request<UserAccount>(
          `/api/v1/super-admin/users/${encodeURIComponent(id)}/role`,
          { method: "PUT", ifMatch: version, body: { role } }
        ),
    };
  }

  // ------------------------------------------------------------- Auth
  private _authApi(): AuthApi {
    return {
      me: () => this.request<UserAccount>("/api/v1/auth/me"),
    };
  }
}

// ---------------------------------------------------------------- factories

export function getApiBaseUrl(): string {
  const url =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    process.env.API_BASE_URL ??
    "http://localhost:8083";
  return url.replace(/\/$/, "");
}

/** Build an ApiClient for a Server Component context (uses Clerk's `auth()`). */
export async function createServerApiClient(): Promise<FetchApiClient> {
  // Defer the dynamic import so this module remains importable from client code
  // (the client variant doesn't pull `@clerk/nextjs/server`).
  const { auth } = await import("@clerk/nextjs/server");
  const tokenProvider: TokenProvider = async () => {
    const a = await auth();
    return (await a.getToken()) ?? null;
  };
  return new FetchApiClient(getApiBaseUrl(), tokenProvider);
}

/** Build an ApiClient for a Client Component (caller passes a getToken fn). */
export function createClientApiClient(
  getToken: () => Promise<string | null>
): FetchApiClient {
  return new FetchApiClient(getApiBaseUrl(), getToken);
}
