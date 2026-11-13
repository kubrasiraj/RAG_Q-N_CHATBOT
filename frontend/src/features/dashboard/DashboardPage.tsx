import { ArrowRight, FileText, MessageSquarePlus } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { EmptyState } from '@/components/common/EmptyState';
import { PageContainer } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useAuth } from '@/features/auth/auth-context';
import { UploadZone } from '@/features/documents/UploadZone';
import { useDocuments } from '@/features/documents/hooks';
import { config } from '@/lib/config';
import { displayNameFromEmail, formatDate } from '@/lib/utils';

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="surface px-5 py-4">
      <p className="eyebrow">{label}</p>
      <p className="mt-1.5 text-3xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const query = useDocuments(0, 100);
  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const exact = query.data !== undefined && items.length === total; // status counts are only exact when everything was loaded

  return (
    <PageContainer>
      <section className="ambient relative mb-8 overflow-hidden rounded-3xl border border-line bg-sidebar px-6 py-10 sm:px-10 sm:py-14">
        <p className="eyebrow text-brand-mint">Welcome back{user ? `, ${displayNameFromEmail(user.email)}` : ''}</p>
        <h1 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight tracking-tight sm:text-5xl">Your documents. Your knowledge. One AI workspace.</h1>
        <p className="mt-4 max-w-xl text-ink-soft sm:text-lg">Upload your documents and turn information into answers with AI.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button variant="primary" size="lg" onClick={() => navigate('/chat')}>
            <MessageSquarePlus className="h-5 w-5" aria-hidden="true" /> Ask a question
          </Button>
          <Button size="lg" onClick={() => navigate('/documents')}>
            <FileText className="h-5 w-5" aria-hidden="true" /> Manage documents
          </Button>
        </div>
      </section>

      <UploadZone />
      <p className="mt-3 text-center text-xs text-ink-muted">Supported formats: PDF, DOCX, TXT. Maximum {config.maxUploadMb} MB per file.</p>

      <section className="mt-10" aria-label="Document overview">
        {query.isPending ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : query.isError ? null : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat label="Documents" value={total} />
              {exact && <Stat label="Completed" value={items.filter((d) => d.status === 'completed').length} />}
              {exact && <Stat label="Pending or processing" value={items.filter((d) => d.status === 'pending' || d.status === 'processing').length} />}
            </div>

            <div className="mb-4 mt-10 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Recent documents</h2>
              {total > 0 && (
                <Link to="/documents" className="inline-flex items-center gap-1 text-sm text-brand-mint hover:underline">
                  View all <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              )}
            </div>
            {items.length === 0 ? (
              <EmptyState
                icon={<FileText className="h-7 w-7" aria-hidden="true" />}
                title="Your library is empty"
                description="Drop a PDF, DOCX or TXT file into the upload area above to get started."
              />
            ) : (
              <ul className="surface divide-y divide-line">
                {items.slice(0, 4).map((doc) => (
                  <li key={doc.id} className="flex items-center gap-4 px-5 py-4">
                    <FileText className="h-5 w-5 shrink-0 text-brand-mint" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{doc.original_filename}</p>
                      <p className="text-xs text-ink-muted">Uploaded {formatDate(doc.created_at)}</p>
                    </div>
                    <StatusBadge status={doc.status} />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>
    </PageContainer>
  );
}
