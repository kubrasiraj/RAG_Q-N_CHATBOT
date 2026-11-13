import { api } from '@/lib/api-client';
import type { QARequest, QAResponse } from './types';

export const chatApi = {
  // Retrieval, embedding and the LLM call can take a while, so this request gets a longer timeout.
  askQuestion: async (payload: QARequest, signal?: AbortSignal): Promise<QAResponse> =>
    (await api.post<QAResponse>('/qa/ask', payload, { signal, timeout: 120_000 })).data,
};
