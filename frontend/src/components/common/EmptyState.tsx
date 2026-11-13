import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="relative flex flex-col items-center overflow-hidden rounded-2xl border border-dashed border-line px-6 py-14 text-center">
      <div className="ambient pointer-events-none absolute inset-0" aria-hidden="true" />
      <div className="relative mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-brand/30 bg-brand-deep/40 text-brand-mint shadow-glow">
        {icon}
      </div>
      <h3 className="relative text-lg font-semibold">{title}</h3>
      <p className="relative mt-1.5 max-w-md text-sm text-ink-soft">{description}</p>
      {action && <div className="relative mt-6">{action}</div>}
    </div>
  );
}
