import { apiRequest, postJson, setAccessToken } from './client';

export interface AuthUser {
  user_id: number;
  uid_linux?: number;
  username: string;
  email: string | null;
  is_admin: boolean;
  email_verified?: boolean;
  totp_enabled?: boolean;
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
  password: string;
}

export interface RegistrationRequest {
  request_id: string;
  username: string;
  email: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  requested_role: string;
  approved_role?: string | null;
  reason?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
}

export interface SubmitRegistrationRequestPayload {
  username: string;
  email: string;
  password: string;
  requested_role?: string;
  reason?: string;
}

export const authApi = {
  async signIn(email: string, password: string): Promise<AuthResult> {
    const body = new URLSearchParams({ username: email, password });
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

  requestAccess(payload: SubmitRegistrationRequestPayload): Promise<RegistrationRequest> {
    return postJson<RegistrationRequest>('/auth/request-access', payload);
  },

  getRegistrationRequests(): Promise<RegistrationRequest[]> {
    return apiRequest<RegistrationRequest[]>('/auth/admin/requests');
  },

  approveRegistrationRequest(requestId: string, approvedRole: string): Promise<RegistrationRequest> {
    return postJson<RegistrationRequest>(`/auth/admin/requests/${requestId}/approve`, {
      approved_role: approvedRole,
    });
  },

  rejectRegistrationRequest(requestId: string): Promise<RegistrationRequest> {
    return postJson<RegistrationRequest>(`/auth/admin/requests/${requestId}/reject`, {});
  },

  currentUser(): Promise<AuthUser> {
    return apiRequest<AuthUser>('/auth/me');
  },

  sendVerificationEmail(): Promise<{ success: boolean; message: string; is_simulation?: boolean; demo_code?: string; email_verified?: boolean }> {
    return postJson('/auth/verify-email/send', {});
  },

  confirmVerificationEmail(code: string): Promise<{ success: boolean; message: string; email_verified: boolean }> {
    return postJson('/auth/verify-email/confirm', { code });
  },

  totpStatus(): Promise<{ totp_enabled: boolean; username: string }> {
    return apiRequest('/auth/totp/status');
  },

  totpSetup(): Promise<{ secret: string; provisioning_uri: string; qr_code_url: string }> {
    return postJson('/auth/totp/setup', {});
  },

  totpEnable(code: string): Promise<{ success: boolean; totp_enabled: boolean; message: string }> {
    return postJson('/auth/totp/enable', { code });
  },

  totpDisable(): Promise<{ success: boolean; totp_enabled: boolean; message: string }> {
    return postJson('/auth/totp/disable', {});
  },

  signOut(): void {
    setAccessToken(null);
  },
};
