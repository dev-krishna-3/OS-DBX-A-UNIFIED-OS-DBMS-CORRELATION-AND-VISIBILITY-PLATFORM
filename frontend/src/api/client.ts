type RequestOptions = Omit<RequestInit, 'headers'> & { headers?: HeadersInit };

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '');
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
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
