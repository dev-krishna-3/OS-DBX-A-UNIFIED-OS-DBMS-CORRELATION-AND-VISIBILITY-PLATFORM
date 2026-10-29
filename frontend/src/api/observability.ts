import { apiRequest, postJson } from './client';

export const observabilityApi = {
  events: <T>(limit = 100) => apiRequest<T[]>(`/events?limit=${limit}`),
  processes: <T>(limit = 100) => apiRequest<T[]>(`/os-events/processes?limit=${limit}`),
  resources: <T>(limit = 100) => apiRequest<T>(`/os-events/resources?limit=${limit}`),
  osCollectorStatus: <T>() => apiRequest<T>('/os-events/status'),
  osMetrics: <T>() => apiRequest<T>('/os-events/metrics'),
  filesystemEvents: <T>(limit = 100) => apiRequest<T[]>(`/os-events/filesystem?limit=${limit}`),
  dbmsObservations: <T>(limit = 100) => apiRequest<T[]>(`/dbms-events/observations?limit=${limit}`),
  collectorStatus: <T>() => apiRequest<T>('/dbms-events/status'),
  collectDbmsEvents: <T>(payload: unknown) => postJson<T>('/dbms-events/collect', payload),
};
