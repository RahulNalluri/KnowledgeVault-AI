export type ApiErrorDetails = Record<string, string[] | string | unknown>;

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: ApiErrorDetails;
    request_id: string;
  };
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  avatar: string | null;
  is_email_verified: boolean;
  date_joined: string;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface RegisteredUser {
  id: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  created_at: string;
}

export interface AccessTokenResponse {
  access: string;
  token_type: "Bearer";
  expires_in: number;
  csrf_token: string;
}

export interface LoginResponse extends AccessTokenResponse {
  user: RegisteredUser;
}

export interface MessageResponse {
  message: string;
}
