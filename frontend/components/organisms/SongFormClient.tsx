// SongFormClient — Client Component wrapper that wires the SongForm to the
// fetch-based ApiClient + Clerk's `useAuth().getToken()` on the client side.
"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { toast } from "sonner";
import type {
  OptionalFieldDefinition,
  SongDetail,
  TaxonomyValue,
} from "@/types/api";
import type { SongWriteInput } from "@/services/api/contracts";
import { createClientApiClient } from "@/services/api/client";
import { SongForm } from "@/components/organisms/SongForm";

export interface SongFormClientProps {
  mode: "create" | "edit";
  initial?: SongDetail;
  seasons: TaxonomyValue[];
  masses: TaxonomyValue[];
  specialEvents: TaxonomyValue[];
  optionalFieldDefinitions: OptionalFieldDefinition[];
}

export function SongFormClient(props: SongFormClientProps) {
  const { getToken } = useAuth();
  const router = useRouter();
  const api = useMemo(
    () => createClientApiClient(async () => (await getToken()) ?? null),
    [getToken]
  );

  async function handleSubmit(values: SongWriteInput) {
    if (props.mode === "create") {
      const created = await api.songs.create(values);
      toast.success("Song created");
      router.push(`/songs/${created.id}`);
      return;
    }
    if (!props.initial) throw new Error("edit mode requires `initial`");
    const updated = await api.songs.update(
      props.initial.id,
      props.initial.version,
      values
    );
    toast.success("Song updated");
    router.push(`/songs/${updated.id}`);
  }

  function handleRefresh() {
    router.refresh();
  }

  return (
    <SongForm
      mode={props.mode}
      initial={props.initial}
      seasons={props.seasons}
      masses={props.masses}
      specialEvents={props.specialEvents}
      optionalFieldDefinitions={props.optionalFieldDefinitions}
      onSubmit={handleSubmit}
      onRefresh={handleRefresh}
    />
  );
}
