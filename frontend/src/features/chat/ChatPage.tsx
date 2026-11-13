import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { HardDrive, Info, Sparkles, Trash2, Upload } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useDocuments } from '@/features/documents/hooks';
import { AssistantBubble, TypingIndicator, UserBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { useChatSessions } from './sessions-context';
import { DEFAULT_TOP_K } from './types';

const SUGGESTIONS = [
  'Summarize the key points of my documents.',
  'What dates, deadlines or numbers are mentioned?',
  'List the main requirements or conditions described.',
  'What does the document say about pricing or costs?',
];

function ReadinessNotice() {
  const { data } = useDocuments(0, 100);
  if (!data || data.items.length !== data.total) return null;
  if (data.items.some((d) => d.status === 'completed')) return null;
  const message =
    data.total === 0
      ? 'You have not uploaded any documents yet. Questions can only be answered from documents.'
      : 'None of your documents have finished processing, so there is nothing to search yet. Check their status on the Documents page.';
  return (
    <div role="note" className="mx-auto mb-4 flex max-w-3xl gap-3 rounded-xl border border-warn/30 bg-warn/5 px-4 py-3 text-sm text-ink-soft">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-warn" aria-hidden="true" />
      <p>
        {message}{' '}
        <Link to="/documents" className="font-medium text-brand-mint underline-offset-4 hover:underline">
          Go to Documents
        </Link>
      </p>
    </div>
  );
}

function EmptyChat({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="relative flex h-full flex-col items-center justify-center px-5 py-10 text-center">
      <div className="ambient pointer-events-none absolute inset-0" aria-hidden="true" />
      <div className="relative mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-brand/30 bg-brand-deep/50 text-brand-mint shadow-glow">
        <Sparkles className="h-8 w-8" aria-hidden="true" />
      </div>
      <h2 className="relative text-2xl font-semibold tracking-tight sm:text-3xl">Ask anything about your documents.</h2>
      <p className="relative mt-2 max-w-md text-ink-soft">Get clear, evidence-backed answers from your uploaded files.</p>
      <div className="relative mt-8 grid w-full max-w-2xl gap-2.5 sm:grid-cols-2">
        {SUGGESTIONS.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => onPick(text)}
            className="rounded-xl border border-line bg-card px-4 py-3.5 text-left text-sm text-ink-soft transition-colors hover:border-brand/60 hover:text-ink"
          >
            {text}
          </button>
        ))}
      </div>
      <Link
        to="/documents"
        className="relative mt-6 inline-flex items-center gap-2 text-sm font-medium text-brand-mint underline-offset-4 hover:underline"
      >
        <Upload className="h-4 w-4" aria-hidden="true" /> Upload more documents
      </Link>
    </div>
  );
}

export function ChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { getSession, isPending, createSession, ask, retry, cancel, clearSession } = useChatSessions();
  const session = sessionId ? getSession(sessionId) : undefined;
  const [topK, setTopK] = useState(DEFAULT_TOP_K);
  const [seed, setSeed] = useState<{ text: string; nonce: number }>();
  const [confirmClear, setConfirmClear] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const messages = session?.messages ?? [];
  const pending = session ? isPending(session.id) : false;
  const lastAssistantId = [...messages].reverse().find((m) => m.role === 'assistant')?.id;

  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    bottomRef.current?.scrollIntoView?.({ behavior: reduce ? 'auto' : 'smooth', block: 'end' });
  }, [messages.length, pending]);

  if (sessionId && !session) return <Navigate to="/chat" replace />;

  const submit = (question: string) => {
    if (session) {
      void ask(session.id, question, { topK });
      return;
    }
    const id = createSession();
    navigate(`/chat/${id}`, { replace: true });
    void ask(id, question, { topK });
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <h1 className="truncate text-[15px] font-semibold">{session && messages.length > 0 ? session.title : 'New conversation'}</h1>
          <p className="flex items-center gap-1.5 text-xs text-ink-muted" title="Chat history is not stored on the server">
            <HardDrive className="h-3 w-3" aria-hidden="true" /> Local session, saved in this browser only
          </p>
        </div>
        {session && messages.length > 0 && (
          <Button size="sm" onClick={() => setConfirmClear(true)}>
            <Trash2 className="h-4 w-4" aria-hidden="true" /> <span className="hidden sm:inline">Clear conversation</span>
            <span className="sm:hidden">Clear</span>
          </Button>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 && !pending ? (
          <EmptyChat onPick={(text) => setSeed({ text, nonce: Date.now() })} />
        ) : (
          <div className="mx-auto max-w-3xl space-y-6 px-4 py-6 sm:px-6">
            {messages.map((message) =>
              message.role === 'user' ? (
                <UserBubble key={message.id} message={message} />
              ) : (
                <AssistantBubble
                  key={message.id}
                  message={message}
                  canRetry={!pending && message.id === lastAssistantId}
                  onRetry={() => session && void retry(session.id, message.id, topK)}
                />
              )
            )}
            {pending && session && <TypingIndicator onCancel={() => cancel(session.id)} />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div>
        {messages.length === 0 && <ReadinessNotice />}
        <ChatInput onSubmit={submit} onCancel={() => session && cancel(session.id)} pending={pending} topK={topK} onTopKChange={setTopK} seed={seed} />
      </div>

      <Dialog
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Clear this conversation?"
        description="All messages in this local session will be removed from this browser."
        footer={
          <>
            <Button onClick={() => setConfirmClear(false)}>Cancel</Button>
            <Button
              variant="danger"
              onClick={() => {
                if (session) clearSession(session.id);
                setConfirmClear(false);
              }}
            >
              Clear conversation
            </Button>
          </>
        }
      />
    </div>
  );
}
