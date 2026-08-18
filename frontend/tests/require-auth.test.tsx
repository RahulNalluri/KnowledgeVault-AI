import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequireAuth } from "@/components/auth/require-auth";

const replace = vi.fn();
let status: "initializing" | "authenticated" | "unauthenticated" = "initializing";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ replace }),
}));

vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ status }),
}));

describe("protected-route boundary", () => {
  beforeEach(() => {
    status = "initializing";
    replace.mockReset();
  });

  it("does not render private content while session restoration is in progress", () => {
    render(<RequireAuth><p>Private content</p></RequireAuth>);

    expect(screen.getByText(/restoring your secure session/i)).toBeVisible();
    expect(screen.queryByText("Private content")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated visitors without flashing private content", async () => {
    status = "unauthenticated";
    render(<RequireAuth><p>Private content</p></RequireAuth>);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login?next=%2Fdashboard"));
    expect(screen.queryByText("Private content")).not.toBeInTheDocument();
  });

  it("renders private content only after authentication succeeds", () => {
    status = "authenticated";
    render(<RequireAuth><p>Private content</p></RequireAuth>);

    expect(screen.getByText("Private content")).toBeVisible();
  });
});
