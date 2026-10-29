import { apiRequest, postJson } from './client';

export const workflowsApi = {
  transactions: <T>(limit = 100) => apiRequest<T[]>(`/transactions?limit=${limit}`),
  locks: <T>(limit = 100) => apiRequest<T[]>(`/locks?limit=${limit}`),
  beginTransaction: <T>(payload: unknown) => postJson<T>('/transactions/begin', payload),
  transactionAction: <T>(transactionId: number, action: 'read' | 'write' | 'commit' | 'rollback', payload?: unknown) =>
    action === 'read' || action === 'write'
      ? postJson<T>(`/transactions/${transactionId}/${action}`, payload ?? {})
      : apiRequest<T>(`/transactions/${transactionId}/${action}`, { method: 'POST' }),
  acquireLock: <T>(payload: unknown) => postJson<T>('/locks', payload),
  trackQuery: <T>(payload: unknown) => postJson<T>('/query-executions', payload),
  detectDeadlock: <T>(payload: unknown) => postJson<T>('/deadlocks/detect', payload),
  detectLiveDeadlock: <T>() => apiRequest<T>('/deadlocks/detect/live', { method: 'POST' }),
  analyzeSchedule: <T>(payload: unknown) => postJson<T>('/schedules/analyze', payload),
  recover: <T>(payload: unknown) => postJson<T>('/recovery/recover', payload),
  createAuditEntry: <T>(payload: unknown) => postJson<T>('/audit/', payload),
  osCollectorStatus: <T>() => apiRequest<T>('/os-events/status'),
  filesystemEvents: <T>() => apiRequest<T[]>('/os-events/filesystem'),
};
