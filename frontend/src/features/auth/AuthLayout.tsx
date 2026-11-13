import type { ReactNode } from 'react';
import { FileSearch, Quote, ShieldCheck } from 'lucide-react';
import { Wordmark } from '@/components/ui/Logo';

const points = [
  { icon: FileSearch, text: 'Answers grounded in the documents you upload' },
  { icon: Quote, text: 'Every answer shows the source passages it used' },
  { icon: ShieldCheck, text: 'Your documents stay private to your account' },
];

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-full bg-app lg:grid-cols-[1.05fr_1fr]">
      <aside className="ambient relative hidden flex-col justify-between overflow-hidden border-r border-line bg-sidebar p-12 lg:flex">
        <Wordmark />
        <div className="relative max-w-md">
          <p className="eyebrow mb-4 text-brand-mint">AI document workspace</p>
          <h1 className="text-4xl font-semibold leading-tight tracking-tight">Your Documents. Your Knowledge. One AI Workspace.</h1>
          <ul className="mt-10 space-y-4">
            {points.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-ink-soft">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-card text-brand-mint">
                  <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-ink-muted">PDF, DOCX and TXT. Retrieval-augmented answers with citations.</p>
      </aside>

      <main className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-md animate-fade-up">
          <div className="mb-10 lg:hidden">
            <Wordmark />
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-1.5 text-ink-soft">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
