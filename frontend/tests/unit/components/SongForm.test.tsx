// T089 — SongForm validates required fields and surfaces server-side
// duplicate / version-conflict errors via ApiError.
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SongForm } from "@/components/organisms/SongForm";
import { ApiError } from "@/types/api";

const noTaxonomies = { seasons: [], masses: [], specialEvents: [] };

describe("SongForm", () => {
  it("rejects an empty title and surfaces the validation message", async () => {
    const onSubmit = vi.fn();
    render(
      <SongForm
        mode="create"
        {...noTaxonomies}
        optionalFieldDefinitions={[]}
        onSubmit={onSubmit}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Create song" }));
    expect(await screen.findByText(/title is required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("surfaces a server-side duplicate-song error with a link to the existing song", async () => {
    const onSubmit = vi.fn().mockRejectedValueOnce(
      new ApiError(409, "conflict_duplicate_song", "Duplicate", {
        conflicting_song_id: "11111111-1111-1111-1111-111111111111",
      })
    );
    render(
      <SongForm
        mode="create"
        {...noTaxonomies}
        optionalFieldDefinitions={[]}
        onSubmit={onSubmit}
      />
    );
    await userEvent.type(screen.getByLabelText("Title"), "Salve Regina");
    await userEvent.type(
      screen.getByRole("textbox", { name: "Composer 1" }),
      "Anonymous"
    );
    await userEvent.click(screen.getByRole("button", { name: "Create song" }));

    await waitFor(() => {
      expect(screen.getByTestId("duplicate-conflict")).toBeInTheDocument();
    });
    const link = screen.getByRole("link", { name: /view the existing song/i });
    expect(link).toHaveAttribute(
      "href",
      "/songs/11111111-1111-1111-1111-111111111111"
    );
  });

  it("renders the version-conflict banner when the server returns conflict_version", async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(409, "conflict_version", "stale"));
    const onRefresh = vi.fn();
    render(
      <SongForm
        mode="edit"
        initial={{
          id: "song-1",
          title: "Salve Regina",
          composers: [{ id: "c1", name: "Anonymous" }],
          seasons: [],
          masses: [],
          special_events: [],
          optional_fields: [],
          version: 1,
          created_at: "2026-04-28T12:00:00Z",
          updated_at: "2026-04-28T12:00:00Z",
        }}
        {...noTaxonomies}
        optionalFieldDefinitions={[]}
        onSubmit={onSubmit}
        onRefresh={onRefresh}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => {
      expect(screen.getByTestId("version-conflict-banner")).toBeInTheDocument();
    });
  });
});
