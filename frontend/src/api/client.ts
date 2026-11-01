type RequestOptions = Omit<RequestInit, 'headers'> & { headers?: HeadersInit };

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
const apiBaseUrl = (rawBaseUrl || '').replace(/\/+$/, '');
const accessTokenKey = 'osdbx_access_token';
const workspaceIdKey = 'osdbx_workspace_id';

export function getWorkspaceId(): string | null {
  if (typeof window === 'undefined') return null;
  return window.sessionStorage.getItem(workspaceIdKey);
}

export function setWorkspaceId(id: string | number | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (id !== null && id !== undefined) {
      window.sessionStorage.setItem(workspaceIdKey, String(id));
    } else {
      window.sessionStorage.removeItem(workspaceIdKey);
    }
  } catch {
    // Keep in-memory
  }
}

function readStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    window.localStorage.removeItem(accessTokenKey);
    return window.sessionStorage.getItem(accessTokenKey);
  } catch {
    return null;
  }
}

let accessToken: string | null = readStoredToken();

export function hasAccessToken(): boolean {
  return (accessToken ?? readStoredToken()) !== null;
}

export function getAccessToken(): string | null {
  return accessToken ?? readStoredToken();
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(accessTokenKey);
    if (token) {
      window.sessionStorage.setItem(accessTokenKey, token);
    } else {
      window.sessionStorage.removeItem(accessTokenKey);
    }
  } catch {
    // Keep the in-memory token usable when browser storage is unavailable.
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = accessToken ?? readStoredToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const workspaceId = getWorkspaceId();
  if (workspaceId && !headers.has('X-Workspace-ID')) {
    headers.set('X-Workspace-ID', workspaceId);
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${apiBaseUrl}/api${path}`, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) {
      setAccessToken(null);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('osdbx:session-expired', { detail: { path } }));
      }
    }
    const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
    const detail = payload?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
      ? detail.map((item) => (typeof item === 'object' && item && 'msg' in item ? String((item as { msg: unknown }).msg) : JSON.stringify(item))).join('; ')
      : `Request failed (${response.status}).`;
    throw new Error(message);
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
