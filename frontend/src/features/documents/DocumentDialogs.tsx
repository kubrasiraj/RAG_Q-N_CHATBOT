import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ErrorState } from '@/components/common/ErrorState';
import { toApiError } from '@/lib/errors';
import { formatBytes, formatDate } from '@/lib/utils';
import { useDeleteDocument, useDocument } from './hooks';
import type { DocumentItem } from './types';

export function DocumentDetailsDialog({ documentId, onClose }: { documentId: string | null; onClose: () => void }) {
  const query = useDocument(documentId);
  const doc = query.data;

  const rows: Array<[string, string]> = doc
    ? [
        ['File name', doc.original_filename],
        ['Type', doc.mime_type],
        ['Size', formatBytes(doc.file_size_bytes)],
        ['Pages', doc.page_count !== null ? String(doc.page_count) : 'Not available'],
        ['Uploaded', formatDate(doc.created_at, true)],
        ['Last updated', formatDate(doc.updated_at, true)],
        ['Processed', doc.processed_at ? formatDate(doc.processed_at, true) : 'Not processed'],
        ['Document ID', doc.id],
      ]
    : [];

  return (
    <Dialog open={documentId !== null} onClose={onClose} title="Document details" footer={<Button onClick={onClose}>Close</Button>}>
      {query.isPending && (
        <div className="space-y-3">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="h-5 w-3/4" />
        </div>
      )}
      {query.isError && <ErrorState message={toApiError(query.error).message} onRetry={() => void query.refetch()} />}
      {doc && (
        <div className="space-y-4">
          <StatusBadge status={doc.status} />
          {doc.status === 'failed' && (
            <p className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-ink-soft">
              The backend marked this document as failed. The API does not provide a reason.
            </p>
          )}
          <dl className="divide-y divide-line text-sm">
            {rows.map(([term, value]) => (
              <div key={term} className="grid grid-cols-[7rem_1fr] gap-3 py-2.5">
                <dt className="text-ink-muted">{term}</dt>
                <dd className="break-all text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </Dialog>
  );
}

export function DeleteDocumentDialog({ document: doc, onClose }: { document: DocumentItem | null; onClose: () => void }) {
  const remove = useDeleteDocument();

  const confirm = () => {
    if (!doc || remove.isPending) return;
    remove.mutate(doc.id, {
      onSuccess: () => {
        toast.success(`${doc.original_filename} deleted`);
        onClose();
      },
      onError: (error) => toast.error('Could not delete the document', { description: toApiError(error).message }),
    });
  };

  return (
    <Dialog
      open={doc !== null}
      onClose={onClose}
      title="Delete this document?"
      description={doc ? `“${doc.original_filename}” will be permanently deleted. This cannot be undone.` : undefined}
      footer={
        <>
          <Button onClick={onClose} disabled={remove.isPending}>
            Cancel
          </Button>
          <Button variant="danger" loading={remove.isPending} onClick={confirm}>
            Delete document
          </Button>
        </>
      }
    />
  );
}
