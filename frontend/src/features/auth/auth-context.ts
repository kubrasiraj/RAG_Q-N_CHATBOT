import { createContext, useContext } from 'react';
import type { AuthStatus, Credentials, User } from './types';

export interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  /** Unix seconds when the current token expires (read from the unverified payload, for display only). */
  tokenExpiresAt: number | null;
  login: (credentials: Credentials) => Promise<void>;
  register: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>.');
  return value;
}
