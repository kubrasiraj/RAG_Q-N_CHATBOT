import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { ApiError } from '@/lib/errors';
import { renderWithProviders, sampleDocument } from '@/test/render';
import { documentsApi } from '@/features/documents/api';
import { chatApi } from './api';
import { ChatPage } from './ChatPage';
import { ChatSessionsProvider } from './ChatSessionsProvider';

vi.mock('./api', () => ({ chatApi: { askQuestion: vi.fn() } }));
vi.mock('@/features/documents/api', () => ({ documentsApi: { list: vi.fn(), get: vi.fn(), upload: vi.fn(), remove: vi.fn() } }));

const source = {
  source_id: 'S1',
  document_id: sampleDocument.id,
  filename: 'handbook.pdf',
  page_number: 4,
  chunk_index: 2,
  similarity: 0.91,
  excerpt: 'Vacation accrues monthly.',
};

function setup() {
  return renderWithProviders(
    <ChatSessionsProvider userId="user-1">
      <Routes>
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:sessionId" element={<ChatPage />} />
      </Routes>
    </ChatSessionsProvider>,
    '/chat',
  );
}

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(documentsApi.list).mockResolvedValue({ items: [sampleDocument], total: 1 });
  });

  it('shows the empty state with example questions', () => {
    setup();
    expect(screen.getByText('Ask anything about your documents.')).toBeInTheDocument();
    expect(screen.getByText('Get clear, evidence-backed answers from your uploaded files.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Upload more documents/ })).toBeInTheDocument();
  });

  it('sends the question to /qa/ask, shows the real answer and sources, and keeps a local session', async () => {
    vi.mocked(chatApi.askQuestion).mockResolvedValue({ answer: 'Vacation accrues monthly [S1].', sources: [source], insufficient_context: false });
    setup();
    await userEvent.type(screen.getByLabelText('Ask a question about your documents'), 'How does vacation work?{Enter}');
    expect(await screen.findByText('Generated answer')).toBeInTheDocument();
    expect(chatApi.askQuestion).toHaveBeenCalledWith({ question: 'How does vacation work?', top_k: 5 }, expect.any(AbortSignal));
    expect(screen.getByText('handbook.pdf')).toBeInTheDocument();
    expect(screen.getByText('Page 4')).toBeInTheDocument();
    expect(screen.getByText('How does vacation work?', { selector: 'div' })).toBeInTheDocument();
    const stored = JSON.parse(localStorage.getItem('novadocs.chats.v1.user-1') ?? '[]') as Array<{ messages: unknown[] }>;
    expect(stored).toHaveLength(1);
    expect(stored[0]?.messages).toHaveLength(2);
  });

  it('Shift+Enter adds a new line instead of sending', async () => {
    setup();
    const input = screen.getByLabelText('Ask a question about your documents');
    await userEvent.type(input, 'first line{Shift>}{Enter}{/Shift}second line');
    expect(chatApi.askQuestion).not.toHaveBeenCalled();
    expect(input).toHaveValue('first line\nsecond line');
  });

  it('will not submit questions shorter than the backend minimum', async () => {
    setup();
    await userEvent.type(screen.getByLabelText('Ask a question about your documents'), 'hi{Enter}');
    expect(chatApi.askQuestion).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Send question' })).toBeDisabled();
  });

  it('displays insufficient-context responses without sources', async () => {
    vi.mocked(chatApi.askQuestion).mockResolvedValue({ answer: 'Nothing about that was found.', sources: [], insufficient_context: true });
    setup();
    await userEvent.type(screen.getByLabelText('Ask a question about your documents'), 'What is the moon made of?{Enter}');
    expect(await screen.findByText('Not enough evidence in your documents')).toBeInTheDocument();
    expect(screen.queryByLabelText('Retrieved sources')).not.toBeInTheDocument();
  });

  it('surfaces API errors and retries the same question', async () => {
    vi.mocked(chatApi.askQuestion)
      .mockRejectedValueOnce(new ApiError('The AI service is temporarily unavailable.', { status: 503 }))
      .mockResolvedValueOnce({ answer: 'Recovered answer.', sources: [source], insufficient_context: false });
    setup();
    await userEvent.type(screen.getByLabelText('Ask a question about your documents'), 'Will this work?{Enter}');
    expect(await screen.findByRole('alert')).toHaveTextContent('The AI service is temporarily unavailable.');
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Recovered answer.')).toBeInTheDocument();
    expect(chatApi.askQuestion).toHaveBeenCalledTimes(2);
    expect(vi.mocked(chatApi.askQuestion).mock.calls[1]?.[0].question).toBe('Will this work?');
    expect(screen.getAllByText('Will this work?', { selector: 'div' })).toHaveLength(1); // retry does not duplicate the user message
  });

  it('clears a conversation only after confirmation', async () => {
    vi.mocked(chatApi.askQuestion).mockResolvedValue({ answer: 'An answer.', sources: [source], insufficient_context: false });
    setup();
    await userEvent.type(screen.getByLabelText('Ask a question about your documents'), 'Tell me something{Enter}');
    await screen.findByText('An answer.');
    await userEvent.click(screen.getByRole('button', { name: /Clear conversation/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Clear conversation', hidden: false }));
    await waitFor(() => expect(screen.getByText('Ask anything about your documents.')).toBeInTheDocument());
  });
});
