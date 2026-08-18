import axios, { AxiosError } from "axios";

import type { AccessTokenResponse, ApiErrorEnvelope } from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});

let accessToken: string | null = null;
let csrfToken: string | null = null;
let refreshPromise: Promise<string> | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function clearClientCredentials(): void {
  accessToken = null;
  csrfToken = null;
}

export function onSessionInvalidated(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export function toApiError(error: unknown): ApiErrorEnvelope["error"] {
  if (axios.isAxiosError<ApiErrorEnvelope>(error) && error.response?.data?.error) {
    return error.response.data.error;
  }
  return {
    code: "NETWORK_ERROR",
    message: "We could not reach the server. Please try again.",
    details: {},
    request_id: "",
  };
}

export function fieldError(error: unknown, field: string): string | undefined {
  const detail = toApiError(error).details[field];
  if (Array.isArray(detail)) {
    return detail.map(String).join(" ");
  }
  return typeof detail === "string" ? detail : undefined;
}

export async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await api.get<{ csrf_token: string }>("/auth/csrf/", {
    skipAuthRefresh: true,
  });
  csrfToken = response.data.csrf_token;
  return csrfToken;
}

export function acceptAuthResponse(response: AccessTokenResponse): void {
  accessToken = response.access;
  csrfToken = response.csrf_token;
}

export async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const csrf = await ensureCsrfToken();
    const response = await api.post<AccessTokenResponse>(
      "/auth/refresh/",
      {},
      {
        headers: { "X-CSRFToken": csrf },
        skipAuthRefresh: true,
      },
    );
    acceptAuthResponse(response.data);
    return response.data.access;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorEnvelope>) => {
    const request = error.config;
    if (
      error.response?.status !== 401 ||
      !request ||
      request.skipAuthRefresh ||
      request.authRetryAttempted ||
      !accessToken
    ) {
      return Promise.reject(error);
    }

    request.authRetryAttempted = true;
    try {
      const replacement = await refreshAccessToken();
      request.headers.Authorization = `Bearer ${replacement}`;
      return await api(request);
    } catch (refreshError) {
      clearClientCredentials();
      unauthorizedHandler?.();
      return Promise.reject(refreshError);
    }
  },
);
