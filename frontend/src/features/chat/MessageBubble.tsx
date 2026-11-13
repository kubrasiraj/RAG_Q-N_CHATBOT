import { useState } from 'react';
import { AlertTriangle, Check, Copy, FileSearch, RotateCcw, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { LogoMark } from '@/components/ui/Logo';
import { formatTime } from '@/lib/utils';
import { MarkdownAnswer } from './MarkdownAnswer';
import { SourceCard } from './SourceCard';
import type { ChatMessage } from './types';

interface MessageBubbleProps {
  message: ChatMessage;
  canRetry: boolean;
  onRetry: () => void;
}

export function UserBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end animate-fade-up">
      <div className="max-w-[85%] sm:max-w-[75%]">
        <div className="whitespace-pre-wrap break-words rounded-2xl rounded-br-md border border-brand/30 bg-brand-deep/60 px-4 py-3 text-[15px] leading-7">
          {message.content}
        </div>
        <p className="mt-1 pr-1 text-right text-[11px] text-ink-muted">{formatTime(message.createdAt)}</p>
      </div>
    </div>
  );
}

export function AssistantBubble({ message, canRetry, onRetry }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [openSources, setOpenSources] = useState<Record<string, boolean>>({});
  const sources = message.sources ?? [];
  const sourceIds = new Set(sources.map((s) => s.source_id));

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error('Could not copy to the clipboard.');
    }
  };

  const showSource = (sourceId: string) => {
    setOpenSources((prev) => ({ ...prev, [sourceId]: true }));
    window.setTimeout(() => document.getElementById(`src-${message.id}-${sourceId}`)?.scrollIntoView({ block: 'nearest' }), 0);
  };

  return (
    <div className="flex gap-3 animate-fade-up">
      <LogoMark className="mt-1 h-8 w-8 shrink-0" />
      <div className="min-w-0 flex-1 space-y-3">
        {message.error ? (
          <div role="alert" className="rounded-2xl rounded-tl-md border border-danger/40 bg-danger/5 p-4">
            <p className="flex items-center gap-2 text-sm font-medium text-danger">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" /> The question could not be answered
            </p>
            <p className="mt-1 text-sm text-ink-soft">{message.error}</p>
            {canRetry && (
              <Button size="sm" className="mt-3" onClick={onRetry}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" /> Try again
              </Button>
            )}
          </div>
        ) : message.insufficientContext ? (
          <div className="rounded-2xl rounded-tl-md border border-warn/35 bg-warn/5 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-warn">
              <FileSearch className="h-4 w-4" aria-hidden="true" /> Not enough evidence in your documents
            </p>
            <p className="mt-1.5 text-sm text-ink-soft">
              The documents available to the assistant do not contain enough information to answer this reliably, so no sources are shown.
            </p>
            <p className="mt-3 whitespace-pre-wrap border-t border-warn/20 pt-3 text-sm text-ink-soft">{message.content}</p>
          </div>
        ) : (
          <div className="rounded-2xl rounded-tl-md border border-line bg-card p-4 shadow-card sm:p-5">
            <p className="eyebrow mb-3 flex items-center gap-1.5 text-brand-mint">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" /> Generated answer
            </p>
            <MarkdownAnswer content={message.content} sourceIds={sourceIds} onCite={showSource} />
          </div>
        )}

        {sources.length > 0 && !message.insufficientContext && !message.error && (
          <section aria-label="Retrieved sources" className="rounded-2xl border border-line/70 bg-workspace p-3 sm:p-4">
            <p className="eyebrow mb-3 flex items-center gap-1.5">
              <FileSearch className="h-3.5 w-3.5" aria-hidden="true" /> Retrieved evidence · {sources.length} {sources.length === 1 ? 'source' : 'sources'}
            </p>
            <div className="space-y-2">
              {sources.map((source) => (
                <SourceCard
                  key={source.source_id}
                  source={source}
                  domId={`src-${message.id}-${source.source_id}`}
                  expanded={openSources[source.source_id] ?? false}
                  onToggle={(open) => setOpenSources((prev) => ({ ...prev, [source.source_id]: open }))}
                />
              ))}
            </div>
          </section>
        )}

        <div className="flex items-center gap-1 text-ink-muted">
          <span className="mr-2 text-[11px]">{formatTime(message.createdAt)}</span>
          {!message.error && (
            <Button variant="ghost" size="sm" onClick={() => void copy()} aria-label="Copy answer">
              {copied ? <Check className="h-4 w-4 text-brand-mint" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
              {copied ? 'Copied' : 'Copy'}
            </Button>
          )}
          {!message.error && canRetry && (
            <Button variant="ghost" size="sm" onClick={onRetry} aria-label="Ask again">
              <RotateCcw className="h-4 w-4" aria-hidden="true" /> Ask again
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export function TypingIndicator({ onCancel }: { onCancel: () => void }) {
  return (
    <div className="flex gap-3" role="status" aria-label="The assistant is searching your documents">
      <LogoMark className="mt-1 h-8 w-8 shrink-0" />
      <div className="flex items-center gap-4 rounded-2xl rounded-tl-md border border-line bg-card px-4 py-3.5">
        <span className="flex gap-1.5" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span key={i} className="h-2 w-2 animate-dot-pulse rounded-full bg-brand-mint" style={{ animationDelay: `${i * 0.18}s` }} />
          ))}
        </span>
        <span className="text-sm text-ink-soft">Searching your documents</span>
        <button type="button" onClick={onCancel} className="text-sm text-ink-muted underline-offset-4 hover:text-ink hover:underline">
          Cancel
        </button>
      </div>
    </div>
  );
}
