import { apiRequest, postJson } from './client';

export const correlationApi = {
  correlateAutomatically: <T>(payload: unknown) => postJson<T>('/correlations/auto', payload),
  createCorrelation: <T>(payload: unknown) => postJson<T>('/correlations', payload),
  liveBridgeMap: <T>() => apiRequest<T>('/bridge/live-map'),
  demoCorrelation: <T>() => apiRequest<T>('/demo/correlation'),
};
