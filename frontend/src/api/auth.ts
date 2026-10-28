import { apiRequest, postJson, setAccessToken } from './client';

export interface AuthUser {
  user_id: number;
  username: string;
  email: string | null;
  uid_linux: number;
  is_admin: boolean;
  created_at: string;
}

export interface AuthResult {
  access_token: string;
  token_type: 'bearer';
  email_notification_sent: boolean;
}

export interface RegistrationResult extends AuthUser {
  email_notification_sent: boolean;
}

export interface RegisterRequest {
  username: string;
  email: string;
  uid_linux: number;
  password: string;
}

export const authApi = {
  async signIn(username: string, password: string): Promise<AuthResult> {
    const body = new URLSearchParams({ username, password });
    const result = await apiRequest<AuthResult>('/auth/token', {
      method: 'POST',
      body,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    setAccessToken(result.access_token);
    return result;
  },

  signUp(payload: RegisterRequest): Promise<RegistrationResult> {
    return postJson<RegistrationResult>('/auth/register', payload);
  },

  currentUser(): Promise<AuthUser> {
    return apiRequest<AuthUser>('/auth/me');
  },

  signOut(): void {
    setAccessToken(null);
  },
};
