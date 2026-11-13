import { cn } from '@/lib/utils';

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn('h-8 w-8', className)} aria-hidden="true">
      <defs>
        <linearGradient id="nova-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" style={{ stopColor: 'rgb(var(--c-mint))' }} />
          <stop offset="1" style={{ stopColor: 'rgb(var(--c-deep))' }} />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#nova-mark)" />
      <path
        d="M10 23V9l12 14V9"
        fill="none"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ stroke: 'rgb(var(--c-ink))' }}
      />
    </svg>
  );
}

export function Wordmark({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <span className="flex items-center gap-3">
      <LogoMark />
      {!collapsed && <span className="text-[15px] font-semibold tracking-[0.18em] text-ink">NOVA DOCS</span>}
    </span>
  );
}
