import { useEffect, useRef, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { FolderOpen, LayoutDashboard, LogOut, Menu, MessageSquare, MessageSquarePlus, PanelLeftClose, PanelLeftOpen, Settings, X } from 'lucide-react';
import { useAuth } from '@/features/auth/auth-context';
import { useChatSessions } from '@/features/chat/sessions-context';
import { cn } from '@/lib/utils';
import { Wordmark } from '@/components/ui/Logo';

const COLLAPSE_KEY = 'novadocs.sidebar.collapsed';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/documents', label: 'Documents', icon: FolderOpen, end: false },
] as const;

function navClass(collapsed: boolean) {
  return ({ isActive }: { isActive: boolean }) =>
    cn(
      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
      collapsed && 'justify-center px-0',
      isActive ? 'bg-brand/15 text-brand-mint shadow-[inset_2px_0_0_rgb(var(--c-brand))]' : 'text-ink-soft hover:bg-elevated hover:text-ink',
    );
}

function SidebarContent({ collapsed, onNavigate, onToggle }: { collapsed: boolean; onNavigate?: () => void; onToggle?: () => void }) {
  const { user, logout } = useAuth();
  const { sessions, deleteSession } = useChatSessions();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="flex h-full flex-col">
      <div className={cn('flex items-center px-4 py-5', collapsed ? 'justify-center' : 'justify-between')}>
        <Wordmark collapsed={collapsed} />
        {onToggle && !collapsed && (
          <button type="button" onClick={onToggle} aria-label="Collapse sidebar" className="rounded-lg p-2 text-ink-muted hover:bg-elevated hover:text-ink">
            <PanelLeftClose className="h-[18px] w-[18px]" aria-hidden="true" />
          </button>
        )}
      </div>

      <div className="px-3">
        <button
          type="button"
          onClick={() => {
            navigate('/chat');
            onNavigate?.();
          }}
          title="New chat"
          className={cn(
            'flex w-full items-center gap-2.5 rounded-xl bg-brand py-2.5 text-sm font-semibold text-app shadow-[0_0_24px_-8px_rgb(var(--c-brand)/0.8)] transition-colors hover:bg-brand-mint',
            collapsed ? 'justify-center' : 'px-3.5',
          )}
        >
          <MessageSquarePlus className="h-[18px] w-[18px]" aria-hidden="true" />
          {!collapsed && 'New chat'}
          {collapsed && <span className="sr-only">New chat</span>}
        </button>
      </div>

      <nav aria-label="Main" className="mt-5 space-y-1 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} title={label} onClick={onNavigate} className={navClass(collapsed)}>
            <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
            {collapsed ? <span className="sr-only">{label}</span> : label}
          </NavLink>
        ))}
        <NavLink
          to="/chat"
          title="Chat"
          onClick={onNavigate}
          className={({ isActive }) => navClass(collapsed)({ isActive })}
        >
          <MessageSquare className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
          {collapsed ? <span className="sr-only">Chat</span> : 'Chat'}
        </NavLink>
      </nav>

      <div className="mt-5 min-h-0 flex-1 overflow-y-auto px-3">
        {!collapsed && sessions.length > 0 && (
          <>
            <p className="eyebrow px-3 pb-2" title="Stored in this browser only">
              Recent chats · this browser
            </p>
            <ul className="space-y-0.5">
              {sessions.slice(0, 10).map((s) => (
                <li key={s.id} className="group relative">
                  <NavLink
                    to={`/chat/${s.id}`}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      cn('block truncate rounded-lg py-2 pl-3 pr-9 text-sm transition-colors', isActive ? 'bg-elevated text-ink' : 'text-ink-soft hover:bg-elevated/60 hover:text-ink')
                    }
                  >
                    {s.title}
                  </NavLink>
                  <button
                    type="button"
                    aria-label={`Delete chat ${s.title}`}
                    onClick={() => {
                      deleteSession(s.id);
                      if (location.pathname === `/chat/${s.id}`) navigate('/chat');
                    }}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-ink-muted opacity-60 hover:bg-card hover:text-danger group-hover:opacity-100 focus:opacity-100"
                  >
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="space-y-1 border-t border-line p-3">
        <NavLink to="/settings" title="Settings" onClick={onNavigate} className={navClass(collapsed)}>
          <Settings className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
          {collapsed ? <span className="sr-only">Settings</span> : 'Settings'}
        </NavLink>
        <div className={cn('flex items-center gap-3 rounded-xl px-2 py-2', collapsed && 'justify-center px-0')}>
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-brand/40 bg-brand-deep text-sm font-semibold uppercase text-brand-mint" aria-hidden="true">
            {user?.email.charAt(0) ?? '?'}
          </span>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" title={user?.email}>
                {user?.email}
              </p>
              <p className="text-xs capitalize text-ink-muted">{user?.role}</p>
            </div>
          )}
          {!collapsed && (
            <button type="button" onClick={logout} aria-label="Sign out" className="rounded-lg p-2 text-ink-muted hover:bg-elevated hover:text-danger">
              <LogOut className="h-[18px] w-[18px]" aria-hidden="true" />
            </button>
          )}
        </div>
        {collapsed && (
          <>
            <button type="button" onClick={logout} aria-label="Sign out" className="flex w-full justify-center rounded-lg p-2.5 text-ink-muted hover:bg-elevated hover:text-danger">
              <LogOut className="h-[18px] w-[18px]" aria-hidden="true" />
            </button>
            {onToggle && (
              <button type="button" onClick={onToggle} aria-label="Expand sidebar" className="flex w-full justify-center rounded-lg p-2.5 text-ink-muted hover:bg-elevated hover:text-ink">
                <PanelLeftOpen className="h-[18px] w-[18px]" aria-hidden="true" />
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  const toggle = () =>
    setCollapsed((value) => {
      try {
        localStorage.setItem(COLLAPSE_KEY, value ? '0' : '1');
      } catch {
        /* preference just will not persist */
      }
      return !value;
    });

  useEffect(() => {
    if (!drawerOpen) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawerOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  return (
    <div className="flex h-full bg-app">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-brand focus:px-4 focus:py-2 focus:text-app">
        Skip to main content
      </a>

      <aside className={cn('hidden shrink-0 border-r border-line bg-sidebar transition-[width] duration-200 lg:block', collapsed ? 'w-[76px]' : 'w-72')}>
        <SidebarContent collapsed={collapsed} onToggle={toggle} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-sidebar px-4 py-3 lg:hidden">
          <Wordmark />
          <button type="button" onClick={() => setDrawerOpen(true)} aria-label="Open navigation" className="flex h-11 w-11 items-center justify-center rounded-xl text-ink-soft hover:bg-elevated">
            <Menu className="h-6 w-6" aria-hidden="true" />
          </button>
        </header>
        <main id="main" tabIndex={-1} className="min-h-0 flex-1 bg-workspace focus:outline-none">
          <Outlet />
        </main>
      </div>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/70" onClick={() => setDrawerOpen(false)} aria-hidden="true" />
          <aside role="dialog" aria-modal="true" aria-label="Navigation" className="absolute inset-y-0 left-0 w-[85%] max-w-xs animate-fade-up border-r border-line bg-sidebar">
            <button
              ref={closeRef}
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close navigation"
              className="absolute right-3 top-4 z-10 flex h-10 w-10 items-center justify-center rounded-lg text-ink-soft hover:bg-elevated"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
            <SidebarContent collapsed={false} onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      )}
    </div>
  );
}
