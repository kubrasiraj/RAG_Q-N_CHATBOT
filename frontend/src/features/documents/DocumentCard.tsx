import { Eye, FileText, MoreVertical, Trash2 } from 'lucide-react';
import { DropdownMenu } from '@/components/ui/DropdownMenu';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatBytes, formatDate } from '@/lib/utils';
import type { DocumentItem } from './types';
import { fileKind } from './validation';

interface DocumentCardProps {
  document: DocumentItem;
  onView: (document: DocumentItem) => void;
  onDelete: (document: DocumentItem) => void;
}

export function DocumentCard({ document, onView, onDelete }: DocumentCardProps) {
  return (
    <article className="surface group flex flex-col gap-4 p-5 transition-colors hover:border-brand/50">
      <div className="flex items-start gap-3.5">
        <div className="flex h-11 w-11 shrink-0 flex-col items-center justify-center rounded-xl border border-brand/25 bg-brand-deep/40 text-brand-mint">
          <FileText className="h-[18px] w-[18px]" aria-hidden="true" />
          <span className="mt-px text-[9px] font-bold tracking-wider">{fileKind(document.original_filename)}</span>
        </div>
        <div className="min-w-0 flex-1">
          <button
            type="button"
            onClick={() => onView(document)}
            title={document.original_filename}
            className="block w-full truncate text-left font-medium hover:text-brand-mint"
          >
            {document.original_filename}
          </button>
          <p className="mt-0.5 text-xs text-ink-muted">
            {formatBytes(document.file_size_bytes)}
            {document.page_count !== null && ` · ${document.page_count} ${document.page_count === 1 ? 'page' : 'pages'}`}
          </p>
        </div>
        <DropdownMenu
          label={`Actions for ${document.original_filename}`}
          trigger={<MoreVertical className="h-[18px] w-[18px]" aria-hidden="true" />}
          items={[
            { label: 'View details', icon: <Eye className="h-4 w-4" aria-hidden="true" />, onSelect: () => onView(document) },
            { label: 'Delete', icon: <Trash2 className="h-4 w-4" aria-hidden="true" />, onSelect: () => onDelete(document), danger: true },
          ]}
        />
      </div>
      <div className="flex items-center justify-between gap-2 border-t border-line pt-3">
        <StatusBadge status={document.status} />
        <span className="text-xs text-ink-muted">Uploaded {formatDate(document.created_at)}</span>
      </div>
    </article>
  );
}

export function DocumentCardSkeleton() {
  return (
    <div className="surface space-y-4 p-5" aria-hidden="true">
      <div className="flex gap-3.5">
        <div className="h-11 w-11 animate-pulse rounded-xl bg-elevated" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-3/4 animate-pulse rounded bg-elevated" />
          <div className="h-3 w-1/3 animate-pulse rounded bg-elevated" />
        </div>
      </div>
      <div className="h-6 w-24 animate-pulse rounded-full bg-elevated" />
    </div>
  );
}
