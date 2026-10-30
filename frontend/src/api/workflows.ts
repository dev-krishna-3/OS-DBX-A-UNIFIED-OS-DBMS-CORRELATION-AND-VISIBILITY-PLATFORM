import { apiRequest, postJson } from './client';

export const workflowsApi = {
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
  osCollectorMetrics: <T>() => apiRequest<T>('/os-events/metrics'),
  startOsCollector: <T>() => apiRequest<T>('/os-events/start', { method: 'POST' }),
  filesystemEvents: <T>() => apiRequest<T[]>('/os-events/filesystem'),
  filesystemDetectionTest: <T>() => apiRequest<T>('/console/filesystem-test', { method: 'POST' }),
  runSqlCausality: <T>(query: string) => postJson<T>('/console/sql', { query }),
  realWorldEvaluation: <T>() => apiRequest<T>('/console/real-world'),
  listTransactions: <T>(limit = 30) => apiRequest<T[]>(`/transactions?limit=${limit}`),
  listLocks: <T>(limit = 40) => apiRequest<T[]>(`/locks?limit=${limit}`),
};

