import { useState } from 'react';
import { ChevronLeft, ChevronRight, FolderOpen, Info, RefreshCw } from 'lucide-react';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { toApiError } from '@/lib/errors';
import { DocumentCard, DocumentCardSkeleton } from './DocumentCard';
import { DeleteDocumentDialog, DocumentDetailsDialog } from './DocumentDialogs';
import { UploadZone } from './UploadZone';
import { useDocuments } from './hooks';
import type { DocumentItem } from './types';

const PAGE_SIZE = 12;

export function DocumentsPage() {
  const [skip, setSkip] = useState(0);
  const [viewId, setViewId] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<DocumentItem | null>(null);
  const query = useDocuments(skip, PAGE_SIZE);
  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const inProgress = items.some((d) => d.status === 'pending' || d.status === 'processing');

  // After deleting the last item of a page, step back to the previous page.
  if (query.data && query.data.items.length === 0 && skip > 0) setSkip(Math.max(0, skip - PAGE_SIZE));

  return (
    <PageContainer>
      <PageHeader
        title="Documents"
        description="Upload files and track their processing status."
        actions={
          <Button onClick={() => void query.refetch()} disabled={query.isFetching} aria-label="Refresh documents">
            <RefreshCw className={`h-4 w-4 ${query.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <UploadZone compact />

      {inProgress && (
        <div role="status" className="mt-6 flex gap-3 rounded-xl border border-brand/30 bg-brand-deep/20 px-4 py-3 text-sm text-ink-soft">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand-mint" aria-hidden="true" />
          <p>
            Documents are processed in the background after upload. This can take a minute or more, especially the first time. Their status updates here automatically,
            and a document can be used for answers once it shows Completed.
          </p>
        </div>
      )}

      <section className="mt-8" aria-label="Your documents">
        {query.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <DocumentCardSkeleton key={i} />
            ))}
          </div>
        ) : query.isError ? (
          <ErrorState message={toApiError(query.error).message} onRetry={() => void query.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<FolderOpen className="h-7 w-7" aria-hidden="true" />}
            title="No documents yet"
            description="Upload a PDF, DOCX or TXT file above. Once it is processed you can ask questions about it."
          />
        ) : (
          <>
            <p className="mb-4 text-sm text-ink-muted">
              {total} {total === 1 ? 'document' : 'documents'}
            </p>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {items.map((doc) => (
                <DocumentCard key={doc.id} document={doc} onView={(d) => setViewId(d.id)} onDelete={setToDelete} />
              ))}
            </div>
            {total > PAGE_SIZE && (
              <nav aria-label="Pagination" className="mt-6 flex items-center justify-between">
                <p className="text-sm text-ink-muted">
                  Showing {skip + 1} to {Math.min(skip + PAGE_SIZE, total)} of {total}
                </p>
                <div className="flex gap-2">
                  <Button size="sm" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}>
                    <ChevronLeft className="h-4 w-4" aria-hidden="true" /> Previous
                  </Button>
                  <Button size="sm" disabled={skip + PAGE_SIZE >= total} onClick={() => setSkip(skip + PAGE_SIZE)}>
                    Next <ChevronRight className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </nav>
            )}
          </>
        )}
      </section>

      <DocumentDetailsDialog documentId={viewId} onClose={() => setViewId(null)} />
      <DeleteDocumentDialog document={toDelete} onClose={() => setToDelete(null)} />
    </PageContainer>
  );
}
