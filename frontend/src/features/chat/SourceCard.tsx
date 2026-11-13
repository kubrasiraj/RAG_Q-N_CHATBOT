import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { QASource } from './types';

interface SourceCardProps {
  source: QASource;
  domId: string;
  expanded?: boolean;
  onToggle?: (open: boolean) => void;
}

export function SourceCard({ source, domId, expanded, onToggle }: SourceCardProps) {
  const [localOpen, setLocalOpen] = useState(false);
  const open = expanded ?? localOpen;
  const panelId = `${domId}-panel`;
  const similarity = Number.isFinite(source.similarity) ? Math.max(0, Math.min(1, source.similarity)) : 0;

  const toggle = () => {
    setLocalOpen(!open);
    onToggle?.(!open);
  };

  return (
    <div id={domId} className="rounded-xl border border-line bg-sidebar/80 transition-colors hover:border-brand/40">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-start gap-3 rounded-xl p-3.5 text-left"
      >
        <span className="mt-0.5 flex h-6 min-w-[1.75rem] items-center justify-center rounded-md border border-brand/40 bg-brand-deep/50 px-1.5 text-[11px] font-bold text-brand-mint">
          {source.source_id}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium" title={source.filename}>
            {source.filename}
          </span>
          <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
            <span>{source.page_number !== null ? `Page ${source.page_number}` : 'Page not available'}</span>
            <span>Chunk {source.chunk_index}</span>
            <span className="flex items-center gap-1.5" title="Similarity score returned by the backend">
              Similarity {source.similarity.toFixed(2)}
              <span className="h-1 w-10 overflow-hidden rounded-full bg-elevated" aria-hidden="true">
                <span className="block h-full rounded-full bg-brand" style={{ width: `${similarity * 100}%` }} />
              </span>
            </span>
          </span>
          {!open && <span className="mt-2 line-clamp-2 block text-[13px] leading-5 text-ink-soft">{source.excerpt}</span>}
        </span>
        <ChevronDown className={cn('mt-1 h-4 w-4 shrink-0 text-ink-muted transition-transform', open && 'rotate-180')} aria-hidden="true" />
      </button>
      {open && (
        <div id={panelId} className="border-t border-line px-3.5 pb-3.5 pt-3">
          <p className="eyebrow mb-2">Retrieved passage</p>
          <blockquote className="whitespace-pre-wrap border-l-2 border-brand/60 pl-3.5 text-[13px] leading-6 text-ink-soft">{source.excerpt}</blockquote>
        </div>
      )}
    </div>
  );
}
