import { apiRequest, postJson } from './client';

export const analysisApi = {
  performanceRecords: <T>() => apiRequest<T[]>('/performance/records'),
  createPerformanceRecord: <T>(payload: unknown) => postJson<T>('/performance/records', payload),
  systemHealth: <T>() => apiRequest<T>('/performance/system-health'),
  scenarios: <T>() => apiRequest<T[]>('/what-if/scenarios'),
  getScenario: <T>(id: number) => apiRequest<T>(`/what-if/scenarios/${id}`),
  saveScheduleScenario: <T>(payload: unknown) => postJson<T>('/what-if/schedules', payload),
  saveRecoveryScenario: <T>(payload: unknown) => postJson<T>('/what-if/recovery', payload),
  saveOsScenario: <T>(payload: unknown) => postJson<T>('/what-if/os', payload),
  auditLog: <T>(limit = 50) => apiRequest<T[]>(`/audit/?limit=${limit}`),
  benchmarkScenarios: <T>() => apiRequest<T[]>('/v1/benchmarks/scenarios'),
  runBenchmark: <T>(payload: unknown) => postJson<T>('/v1/benchmarks/run', payload),
};
