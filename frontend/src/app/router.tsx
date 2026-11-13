import { createBrowserRouter } from 'react-router-dom';
import { NotFoundPage } from '@/components/common/NotFoundPage';
import { ProtectedLayout } from '@/components/layout/ProtectedLayout';
import { LoginPage } from '@/features/auth/LoginPage';
import { RegisterPage } from '@/features/auth/RegisterPage';
import { ProtectedRoute, PublicOnlyRoute } from '@/features/auth/RouteGuards';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { DocumentsPage } from '@/features/documents/DocumentsPage';

// Chat pulls in the Markdown renderer, so it is loaded on demand to keep the first load small.
const loadChat = async () => ({ Component: (await import('@/features/chat/ChatPage')).ChatPage });
const loadSettings = async () => ({ Component: (await import('@/features/settings/SettingsPage')).SettingsPage });

export const router = createBrowserRouter([
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <ProtectedLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'documents', element: <DocumentsPage /> },
          { path: 'chat', lazy: loadChat },
          { path: 'chat/:sessionId', lazy: loadChat },
          { path: 'settings', lazy: loadSettings },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
