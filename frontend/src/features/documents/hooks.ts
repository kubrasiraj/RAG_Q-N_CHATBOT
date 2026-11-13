import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from './api';
import type { DocumentItem } from './types';

export const documentKeys = {
  all: ['documents'] as const,
  list: (skip: number, limit: number) => ['documents', 'list', skip, limit] as const,
  detail: (id: string) => ['documents', 'detail', id] as const,
};

const POLL_PROCESSING_MS = 3000;
const POLL_PENDING_MS = 5000;

/**
 * How often to re-check the API. Polling continues only while a document is pending or processing
 * and stops as soon as every document is completed or failed. Returns false to stop.
 */
export function documentPollInterval(items: readonly DocumentItem[] | undefined): number | false {
  if (!items) return false;
  if (items.some((d) => d.status === 'processing')) return POLL_PROCESSING_MS;
  if (items.some((d) => d.status === 'pending')) return POLL_PENDING_MS;
  return false;
}

/**
 * Lists documents from the API. Status changes made by the backend's background processing show
 * up on their own, because the list keeps re-fetching while anything is still in progress.
 */
export function useDocuments(skip = 0, limit = 12) {
  return useQuery({
    queryKey: documentKeys.list(skip, limit),
    queryFn: ({ signal }) => documentsApi.list({ skip, limit }, signal),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: true,
    refetchInterval: (query) => documentPollInterval(query.state.data?.items),
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: documentKeys.detail(id ?? ''),
    queryFn: ({ signal }) => documentsApi.get(id as string, signal),
    enabled: id !== null,
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentKeys.all }),
  });
}

export function useInvalidateDocuments() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: documentKeys.all });
}
