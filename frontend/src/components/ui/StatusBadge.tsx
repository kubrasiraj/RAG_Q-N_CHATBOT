import { cn } from '@/lib/utils';
import type { DocumentStatus } from '@/features/documents/types';

const styles: Record<DocumentStatus, { label: string; classes: string; dot: string }> = {
  pending: { label: 'Pending', classes: 'border-warn/40 bg-warn/10 text-warn', dot: 'bg-warn' },
  processing: { label: 'Processing', classes: 'border-brand-mint/40 bg-brand-mint/10 text-brand-mint', dot: 'bg-brand-mint animate-pulse' },
  completed: { label: 'Completed', classes: 'border-brand/50 bg-brand/15 text-brand-mint', dot: 'bg-brand' },
  failed: { label: 'Failed', classes: 'border-danger/40 bg-danger/10 text-danger', dot: 'bg-danger' },
};

export function StatusBadge({ status, className }: { status: DocumentStatus; className?: string }) {
  const s = styles[status];
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium', s.classes, className)}>
      <span className={cn('h-1.5 w-1.5 rounded-full', s.dot)} aria-hidden="true" />
      {s.label}
    </span>
  );
}
