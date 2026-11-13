import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { setUnauthorizedHandler } from '@/lib/api-client';
import { getTokenExpiry, isTokenExpired, tokenStore } from '@/lib/auth';
import { authApi } from './api';
import { AuthContext, type AuthContextValue } from './auth-context';
import type { AuthStatus, Credentials, User } from './types';

const MAX_TIMEOUT_MS = 2 ** 31 - 1;

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  // A stored token that is already expired is dropped immediately; a live one is verified via /auth/me.
  const [status, setStatus] = useState<AuthStatus>(() => {
    const token = tokenStore.get();
    if (token && isTokenExpired(token)) tokenStore.clear();
    return tokenStore.get() ? 'loading' : 'unauthenticated';
  });
  const [tokenExpiresAt, setTokenExpiresAt] = useState<number | null>(() => {
    const token = tokenStore.get();
    return token ? getTokenExpiry(token) : null;
  });
  const timer = useRef<number | undefined>(undefined);

  const endSession = useCallback(() => {
    window.clearTimeout(timer.current);
    tokenStore.clear();
    setUser(null);
    setTokenExpiresAt(null);
    setStatus('unauthenticated');
    queryClient.clear();
  }, [queryClient]);

  const expireSession = useCallback(() => {
    endSession();
    toast.error('Your session has expired. Please sign in again.');
  }, [endSession]);

  /** Arms the "session expired" timer. It sets no state, so it is safe to call from effects. */
  const armExpiryTimer = useCallback(
    (token: string) => {
      window.clearTimeout(timer.current);
      const exp = getTokenExpiry(token);
      if (exp === null) return;
      const delay = Math.max(0, exp * 1000 - Date.now());
      timer.current = window.setTimeout(expireSession, Math.min(delay, MAX_TIMEOUT_MS));
    },
    [expireSession],
  );

  // A 401 on any protected request ends the session.
  useEffect(() => {
    setUnauthorizedHandler(expireSession);
    return () => setUnauthorizedHandler(null);
  }, [expireSession]);

  // Restore a session after a reload, but only if the stored token is still valid server-side.
  useEffect(() => {
    let cancelled = false;
    const token = tokenStore.get();
    if (!token) return;
    armExpiryTimer(token);
    authApi
      .me()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus('authenticated');
      })
      .catch(() => {
        if (!cancelled) endSession();
      });
    return () => {
      cancelled = true;
      window.clearTimeout(timer.current);
    };
  }, [armExpiryTimer, endSession]);

  const login = useCallback(
    async (credentials: Credentials) => {
      const { access_token } = await authApi.login(credentials);
      tokenStore.set(access_token);
      try {
        const me = await authApi.me();
        setUser(me);
        setStatus('authenticated');
        setTokenExpiresAt(getTokenExpiry(access_token));
        armExpiryTimer(access_token);
      } catch (error) {
        tokenStore.clear();
        throw error;
      }
    },
    [armExpiryTimer],
  );

  const register = useCallback(
    async (credentials: Credentials) => {
      await authApi.register(credentials);
      await login(credentials);
    },
    [login],
  );

  const logout = useCallback(() => {
    endSession();
    toast.success('You have been signed out.');
  }, [endSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, tokenExpiresAt, login, register, logout }),
    [user, status, tokenExpiresAt, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
