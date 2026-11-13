import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { renderWithProviders, sampleDocument } from '@/test/render';
import { documentsApi } from './api';
import { UploadZone } from './UploadZone';

vi.mock('./api', () => ({ documentsApi: { list: vi.fn(), get: vi.fn(), upload: vi.fn(), remove: vi.fn() } }));

describe('UploadZone', () => {
  beforeEach(() => vi.clearAllMocks());

  it('rejects unsupported files client-side without calling the API', async () => {
    renderWithProviders(<UploadZone />);
    const input = screen.getByLabelText('Choose files to upload');
    // applyAccept is disabled so the file reaches our own validation, as with drag-and-drop.
    await userEvent.setup({ applyAccept: false }).upload(input, new File(['x'], 'virus.exe'));
    expect(await screen.findByText(/Unsupported file type/)).toBeInTheDocument();
    expect(documentsApi.upload).not.toHaveBeenCalled();
  });

  it('uploads a valid file and reports the status returned by the server', async () => {
    vi.mocked(documentsApi.upload).mockResolvedValue({ ...sampleDocument, status: 'pending' });
    renderWithProviders(<UploadZone />);
    const file = new File(['hello'], 'hello.txt', { type: 'text/plain' });
    await userEvent.upload(screen.getByLabelText('Choose files to upload'), file);
    await waitFor(() => expect(documentsApi.upload).toHaveBeenCalledTimes(1));
    expect(vi.mocked(documentsApi.upload).mock.calls[0]?.[0]).toBe(file);
    expect(await screen.findByText('Uploaded')).toBeInTheDocument();
  });

  it('shows the backend error when an upload fails', async () => {
    const { ApiError } = await import('@/lib/errors');
    vi.mocked(documentsApi.upload).mockRejectedValue(new ApiError('Invalid or corrupted PDF file.', { status: 400 }));
    renderWithProviders(<UploadZone />);
    await userEvent.upload(screen.getByLabelText('Choose files to upload'), new File(['%PDF'], 'bad.pdf'));
    expect(await screen.findByText('Invalid or corrupted PDF file.')).toBeInTheDocument();
  });
});
