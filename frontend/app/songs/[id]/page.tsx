// Song detail page (T080) — RSC. Fetches the song detail, renders SongDetailView.
// 404 path uses Next.js `notFound()` so the framework's not-found UI takes over.
import { notFound } from "next/navigation";
import { ApiError, type SongDetail } from "@/types/api";
import { createServerApiClient } from "@/services/api/client";
import { CatalogPageLayout } from "@/components/templates/CatalogPageLayout";
import { SongDetailView } from "@/components/organisms/SongDetail";
import { ErrorState } from "@/components/atoms/ErrorState";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function SongDetailPage({ params }: PageProps) {
  const { id } = await params;
  const api = await createServerApiClient();
  let song: SongDetail | null = null;
  let fetchError: unknown = null;
  try {
    song = await api.songs.get(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    fetchError = err;
  }
  return (
    <CatalogPageLayout filterSlot={null} title="Song detail">
      {song ? (
        <SongDetailView song={song} />
      ) : (
        <ErrorState error={fetchError} />
      )}
    </CatalogPageLayout>
  );
}
