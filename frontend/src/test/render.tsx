import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

export function renderWithProviders(ui: ReactElement, route = '/') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

export const sampleDocument = {
  id: '11111111-1111-4111-8111-111111111111',
  original_filename: 'handbook.pdf',
  mime_type: 'application/pdf',
  file_size_bytes: 2048,
  status: 'completed' as const,
  page_count: 12,
  created_at: '2026-11-01T10:00:00Z',
  updated_at: '2026-11-01T10:05:00Z',
  processed_at: '2026-11-01T10:05:00Z',
};
