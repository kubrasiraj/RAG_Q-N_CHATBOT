import { Link } from 'react-router-dom';
import { LogoMark } from '@/components/ui/Logo';

export function NotFoundPage() {
  return (
    <div className="ambient flex h-full flex-col items-center justify-center bg-app px-6 text-center">
      <LogoMark className="mb-6 h-12 w-12" />
      <h1 className="text-3xl font-semibold">Page not found</h1>
      <p className="mt-2 text-ink-soft">The page you are looking for does not exist.</p>
      <Link to="/" className="mt-6 rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-app hover:bg-brand-mint">
        Back to the dashboard
      </Link>
    </div>
  );
}
