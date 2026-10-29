import { apiRequest, postJson } from './client';

export const simulationsApi = {
  schedule: <T>(payload: unknown) => postJson<T>('/simulations/scheduling', payload),
  memory: <T>(payload: unknown) => postJson<T>('/simulations/memory', payload),
  bankerDeadlock: <T>(payload: unknown) => postJson<T>('/simulations/deadlock/bankers', payload),
  resourceGraphDeadlock: <T>(payload: unknown) => postJson<T>('/simulations/deadlock/rag', payload),
  disk: <T>(payload: unknown) => postJson<T>('/simulations/disk', payload),
  synchronization: <T>(payload: unknown) => postJson<T>('/simulations/sync', payload),
  history: <T>() => apiRequest<T[]>('/simulations/history'),
};
