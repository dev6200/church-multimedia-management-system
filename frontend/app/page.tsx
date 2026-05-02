// Catalog list page (T079) — RSC fetches songs + taxonomies in parallel,
// composes the catalog template.
import { Suspense } from "react";
import { createServerApiClient } from "@/services/api/client";
import type { Page, SongSummary, TaxonomyValue } from "@/types/api";
import { CatalogPageLayout } from "@/components/templates/CatalogPageLayout";
import { CatalogFilters } from "@/components/organisms/CatalogFilters";
import { CatalogList } from "@/components/organisms/CatalogList";
import { ErrorState } from "@/components/atoms/ErrorState";
import { LoadingSkeleton } from "@/components/atoms/LoadingSkeleton";

interface PageProps {
  searchParams: Promise<{
    q?: string | string[];
    season?: string | string[];
    mass?: string | string[];
    special_event?: string | string[];
    page?: string;
  }>;
}

function asArray(v: string | string[] | undefined): string[] {
  if (v === undefined) return [];
  return Array.isArray(v) ? v : [v];
}

function asString(v: string | string[] | undefined): string | undefined {
  if (v === undefined) return undefined;
  return Array.isArray(v) ? v[0] : v;
}

export default async function CatalogPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const q = asString(params.q);
  const seasonIds = asArray(params.season);
  const massIds = asArray(params.mass);
  const specialEventIds = asArray(params.special_event);
  const page = Number(params.page ?? "1") || 1;

  const api = await createServerApiClient();
  let pageData: Page<SongSummary>;
  let seasons: TaxonomyValue[];
  let masses: TaxonomyValue[];
  let specialEvents: TaxonomyValue[];
  let fatal: unknown = null;
  try {
    [pageData, seasons, masses, specialEvents] = await Promise.all([
      api.songs.list({
        q,
        season: seasonIds,
        mass: massIds,
        specialEvent: specialEventIds,
        page,
      }),
      api.taxonomies.list("SEASON"),
      api.taxonomies.list("MASS"),
      api.taxonomies.list("SPECIAL_EVENT"),
    ]);
  } catch (err) {
    fatal = err;
    pageData = { items: [], page: 1, page_size: 20, total: 0 };
    seasons = [];
    masses = [];
    specialEvents = [];
  }

  return (
    <CatalogPageLayout
      filterSlot={
        <CatalogFilters
          seasons={seasons}
          masses={masses}
          specialEvents={specialEvents}
          initialQ={q ?? ""}
          initialSeasonIds={seasonIds}
          initialMassIds={massIds}
          initialSpecialEventIds={specialEventIds}
        />
      }
    >
      {fatal ? (
        <ErrorState error={fatal} />
      ) : (
        <Suspense fallback={<LoadingSkeleton lines={5} />}>
          <CatalogList page={pageData} />
        </Suspense>
      )}
    </CatalogPageLayout>
  );
}
