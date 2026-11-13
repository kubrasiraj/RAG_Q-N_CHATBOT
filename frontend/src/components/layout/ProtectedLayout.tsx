import { ChatSessionsProvider } from '@/features/chat/ChatSessionsProvider';
import { useAuth } from '@/features/auth/auth-context';
import { AppShell } from './AppShell';

export function ProtectedLayout() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <ChatSessionsProvider key={user.id} userId={user.id}>
      <AppShell />
    </ChatSessionsProvider>
  );
}
