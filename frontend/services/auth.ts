import { api, acceptAuthResponse, clearClientCredentials, ensureCsrfToken } from "@/lib/api/client";
import type {
  LoginResponse,
  MessageResponse,
  RegisteredUser,
  UserProfile,
} from "@/types/api";

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegistrationInput extends LoginInput {
  full_name: string;
}

export interface PasswordResetInput {
  token: string;
  new_password: string;
  new_password_confirmation: string;
}

export interface PasswordChangeInput {
  current_password: string;
  new_password: string;
  new_password_confirmation: string;
}

export async function login(input: LoginInput): Promise<LoginResponse> {
  const csrf = await ensureCsrfToken();
  const response = await api.post<LoginResponse>("/auth/login/", input, {
    headers: { "X-CSRFToken": csrf },
    skipAuthRefresh: true,
  });
  acceptAuthResponse(response.data);
  return response.data;
}

export async function logout(): Promise<void> {
  const csrf = await ensureCsrfToken();
  try {
    await api.post(
      "/auth/logout/",
      {},
      { headers: { "X-CSRFToken": csrf }, skipAuthRefresh: true },
    );
  } finally {
    clearClientCredentials();
  }
}

export async function register(input: RegistrationInput): Promise<RegisteredUser> {
  const response = await api.post<RegisteredUser>("/auth/register/", input, {
    skipAuthRefresh: true,
  });
  return response.data;
}

export async function getCurrentUser(): Promise<UserProfile> {
  const response = await api.get<UserProfile>("/users/me/");
  return response.data;
}

export async function updateCurrentUser(fullName: string): Promise<UserProfile> {
  const response = await api.patch<UserProfile>("/users/me/", { full_name: fullName });
  return response.data;
}

export async function requestPasswordReset(email: string): Promise<MessageResponse> {
  const response = await api.post<MessageResponse>(
    "/auth/password/reset/request/",
    { email },
    { skipAuthRefresh: true },
  );
  return response.data;
}

export async function confirmPasswordReset(input: PasswordResetInput): Promise<void> {
  await api.post("/auth/password/reset/confirm/", input, { skipAuthRefresh: true });
  clearClientCredentials();
}

export async function confirmEmailVerification(token: string): Promise<void> {
  await api.post(
    "/auth/email/verification/confirm/",
    { token },
    { skipAuthRefresh: true },
  );
}

export async function resendEmailVerification(): Promise<MessageResponse> {
  const response = await api.post<MessageResponse>("/auth/email/verification/resend/", {});
  return response.data;
}

export async function changePassword(input: PasswordChangeInput): Promise<void> {
  await api.post("/auth/password/change/", input);
  clearClientCredentials();
}
