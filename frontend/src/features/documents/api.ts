import { api } from '@/lib/api-client';
import type { DocumentItem, DocumentList } from './types';

export const documentsApi = {
  // The backend route is `/documents/` (trailing slash). Without it FastAPI answers with a redirect.
  list: async (params: { skip: number; limit: number }, signal?: AbortSignal): Promise<DocumentList> =>
    (await api.get<DocumentList>('/documents/', { params, signal })).data,

  get: async (id: string, signal?: AbortSignal): Promise<DocumentItem> =>
    (await api.get<DocumentItem>(`/documents/${id}`, { signal })).data,

  upload: async (file: File, onProgress?: (percent: number | undefined) => void): Promise<DocumentItem> => {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post<DocumentItem>('/documents/upload', form, {
      timeout: 120_000,
      onUploadProgress: (event) => onProgress?.(event.total ? Math.round((event.loaded / event.total) * 100) : undefined),
    });
    return response.data;
  },

  remove: async (id: string): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },
};
