import { useCallback, useRef, useState, type DragEvent } from 'react';
import { CheckCircle2, FileText, Loader2, UploadCloud, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { config } from '@/lib/config';
import { toApiError } from '@/lib/errors';
import { cn, formatBytes, uid } from '@/lib/utils';
import { documentsApi } from './api';
import { useInvalidateDocuments } from './hooks';
import { ACCEPT_ATTRIBUTE, validateFile } from './validation';

interface QueueItem {
  id: string;
  name: string;
  size: number;
  state: 'uploading' | 'done' | 'error';
  progress?: number;
  error?: string;
}

export function UploadZone({ compact = false }: { compact?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const busyRef = useRef(false);
  const dragDepth = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const invalidate = useInvalidateDocuments();

  const patch = useCallback((id: string, changes: Partial<QueueItem>) => {
    setQueue((items) => items.map((item) => (item.id === id ? { ...item, ...changes } : item)));
  }, []);

  const handleFiles = useCallback(
    async (fileList: FileList | File[]) => {
      if (busyRef.current) return; // prevents duplicate submissions while an upload batch is running
      const files = Array.from(fileList);
      if (files.length === 0) return;

      busyRef.current = true;
      setBusy(true);
      const items: QueueItem[] = files.map((file) => ({ id: uid(), name: file.name, size: file.size, state: 'uploading' }));
      setQueue((existing) => [...items, ...existing.filter((e) => e.state === 'uploading')]);

      for (const [index, file] of files.entries()) {
        const item = items[index];
        if (!item) continue;
        const problem = validateFile(file, config.maxUploadMb);
        if (problem) {
          patch(item.id, { state: 'error', error: problem });
          continue;
        }
        try {
          const created = await documentsApi.upload(file, (progress) => patch(item.id, { progress }));
          patch(item.id, { state: 'done', progress: 100 });
          toast.success(`${created.original_filename} uploaded`, { description: `Status reported by the server: ${created.status}.` });
          void invalidate();
          window.setTimeout(() => setQueue((q) => q.filter((entry) => entry.id !== item.id)), 4000);
        } catch (error) {
          const message = toApiError(error).message;
          patch(item.id, { state: 'error', error: message });
          toast.error(`Could not upload ${file.name}`, { description: message });
        }
      }

      busyRef.current = false;
      setBusy(false);
    },
    [invalidate, patch],
  );

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    void handleFiles(event.dataTransfer.files);
  };

  return (
    <div>
      <div
        role="group"
        aria-label="Upload documents"
        onDragEnter={(e) => {
          e.preventDefault();
          dragDepth.current += 1;
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => {
          dragDepth.current = Math.max(0, dragDepth.current - 1);
          if (dragDepth.current === 0) setDragging(false);
        }}
        onDrop={onDrop}
        className={cn(
          'relative overflow-hidden rounded-2xl border-2 border-dashed text-center transition-colors duration-200',
          compact ? 'px-6 py-7' : 'px-6 py-12 sm:py-14',
          dragging ? 'border-brand-mint bg-brand-deep/40' : 'border-brand/40 bg-card hover:border-brand/70',
        )}
      >
        <div className="ambient pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="relative flex flex-col items-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-brand/30 bg-brand-deep/50 text-brand-mint shadow-glow">
            <UploadCloud className="h-7 w-7" aria-hidden="true" />
          </div>
          <p className="text-lg font-semibold">{dragging ? 'Drop to upload' : 'Drag and drop your documents here'}</p>
          <p className="mt-1 text-sm text-ink-soft">PDF, DOCX or TXT, up to {config.maxUploadMb} MB each</p>
          <Button variant="primary" className="mt-5" loading={busy} onClick={() => inputRef.current?.click()}>
            {busy ? 'Uploading' : 'Browse files'}
          </Button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPT_ATTRIBUTE}
            className="sr-only"
            tabIndex={-1}
            aria-label="Choose files to upload"
            onChange={(event) => {
              if (event.target.files) void handleFiles(event.target.files);
              event.target.value = '';
            }}
          />
        </div>
      </div>

      {queue.length > 0 && (
        <ul className="mt-3 space-y-2" aria-live="polite" aria-label="Upload progress">
          {queue.map((item) => (
            <li key={item.id} className="flex items-center gap-3 rounded-xl border border-line bg-card px-4 py-3">
              <FileText className="h-5 w-5 shrink-0 text-ink-muted" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{item.name}</p>
                {item.state === 'uploading' && (
                  <div className="mt-1.5 flex items-center gap-3">
                    <div
                      role="progressbar"
                      aria-label={`Uploading ${item.name}`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={item.progress}
                      className="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated"
                    >
                      <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${item.progress ?? 0}%` }} />
                    </div>
                    <span className="w-24 text-right text-xs text-ink-muted">
                      {item.progress === 100 ? 'Finishing' : `${item.progress ?? 0}% of ${formatBytes(item.size)}`}
                    </span>
                  </div>
                )}
                {item.state === 'error' && <p className="mt-0.5 text-xs text-danger">{item.error}</p>}
                {item.state === 'done' && <p className="mt-0.5 text-xs text-brand-mint">Uploaded</p>}
              </div>
              {item.state === 'uploading' && <Loader2 className="h-4 w-4 animate-spin text-brand" aria-hidden="true" />}
              {item.state === 'done' && <CheckCircle2 className="h-4 w-4 text-brand-mint" aria-hidden="true" />}
              {item.state === 'error' && (
                <button
                  type="button"
                  aria-label={`Dismiss error for ${item.name}`}
                  onClick={() => setQueue((q) => q.filter((entry) => entry.id !== item.id))}
                  className="text-danger hover:opacity-80"
                >
                  <XCircle className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
