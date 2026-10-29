type RequestOptions = Omit<RequestInit, 'headers'> & { headers?: HeadersInit };

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '');
const accessTokenKey = 'osdbx_access_token';

function readStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.sessionStorage.getItem(accessTokenKey) ?? window.localStorage.getItem(accessTokenKey);
  } catch {
    return null;
  }
}

let accessToken: string | null = readStoredToken();

export function hasAccessToken(): boolean {
  return accessToken !== null;
}

export function setAccessToken(token: string | null, remember = false): void {
  accessToken = token;
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(accessTokenKey);
    window.localStorage.removeItem(accessTokenKey);
    if (token) (remember ? window.localStorage : window.sessionStorage).setItem(accessTokenKey, token);
  } catch {
    // Keep the in-memory token usable when browser storage is unavailable.
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!apiBaseUrl) {
    throw new Error('API is not configured. Set VITE_API_BASE_URL in the frontend environment.');
  }

  const headers = new Headers(options.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${apiBaseUrl}/api${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status}).`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>(path, { method: 'POST', body: JSON.stringify(body) });
}

export function getJson<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}
