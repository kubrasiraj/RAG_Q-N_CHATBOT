import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { AuthProvider } from '@/features/auth/AuthProvider';
import { ApiError } from '@/lib/errors';

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        // Client errors (4xx) will not change on retry; only transient failures are retried.
        retry: (failureCount, error) => failureCount < 2 && !(error instanceof ApiError && error.status !== undefined && error.status < 500),
      },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
        <Toaster
          theme="dark"
          position="top-right"
          toastOptions={{
            style: { background: 'rgb(var(--c-card))', border: '1px solid rgb(var(--c-line))', color: 'rgb(var(--c-ink))' },
          }}
        />
      </AuthProvider>
    </QueryClientProvider>
  );
}
