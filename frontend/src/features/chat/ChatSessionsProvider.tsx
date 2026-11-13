import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from 'react';
import { toApiError } from '@/lib/errors';
import { uid } from '@/lib/utils';
import { chatApi } from './api';
import { ChatSessionsContext, type ChatSessionsContextValue } from './sessions-context';
import { clearSessions, loadSessions, saveSessions } from './storage';
import { DEFAULT_TOP_K, MIN_QUESTION_LENGTH, type ChatMessage, type ChatSession } from './types';

type Action =
  | { type: 'create'; session: ChatSession }
  | { type: 'delete'; sessionId: string }
  | { type: 'clear'; sessionId: string }
  | { type: 'clearAll' }
  | { type: 'append'; sessionId: string; message: ChatMessage }
  | { type: 'removeMessage'; sessionId: string; messageId: string };

const DEFAULT_TITLE = 'New chat';

function titleFrom(question: string): string {
  const clean = question.replace(/\s+/g, ' ').trim();
  return clean.length > 48 ? `${clean.slice(0, 47)}…` : clean;
}

function reducer(state: ChatSession[], action: Action): ChatSession[] {
  switch (action.type) {
    case 'create':
      return [action.session, ...state];
    case 'delete':
      return state.filter((s) => s.id !== action.sessionId);
    case 'clear':
      return state.map((s) => (s.id === action.sessionId ? { ...s, title: DEFAULT_TITLE, messages: [], updatedAt: new Date().toISOString() } : s));
    case 'clearAll':
      return [];
    case 'append':
      return state
        .map((s) =>
          s.id === action.sessionId
            ? {
                ...s,
                title: s.title === DEFAULT_TITLE && action.message.role === 'user' ? titleFrom(action.message.content) : s.title,
                messages: [...s.messages, action.message],
                updatedAt: action.message.createdAt,
              }
            : s,
        )
        .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
    case 'removeMessage':
      return state.map((s) => (s.id === action.sessionId ? { ...s, messages: s.messages.filter((m) => m.id !== action.messageId) } : s));
  }
}

export function ChatSessionsProvider({ userId, children }: { userId: string; children: ReactNode }) {
  const [sessions, dispatch] = useReducer(reducer, userId, loadSessions);
  const [pending, setPending] = useState<ReadonlySet<string>>(new Set());
  const controllers = useRef(new Map<string, AbortController>());
  const sessionsRef = useRef(sessions);

  useEffect(() => {
    sessionsRef.current = sessions;
    saveSessions(userId, sessions);
  }, [sessions, userId]);

  // Abort anything still in flight when the provider goes away (logout / unmount).
  useEffect(() => {
    const active = controllers.current;
    return () => active.forEach((c) => c.abort());
  }, []);

  const setPendingFor = useCallback((sessionId: string, value: boolean) => {
    setPending((prev) => {
      const next = new Set(prev);
      if (value) next.add(sessionId);
      else next.delete(sessionId);
      return next;
    });
  }, []);

  const ask = useCallback<ChatSessionsContextValue['ask']>(
    async (sessionId, question, options = {}) => {
      const text = question.trim();
      if (text.length < MIN_QUESTION_LENGTH || controllers.current.has(sessionId)) return; // no duplicate submissions

      if (!options.reuseLastUserMessage) {
        dispatch({
          type: 'append',
          sessionId,
          message: { id: uid(), role: 'user', content: text, createdAt: new Date().toISOString() },
        });
      }

      const controller = new AbortController();
      controllers.current.set(sessionId, controller);
      setPendingFor(sessionId, true);

      try {
        const response = await chatApi.askQuestion({ question: text, top_k: options.topK ?? DEFAULT_TOP_K }, controller.signal);
        dispatch({
          type: 'append',
          sessionId,
          message: {
            id: uid(),
            role: 'assistant',
            content: response.answer,
            sources: response.sources,
            insufficientContext: response.insufficient_context,
            createdAt: new Date().toISOString(),
          },
        });
      } catch (error) {
        const apiError = toApiError(error);
        const retrySuffix = apiError.retryAfterSeconds ? ` Try again in about ${apiError.retryAfterSeconds} seconds.` : '';
        dispatch({
          type: 'append',
          sessionId,
          message: { id: uid(), role: 'assistant', content: '', error: apiError.message + retrySuffix, createdAt: new Date().toISOString() },
        });
      } finally {
        controllers.current.delete(sessionId);
        setPendingFor(sessionId, false);
      }
    },
    [setPendingFor],
  );

  const retry = useCallback<ChatSessionsContextValue['retry']>(
    async (sessionId, assistantMessageId, topK) => {
      const session = sessionsRef.current.find((s) => s.id === sessionId);
      if (!session || controllers.current.has(sessionId)) return;
      const index = session.messages.findIndex((m) => m.id === assistantMessageId);
      const question = session.messages
        .slice(0, Math.max(index, 0))
        .reverse()
        .find((m) => m.role === 'user');
      if (index < 0 || !question) return;
      dispatch({ type: 'removeMessage', sessionId, messageId: assistantMessageId });
      await ask(sessionId, question.content, { topK, reuseLastUserMessage: true });
    },
    [ask],
  );

  const cancel = useCallback((sessionId: string) => controllers.current.get(sessionId)?.abort(), []);

  const value = useMemo<ChatSessionsContextValue>(
    () => ({
      sessions,
      isPending: (id) => pending.has(id),
      getSession: (id) => sessions.find((s) => s.id === id),
      createSession: () => {
        const now = new Date().toISOString();
        const session: ChatSession = { id: uid(), title: DEFAULT_TITLE, createdAt: now, updatedAt: now, messages: [] };
        dispatch({ type: 'create', session });
        return session.id;
      },
      deleteSession: (id) => {
        controllers.current.get(id)?.abort();
        dispatch({ type: 'delete', sessionId: id });
      },
      clearSession: (id) => {
        controllers.current.get(id)?.abort();
        dispatch({ type: 'clear', sessionId: id });
      },
      clearAll: () => {
        controllers.current.forEach((c) => c.abort());
        dispatch({ type: 'clearAll' });
        clearSessions(userId);
      },
      ask,
      retry,
      cancel,
    }),
    [sessions, pending, ask, retry, cancel, userId],
  );

  return <ChatSessionsContext.Provider value={value}>{children}</ChatSessionsContext.Provider>;
}
