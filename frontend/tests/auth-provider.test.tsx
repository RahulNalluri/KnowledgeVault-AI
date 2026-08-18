import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "@/components/providers/auth-provider";

const replace = vi.fn();
const refreshAccessToken = vi.fn();
const clearClientCredentials = vi.fn();
const onSessionInvalidated = vi.fn();
const getCurrentUser = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("@/lib/api/client", () => ({
  refreshAccessToken: (...args: unknown[]) => refreshAccessToken(...args),
  clearClientCredentials: (...args: unknown[]) => clearClientCredentials(...args),
  onSessionInvalidated: (...args: unknown[]) => onSessionInvalidated(...args),
}));

vi.mock("@/services/auth", () => ({
  getCurrentUser: (...args: unknown[]) => getCurrentUser(...args),
  login: vi.fn(),
  logout: vi.fn(),
}));

function AuthState() {
  const { status, user } = useAuth();
  return <p>{status}:{user?.email ?? "none"}</p>;
}

const profile = {
  id: "user-id",
  email: "person@example.com",
  full_name: "Example Person",
  avatar: null,
  is_email_verified: true,
  date_joined: "2026-08-18T00:00:00Z",
  last_login: null,
  created_at: "2026-08-18T00:00:00Z",
  updated_at: "2026-08-18T00:00:00Z",
};

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("restores an authenticated browser session through refresh and profile lookup", async () => {
    refreshAccessToken.mockResolvedValue("access-token");
    getCurrentUser.mockResolvedValue(profile);

    render(<AuthProvider><AuthState /></AuthProvider>);

    expect(await screen.findByText("authenticated:person@example.com")).toBeVisible();
    expect(refreshAccessToken).toHaveBeenCalledOnce();
    expect(getCurrentUser).toHaveBeenCalledOnce();
  });

  it("settles safely as unauthenticated when refresh restoration fails", async () => {
    refreshAccessToken.mockRejectedValue(new Error("no refresh cookie"));

    render(<AuthProvider><AuthState /></AuthProvider>);

    expect(await screen.findByText("unauthenticated:none")).toBeVisible();
    expect(clearClientCredentials).toHaveBeenCalled();
    expect(getCurrentUser).not.toHaveBeenCalled();
  });
});
