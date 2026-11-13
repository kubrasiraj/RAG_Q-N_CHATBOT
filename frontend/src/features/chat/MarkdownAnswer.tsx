import { Children, isValidElement, type ReactNode } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';

const MARKER = /\[(S\d+)\]/g;

/** Turns `[S1]`-style markers into buttons, but only for source ids that were actually returned. */
function withCitations(children: ReactNode, sourceIds: ReadonlySet<string>, onCite: (id: string) => void): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child !== 'string') return isValidElement(child) ? child : child;
    const parts = child.split(MARKER);
    if (parts.length === 1) return child;
    return parts.map((part, i) =>
      i % 2 === 1 && sourceIds.has(part) ? (
        <button
          key={i}
          type="button"
          onClick={() => onCite(part)}
          aria-label={`Show source ${part}`}
          className="mx-0.5 inline-flex h-5 min-w-[1.5rem] items-center justify-center rounded-md border border-brand/40 bg-brand-deep/50 px-1 align-baseline text-[11px] font-semibold text-brand-mint hover:bg-brand-deep"
        >
          {part}
        </button>
      ) : i % 2 === 1 ? (
        `[${part}]`
      ) : (
        part
      ),
    );
  });
}

interface MarkdownAnswerProps {
  content: string;
  sourceIds: ReadonlySet<string>;
  onCite: (sourceId: string) => void;
}

/** Raw HTML is not enabled in react-markdown, and rehype-sanitize filters the output as a second layer. */
export function MarkdownAnswer({ content, sourceIds, onCite }: MarkdownAnswerProps) {
  const wrap = (children: ReactNode) => withCitations(children, sourceIds, onCite);
  const components: Components = {
    p: ({ children }) => <p>{wrap(children)}</p>,
    li: ({ children }) => <li>{wrap(children)}</li>,
    td: ({ children }) => <td>{wrap(children)}</td>,
    strong: ({ children }) => <strong>{wrap(children)}</strong>,
    em: ({ children }) => <em>{wrap(children)}</em>,
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noopener noreferrer nofollow">
        {children}
      </a>
    ),
    table: ({ children }) => (
      <div className="overflow-x-auto">
        <table>{children}</table>
      </div>
    ),
  };

  return (
    <div className="prose-nova">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
