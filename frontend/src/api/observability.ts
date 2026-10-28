import { apiRequest, postJson } from './client';

export const observabilityApi = {
  events: <T>() => apiRequest<T[]>('/events'),
  processes: <T>() => apiRequest<T[]>('/os-events/processes'),
  resources: <T>() => apiRequest<T>('/os-events/resources'),
  dbmsObservations: <T>() => apiRequest<T[]>('/dbms-events/observations'),
  collectorStatus: <T>() => apiRequest<T>('/dbms-events/status'),
  collectDbmsEvents: <T>(payload: unknown) => postJson<T>('/dbms-events/collect', payload),
};
