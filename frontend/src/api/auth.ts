import { apiRequest, postJson, setAccessToken } from './client';

export interface AuthUser {
  user_id: number;
  username: string;
  email: string | null;
  email_verified: boolean;
  totp_enabled: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface LoginStepResult {
  access_token: string | null;
  token_type: 'bearer';
  requires_totp: boolean;
  requires_totp_setup: boolean;
  challenge_token: string | null;
  email_notification_sent: boolean;
}

export interface RegistrationResult extends AuthUser {
  email_notification_sent: boolean;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  verification_code: string;
}

export interface TotpSetupResult {
  secret: string;
  provisioning_uri: string;
  qr_code_data_url: string;
}

export interface TotpEnableResult {
  access_token: string;
  token_type: 'bearer';
  email_notification_sent: boolean;
  recovery_codes: string[];
}

export interface AuthResult {
  access_token: string;
  token_type: 'bearer';
  email_notification_sent: boolean;
}

export const authApi = {
  async signIn(email: string, password: string): Promise<LoginStepResult> {
    const body = new URLSearchParams({ username: email, password });
    return apiRequest<LoginStepResult>('/auth/token', {
      method: 'POST',
      body,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },

  signUp(payload: RegisterRequest): Promise<RegistrationResult> {
    return postJson<RegistrationResult>('/auth/register', payload);
  },

  startEmailVerification(email: string): Promise<{ verification_email_sent: boolean }> {
    return postJson('/auth/email-verification/start', { email });
  },

  startTotpSetup(challengeToken: string): Promise<TotpSetupResult> {
    return postJson('/auth/totp/setup', { challenge_token: challengeToken });
  },

  async enableTotp(challengeToken: string, code: string): Promise<TotpEnableResult> {
    return postJson('/auth/totp/enable', { challenge_token: challengeToken, code });
  },

  async verifyTotp(challengeToken: string, code: string, remember: boolean): Promise<AuthResult> {
    const result = await postJson<AuthResult>('/auth/totp/verify', { challenge_token: challengeToken, code });
    setAccessToken(result.access_token, remember);
    return result;
  },

  activateSession(token: string, remember: boolean): void {
    setAccessToken(token, remember);
  },

  currentUser(): Promise<AuthUser> {
    return apiRequest<AuthUser>('/auth/me');
  },

  signOut(): void {
    setAccessToken(null);
  },
};
