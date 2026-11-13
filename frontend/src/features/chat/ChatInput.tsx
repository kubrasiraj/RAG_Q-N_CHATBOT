import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { ArrowUp, Square } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { MAX_QUESTION_LENGTH, MIN_QUESTION_LENGTH } from './types';

interface ChatInputProps {
  onSubmit: (question: string) => void;
  onCancel: () => void;
  pending: boolean;
  topK: number;
  onTopKChange: (value: number) => void;
  /** Lets the page insert an example question. Changing `seed.nonce` applies it. */
  seed?: { text: string; nonce: number };
}

export function ChatInput({ onSubmit, onCancel, pending, topK, onTopKChange, seed }: ChatInputProps) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);
  const trimmed = value.trim();
  const canSend = !pending && trimmed.length >= MIN_QUESTION_LENGTH && trimmed.length <= MAX_QUESTION_LENGTH;

  const [appliedNonce, setAppliedNonce] = useState<number | undefined>(undefined);
  if (seed && seed.nonce !== appliedNonce) {
    setAppliedNonce(seed.nonce);
    setValue(seed.text);
  }

  useEffect(() => {
    if (seed) ref.current?.focus();
  }, [seed]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const submit = () => {
    if (!canSend) return;
    onSubmit(trimmed);
    setValue('');
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-line bg-workspace/90 px-3 pb-3 pt-3 sm:px-6 sm:pb-5">
      <div className="mx-auto max-w-3xl">
        <div
          className={cn(
            'rounded-2xl border border-line bg-card p-2 shadow-card transition-colors',
            'focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/25',
          )}
        >
          <label htmlFor="chat-question" className="sr-only">
            Ask a question about your documents
          </label>
          <textarea
            id="chat-question"
            ref={ref}
            rows={1}
            value={value}
            maxLength={MAX_QUESTION_LENGTH}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask anything about your documents"
            className="block max-h-[200px] w-full resize-none bg-transparent px-3 py-2.5 text-[15px] leading-6 text-ink placeholder:text-ink-muted focus:outline-none"
          />
          <div className="flex items-center justify-between gap-3 px-1 pt-1">
            <div className="flex items-center gap-2 text-xs text-ink-muted">
              <label htmlFor="chat-top-k">Sources</label>
              <select
                id="chat-top-k"
                value={topK}
                onChange={(e) => onTopKChange(Number(e.target.value))}
                className="h-8 rounded-lg border border-line bg-elevated px-2 text-xs text-ink focus:border-brand focus:outline-none"
              >
                {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
              {value.length > MAX_QUESTION_LENGTH - 200 && (
                <span className="tabular-nums">
                  {value.length}/{MAX_QUESTION_LENGTH}
                </span>
              )}
            </div>
            {pending ? (
              <Button size="icon" onClick={onCancel} aria-label="Stop and cancel the request">
                <Square className="h-4 w-4" aria-hidden="true" />
              </Button>
            ) : (
              <Button variant="primary" size="icon" onClick={submit} disabled={!canSend} aria-label="Send question">
                <ArrowUp className="h-5 w-5" aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>
        <p className="mt-2 hidden text-center text-xs text-ink-muted sm:block">
          Press Enter to send, Shift + Enter for a new line. Answers are based only on your processed documents.
        </p>
      </div>
    </div>
  );
}
