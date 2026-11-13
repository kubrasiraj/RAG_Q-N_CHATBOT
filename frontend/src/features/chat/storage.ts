import type { ChatSession } from './types';

const MAX_SESSIONS = 30;
const MAX_MESSAGES = 200;

const keyFor = (userId: string) => `novadocs.chats.v1.${userId}`;

function isSession(value: unknown): value is ChatSession {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.id === 'string' && typeof v.title === 'string' && Array.isArray(v.messages);
}

/**
 * Local chat sessions live in this browser only (localStorage, one key per user id). They include
 * answers and source excerpts from the user's documents, so they are never sent anywhere else.
 */
export function loadSessions(userId: string): ChatSession[] {
  try {
    const raw = localStorage.getItem(keyFor(userId));
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isSession) : [];
  } catch {
    return [];
  }
}

export function saveSessions(userId: string, sessions: ChatSession[]): void {
  const trimmed = sessions.slice(0, MAX_SESSIONS).map((s) => ({ ...s, messages: s.messages.slice(-MAX_MESSAGES) }));
  try {
    localStorage.setItem(keyFor(userId), JSON.stringify(trimmed));
  } catch {
    /* storage full or unavailable: sessions stay in memory for this visit */
  }
}

export function clearSessions(userId: string): void {
  try {
    localStorage.removeItem(keyFor(userId));
  } catch {
    /* ignore */
  }
}
