import { Loader2 } from 'lucide-react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './auth-context';

function FullScreenSpinner() {
  return (
    <div role="status" className="flex h-full items-center justify-center bg-app">
      <Loader2 className="h-8 w-8 animate-spin text-brand" aria-hidden="true" />
      <span className="sr-only">Loading your workspace</span>
    </div>
  );
}

/** UX gate only. The backend enforces authorization on every API call. */
export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === 'loading') return <FullScreenSpinner />;
  if (status === 'unauthenticated') return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { status } = useAuth();
  if (status === 'loading') return <FullScreenSpinner />;
  if (status === 'authenticated') return <Navigate to="/" replace />;
  return <Outlet />;
}
