import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/(auth)/login/page";

const login = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ login }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe("login page", () => {
  beforeEach(() => {
    login.mockReset();
    replace.mockReset();
  });

  it("shows client-side validation before sending credentials", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter a valid email address.")).toBeVisible();
    expect(login).not.toHaveBeenCalled();
  });

  it("submits valid credentials and enters the protected application", async () => {
    const user = userEvent.setup();
    login.mockResolvedValue(undefined);
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "person@example.com");
    await user.type(screen.getByLabelText("Password"), "private-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(login).toHaveBeenCalledWith({
      email: "person@example.com",
      password: "private-password",
    });
    expect(replace).toHaveBeenCalledWith("/dashboard");
  });
});
