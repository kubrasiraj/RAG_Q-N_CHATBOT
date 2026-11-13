import { api } from '@/lib/api-client';

export interface HealthResponse {
  status: string;
  service?: string;
  environment?: string;
  database?: string;
}

export const healthApi = {
  app: async (): Promise<HealthResponse> => (await api.get<HealthResponse>('/health', { timeout: 10_000 })).data,
  database: async (): Promise<HealthResponse> => (await api.get<HealthResponse>('/health/db', { timeout: 10_000 })).data,
};
