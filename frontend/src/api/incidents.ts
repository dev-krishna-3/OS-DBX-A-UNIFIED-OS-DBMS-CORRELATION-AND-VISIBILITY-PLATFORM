import { apiRequest } from './client';

export const incidentsApi = {
  list: <T>() => apiRequest<T[]>('/deadlocks/incidents'),
  investigation: <T>(incidentId: number) => apiRequest<T>(`/incidents/${incidentId}/investigation`),
  replay: <T>(incidentId: number) => apiRequest<T>(`/incidents/${incidentId}/replay`, { method: 'POST' }),
  blastRadius: <T>(incidentId: number) => apiRequest<T>(`/v1/incidents/${incidentId}/blast-radius`),
};
