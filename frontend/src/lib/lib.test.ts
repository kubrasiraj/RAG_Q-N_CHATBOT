import { AxiosError, type AxiosResponse } from 'axios';
import { toApiError, parseDetail } from './errors';
import { getTokenExpiry, isTokenExpired, tokenStore } from './auth';
import { displayNameFromEmail, formatBytes } from './utils';

function jwt(payload: object): string {
  const b64 = (o: object) => btoa(JSON.stringify(o)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
  return `${b64({ alg: 'HS256' })}.${b64(payload)}.sig`;
}

function axiosFailure(status: number, data: unknown, headers: Record<string, string> = {}) {
  const response = { status, data, headers, statusText: '', config: {} } as unknown as AxiosResponse;
  return new AxiosError('failed', 'ERR_BAD_REQUEST', undefined, undefined, response);
}

describe('utils', () => {
  it('formats byte sizes', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(2048)).toBe('2.0 KB');
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB');
  });
  it('derives a display name from the email local part', () => {
    expect(displayNameFromEmail('nafea@example.com')).toBe('nafea');
  });
});

describe('error normalisation', () => {
  it('reads FastAPI string, object and validation-list details', () => {
    expect(parseDetail({ detail: 'Invalid email or password.' }).message).toBe('Invalid email or password.');
    expect(parseDetail({ detail: { code: 'AI_RATE_LIMITED', message: 'Slow down.' } })).toEqual({ code: 'AI_RATE_LIMITED', message: 'Slow down.' });
    expect(parseDetail({ detail: [{ msg: 'Value error, Question cannot be empty.' }] }).message).toBe('Question cannot be empty.');
  });
  it('maps a 503 rate limit including Retry-After', () => {
    const error = toApiError(axiosFailure(503, { detail: { code: 'AI_RATE_LIMITED', message: 'Rate limited.' } }, { 'retry-after': '20' }));
    expect(error.message).toBe('Rate limited.');
    expect(error.code).toBe('AI_RATE_LIMITED');
    expect(error.retryAfterSeconds).toBe(20);
  });
  it('uses a safe fallback and never leaks raw bodies for unknown server errors', () => {
    const error = toApiError(axiosFailure(500, '<html>Traceback (most recent call last)...</html>'));
    expect(error.message).toBe('The server ran into a problem. Please try again shortly.');
  });
  it('reports an unreachable server', () => {
    const error = toApiError(new AxiosError('Network Error', 'ERR_NETWORK'));
    expect(error.code).toBe('NETWORK');
  });
});

describe('token handling', () => {
  afterEach(() => tokenStore.clear());

  it('reads expiry from the payload and detects expired tokens', () => {
    const future = Math.floor(Date.now() / 1000) + 600;
    const past = Math.floor(Date.now() / 1000) - 600;
    expect(getTokenExpiry(jwt({ exp: future }))).toBe(future);
    expect(isTokenExpired(jwt({ exp: future }))).toBe(false);
    expect(isTokenExpired(jwt({ exp: past }))).toBe(true);
    expect(getTokenExpiry('not-a-jwt')).toBeNull();
  });

  it('keeps the token in sessionStorage only, never localStorage', () => {
    tokenStore.set('abc.def.ghi');
    expect(sessionStorage.getItem('novadocs.access_token')).toBe('abc.def.ghi');
    expect(Object.keys(localStorage)).toHaveLength(0);
    tokenStore.clear();
    expect(sessionStorage.getItem('novadocs.access_token')).toBeNull();
    expect(tokenStore.get()).toBeNull();
  });
});
