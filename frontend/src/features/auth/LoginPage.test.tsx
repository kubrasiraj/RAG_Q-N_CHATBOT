import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { ApiError } from '@/lib/errors';
import { tokenStore } from '@/lib/auth';
import { renderWithProviders } from '@/test/render';
import { authApi } from './api';
import { AuthProvider } from './AuthProvider';
import { LoginPage } from './LoginPage';

vi.mock('./api', () => ({ authApi: { login: vi.fn(), register: vi.fn(), me: vi.fn() } }));

const me = { id: 'u1', email: 'dev@example.com', role: 'customer', is_active: true, created_at: '2026-01-01T00:00:00Z' };

function setup() {
  return renderWithProviders(
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<p>Workspace home</p>} />
      </Routes>
    </AuthProvider>,
    '/login',
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    tokenStore.clear();
  });

  it('validates the email and password before calling the API', async () => {
    setup();
    await userEvent.type(screen.getByLabelText('Email'), 'not-an-email');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument();
    expect(screen.getByText('Enter your password.')).toBeInTheDocument();
    expect(authApi.login).not.toHaveBeenCalled();
  });

  it('signs in with the exact backend fields, stores the token and navigates home', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'tok.en.value', token_type: 'bearer' });
    vi.mocked(authApi.me).mockResolvedValue(me);
    setup();
    await userEvent.type(screen.getByLabelText('Email'), 'dev@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'correct horse');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByText('Workspace home')).toBeInTheDocument();
    expect(authApi.login).toHaveBeenCalledWith({ email: 'dev@example.com', password: 'correct horse' });
    expect(tokenStore.get()).toBe('tok.en.value');
    expect(Object.keys(localStorage)).toHaveLength(0);
  });

  it('shows the backend error message when credentials are rejected', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new ApiError('Invalid email or password.', { status: 401 }));
    setup();
    await userEvent.type(screen.getByLabelText('Email'), 'dev@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.');
    expect(tokenStore.get()).toBeNull();
  });

  it('toggles password visibility', async () => {
    setup();
    const field = screen.getByLabelText('Password');
    expect(field).toHaveAttribute('type', 'password');
    await userEvent.click(screen.getByRole('button', { name: 'Show password' }));
    await waitFor(() => expect(field).toHaveAttribute('type', 'text'));
  });
});
