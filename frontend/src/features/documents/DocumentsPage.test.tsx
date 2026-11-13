import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { ApiError } from '@/lib/errors';
import { renderWithProviders, sampleDocument } from '@/test/render';
import { documentsApi } from './api';
import { DocumentsPage } from './DocumentsPage';
import { documentPollInterval } from './hooks';

vi.mock('./api', () => ({ documentsApi: { list: vi.fn(), get: vi.fn(), upload: vi.fn(), remove: vi.fn() } }));

const pendingDoc = { ...sampleDocument, id: '22222222-2222-4222-8222-222222222222', original_filename: 'notes.txt', status: 'pending' as const, page_count: null, processed_at: null };

describe('DocumentsPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('lists documents with the real status returned by the API', async () => {
    vi.mocked(documentsApi.list).mockResolvedValue({ items: [sampleDocument, pendingDoc], total: 2 });
    renderWithProviders(<DocumentsPage />);
    expect(await screen.findByText('handbook.pdf')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/processed in the background/i);
    expect(documentsApi.list).toHaveBeenCalledWith({ skip: 0, limit: 12 }, expect.anything());
  });

  it('shows an empty state and an error state with retry', async () => {
    vi.mocked(documentsApi.list).mockResolvedValueOnce({ items: [], total: 0 });
    const { unmount } = renderWithProviders(<DocumentsPage />);
    expect(await screen.findByText('No documents yet')).toBeInTheDocument();
    unmount();

    vi.mocked(documentsApi.list).mockRejectedValueOnce(new ApiError('Cannot reach the server.')).mockResolvedValueOnce({ items: [sampleDocument], total: 1 });
    renderWithProviders(<DocumentsPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server.');
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('handbook.pdf')).toBeInTheDocument();
  });

  it('deletes only after confirmation', async () => {
    vi.mocked(documentsApi.list).mockResolvedValue({ items: [sampleDocument], total: 1 });
    vi.mocked(documentsApi.remove).mockResolvedValue();
    renderWithProviders(<DocumentsPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Actions for handbook.pdf' }));
    await userEvent.click(screen.getByRole('menuitem', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    expect(documentsApi.remove).not.toHaveBeenCalled();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete document' }));
    await waitFor(() => expect(documentsApi.remove).toHaveBeenCalledWith(sampleDocument.id));
  });

  it('loads details from the detail endpoint and explains failed documents honestly', async () => {
    const failed = { ...sampleDocument, status: 'failed' as const, page_count: null, processed_at: null };
    vi.mocked(documentsApi.list).mockResolvedValue({ items: [failed], total: 1 });
    vi.mocked(documentsApi.get).mockResolvedValue(failed);
    renderWithProviders(<DocumentsPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Actions for handbook.pdf' }));
    await userEvent.click(screen.getByRole('menuitem', { name: 'View details' }));
    expect(await screen.findByText(/does not provide a reason/i)).toBeInTheDocument();
    expect(documentsApi.get).toHaveBeenCalledWith(failed.id, expect.anything());
    expect(screen.getByText('Not processed')).toBeInTheDocument();
  });
});

describe('status polling', () => {
  const doc = (status: 'pending' | 'processing' | 'completed' | 'failed') => ({ ...sampleDocument, status });

  it('polls while documents are in progress and stops when all are completed or failed', () => {
    expect(documentPollInterval(undefined)).toBe(false);
    expect(documentPollInterval([])).toBe(false);
    expect(documentPollInterval([doc('pending')])).toBe(5000);
    expect(documentPollInterval([doc('pending'), doc('processing')])).toBe(3000);
    expect(documentPollInterval([doc('completed'), doc('failed')])).toBe(false);
  });

  it('shows each real status, including processing and failed, and no fake progress', async () => {
    vi.mocked(documentsApi.list).mockResolvedValue({
      items: [doc('pending'), { ...doc('processing'), id: 'p2', original_filename: 'b.pdf' }, { ...doc('failed'), id: 'p3', original_filename: 'c.pdf' }],
      total: 3,
    });
    renderWithProviders(<DocumentsPage />);
    expect(await screen.findByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Processing')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });
});
