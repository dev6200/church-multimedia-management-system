import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "tok" }),
  ClerkProvider: ({ children }: { children: ReactNode }) => children,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

const taxonomiesCreate = vi.fn();
vi.mock("@/services/api/client", () => ({
  createClientApiClient: () => ({
    taxonomies: {
      create: taxonomiesCreate,
    },
  }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { TaxonomyValueEditor } from "@/components/organisms/TaxonomyValueEditor";
import { toast } from "sonner";

afterEach(() => {
  cleanup();
  vi.mocked(toast.success).mockClear();
  vi.mocked(toast.error).mockClear();
  taxonomiesCreate.mockReset();
});

describe("TaxonomyValueEditor success toast", () => {
  it("fires toast.success with `<name> added` after a successful add", async () => {
    taxonomiesCreate.mockResolvedValueOnce({
      id: "x",
      kind: "SEASON",
      name: "Lent II",
      version: 1,
      created_at: "2026-05-03T00:00:00Z",
      updated_at: "2026-05-03T00:00:00Z",
    });

    render(<TaxonomyValueEditor kind="SEASON" initialValues={[]} />);

    await userEvent.type(
      screen.getByPlaceholderText("Add a new value"),
      "Lent II"
    );
    await userEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Lent II added");
    });
  });
});
