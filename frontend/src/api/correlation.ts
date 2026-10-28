import { postJson } from './client';

export const correlationApi = {
  correlateAutomatically: <T>(payload: unknown) => postJson<T>('/correlations/auto', payload),
  createCorrelation: <T>(payload: unknown) => postJson<T>('/correlations', payload),
};
