import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  api,
  clearClientCredentials,
  getAccessToken,
  refreshAccessToken,
  toApiError,
} from "@/lib/api/client";
import { login, logout } from "@/services/auth";

describe("browser authentication client", () => {
  beforeEach(() => {
    clearClientCredentials();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("deduplicates concurrent refresh requests and keeps tokens out of browser storage", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ data: { csrf_token: "csrf-one" } });
    const post = vi.spyOn(api, "post").mockResolvedValue({
      data: {
        access: "access-one",
        token_type: "Bearer",
        expires_in: 300,
        csrf_token: "csrf-two",
      },
    });

    const [first, second] = await Promise.all([refreshAccessToken(), refreshAccessToken()]);

    expect(first).toBe("access-one");
    expect(second).toBe("access-one");
    expect(post).toHaveBeenCalledTimes(1);
    expect(localStorage).toHaveLength(0);
    expect(getAccessToken()).toBe("access-one");
  });

  it("bootstraps CSRF for login and accepts only the returned access token", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ data: { csrf_token: "csrf-login" } });
    const post = vi.spyOn(api, "post").mockResolvedValue({
      data: {
        access: "short-lived-access",
        token_type: "Bearer",
        expires_in: 300,
        csrf_token: "rotated-csrf",
        user: {
          id: "user-id",
          email: "person@example.com",
          full_name: "Example Person",
          is_email_verified: false,
          created_at: "2026-08-18T00:00:00Z",
        },
      },
    });

    await login({ email: "person@example.com", password: "private-password" });

    expect(post).toHaveBeenCalledWith(
      "/auth/login/",
      { email: "person@example.com", password: "private-password" },
      expect.objectContaining({ headers: { "X-CSRFToken": "csrf-login" } }),
    );
    expect(getAccessToken()).toBe("short-lived-access");
    expect(localStorage).toHaveLength(0);
  });

  it("clears in-memory credentials even when logout cannot reach the API", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ data: { csrf_token: "csrf-logout" } });
    vi.spyOn(api, "post").mockRejectedValue(new Error("offline"));

    await expect(logout()).rejects.toThrow("offline");

    expect(getAccessToken()).toBeNull();
  });

  it("normalizes non-API failures into a safe network error", () => {
    expect(toApiError(new AxiosError("socket failed"))).toEqual({
      code: "NETWORK_ERROR",
      message: "We could not reach the server. Please try again.",
      details: {},
      request_id: "",
    });
  });
});
