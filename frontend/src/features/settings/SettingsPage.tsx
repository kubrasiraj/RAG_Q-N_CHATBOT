import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { LogOut, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { useAuth } from '@/features/auth/auth-context';
import { useChatSessions } from '@/features/chat/sessions-context';
import { config } from '@/lib/config';
import { formatDate } from '@/lib/utils';
import { healthApi } from './api';

function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section className="surface p-6">
      <h2 className="font-semibold">{title}</h2>
      {description && <p className="mt-1 text-sm text-ink-soft">{description}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Rows({ rows }: { rows: Array<[string, ReactNode]> }) {
  return (
    <dl className="divide-y divide-line text-sm">
      {rows.map(([term, value]) => (
        <div key={term} className="grid gap-1 py-3 sm:grid-cols-[11rem_1fr] sm:gap-3">
          <dt className="text-ink-muted">{term}</dt>
          <dd className="break-all text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ServiceStatus({ label, query }: { label: string; query: { isPending: boolean; isError: boolean; data?: { status: string } } }) {
  const text = query.isPending ? 'Checking' : query.isError ? 'Unreachable' : query.data?.status === 'ok' ? 'Connected' : (query.data?.status ?? 'Unknown');
  const good = !query.isPending && !query.isError && query.data?.status === 'ok';
  return (
    <span className="inline-flex items-center gap-2" aria-label={`${label}: ${text}`}>
      <span className={`h-2 w-2 rounded-full ${query.isPending ? 'animate-pulse bg-ink-muted' : good ? 'bg-brand' : 'bg-danger'}`} aria-hidden="true" />
      {text}
    </span>
  );
}

export function SettingsPage() {
  const { user, tokenExpiresAt, logout } = useAuth();
  const { sessions, clearAll } = useChatSessions();
  const [confirmClear, setConfirmClear] = useState(false);
  const health = useQuery({ queryKey: ['health', 'app'], queryFn: healthApi.app, retry: false });
  const db = useQuery({ queryKey: ['health', 'db'], queryFn: healthApi.database, retry: false });

  if (!user) return null;

  return (
    <PageContainer>
      <PageHeader title="Settings" description="Your account and application information." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Profile" description="Account details returned by the server.">
          <Rows
            rows={[
              ['Email', user.email],
              ['Role', user.role],
              ['Account status', user.is_active ? 'Active' : 'Inactive'],
              ['Member since', formatDate(user.created_at)],
              ['Session expires', tokenExpiresAt ? formatDate(new Date(tokenExpiresAt * 1000).toISOString(), true) : 'Unknown'],
            ]}
          />
          <Button variant="danger" className="mt-5" onClick={logout}>
            <LogOut className="h-4 w-4" aria-hidden="true" /> Sign out
          </Button>
        </Section>

        <Section title="Application" description="Live status of the connected backend.">
          <Rows
            rows={[
              ['API', <ServiceStatus key="api" label="API" query={health} />],
              ['Database', <ServiceStatus key="db" label="Database" query={db} />],
              ['Service', health.data?.service ?? 'Not available'],
              ['Environment', health.data?.environment ?? 'Not available'],
              ['API base URL', config.apiBaseUrl],
              ['Upload limit (UI)', `${config.maxUploadMb} MB`],
              ['Theme', 'Obsidian Emerald (dark)'],
            ]}
          />
        </Section>

        <Section
          title="Local chat sessions"
          description="Conversations are kept only in this browser. The backend does not store chat history."
        >
          <p className="text-sm text-ink-soft">
            {sessions.length} {sessions.length === 1 ? 'session' : 'sessions'} stored on this device.
          </p>
          <Button className="mt-4" disabled={sessions.length === 0} onClick={() => setConfirmClear(true)}>
            <Trash2 className="h-4 w-4" aria-hidden="true" /> Delete all local chats
          </Button>
        </Section>
      </div>

      <Dialog
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Delete all local chats?"
        description="This removes every conversation, including saved answers and source excerpts, from this browser."
        footer={
          <>
            <Button onClick={() => setConfirmClear(false)}>Cancel</Button>
            <Button
              variant="danger"
              onClick={() => {
                clearAll();
                setConfirmClear(false);
                toast.success('Local chats deleted.');
              }}
            >
              Delete all
            </Button>
          </>
        }
      />
    </PageContainer>
  );
}
