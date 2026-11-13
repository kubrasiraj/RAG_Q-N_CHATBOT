import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { AssistantBubble } from './MessageBubble';
import { SourceCard } from './SourceCard';
import type { ChatMessage, QASource } from './types';

const source: QASource = {
  source_id: 'S1',
  document_id: '11111111-1111-4111-8111-111111111111',
  filename: 'handbook.pdf',
  page_number: 4,
  chunk_index: 12,
  similarity: 0.83,
  excerpt: 'Employees accrue 1.5 vacation days per month.',
};

const base: ChatMessage = { id: 'm1', role: 'assistant', content: '', createdAt: '2026-11-11T10:00:00Z' };

describe('citations and sources', () => {
  it('renders real source fields and expands the excerpt', async () => {
    render(<SourceCard source={source} domId="s1" />);
    expect(screen.getByText('S1')).toBeInTheDocument();
    expect(screen.getByText('handbook.pdf')).toBeInTheDocument();
    expect(screen.getByText('Page 4')).toBeInTheDocument();
    expect(screen.getByText('Chunk 12')).toBeInTheDocument();
    expect(screen.getByText(/Similarity 0\.83/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { expanded: false }));
    expect(screen.getByText('Retrieved passage')).toBeInTheDocument();
  });

  it('never invents a page number when the backend returns null', () => {
    render(<SourceCard source={{ ...source, page_number: null }} domId="s2" />);
    expect(screen.getByText('Page not available')).toBeInTheDocument();
    expect(screen.queryByText(/^Page \d/)).not.toBeInTheDocument();
  });
});

describe('AssistantBubble', () => {
  it('shows the generated answer separately from retrieved evidence, with clickable [S1] markers', async () => {
    const message = { ...base, content: 'You get **1.5 days** per month [S1]. Unknown [S9].', sources: [source], insufficientContext: false };
    render(<AssistantBubble message={message} canRetry={false} onRetry={() => {}} />);
    expect(screen.getByText('Generated answer')).toBeInTheDocument();
    expect(screen.getByText(/Retrieved evidence · 1 source/)).toBeInTheDocument();
    expect(screen.getByText(/\[S9\]/)).toBeInTheDocument(); // not a returned source, so it stays plain text
    await userEvent.click(screen.getByRole('button', { name: 'Show source S1' }));
    expect(screen.getByText('Retrieved passage')).toBeInTheDocument();
  });

  it('renders insufficient context distinctly and without sources', () => {
    const message = { ...base, content: 'The documents do not mention this.', sources: [], insufficientContext: true };
    render(<AssistantBubble message={message} canRetry={false} onRetry={() => {}} />);
    expect(screen.getByText('Not enough evidence in your documents')).toBeInTheDocument();
    expect(screen.getByText('The documents do not mention this.')).toBeInTheDocument();
    expect(screen.queryByText('Generated answer')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Retrieved sources')).not.toBeInTheDocument();
  });

  it('does not inject raw HTML from model output and makes links safe', () => {
    const content = '<img src=x onerror="alert(1)"><script>alert(2)</script>\n\n[docs](https://example.com)';
    const { container } = render(<AssistantBubble message={{ ...base, content, sources: [source] }} canRetry={false} onRetry={() => {}} />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    const link = screen.getByRole('link', { name: 'docs' });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link.getAttribute('rel')).toContain('noopener');
  });

  it('offers retry on errors', async () => {
    const onRetry = vi.fn();
    render(<AssistantBubble message={{ ...base, error: 'The AI service is temporarily unavailable.' }} canRetry onRetry={onRetry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('The AI service is temporarily unavailable.');
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
