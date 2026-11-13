import axios from 'axios';
import { config } from './config';
import { tokenStore } from './auth';
import { toApiError } from './errors';

export const api = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 30_000,
});

let onUnauthorized: (() => void) | null = null;

/** The auth provider registers a handler so any 401 on a protected call ends the session cleanly. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

api.interceptors.request.use((request) => {
  const token = tokenStore.get();
  if (token) request.headers.set('Authorization', `Bearer ${token}`);
  return request;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      !error.config?.url?.includes('/auth/login') &&
      tokenStore.get()
    ) {
      onUnauthorized?.();
    }
    return Promise.reject(toApiError(error));
  },
);
