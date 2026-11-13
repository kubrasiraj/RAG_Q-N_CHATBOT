import { createContext, useContext } from 'react';
import type { ChatSession } from './types';

export interface AskOptions {
  topK?: number;
  /** Re-ask using the existing last user message instead of appending a new one. */
  reuseLastUserMessage?: boolean;
}

export interface ChatSessionsContextValue {
  sessions: ChatSession[];
  isPending: (sessionId: string) => boolean;
  getSession: (sessionId: string) => ChatSession | undefined;
  createSession: () => string;
  deleteSession: (sessionId: string) => void;
  clearSession: (sessionId: string) => void;
  clearAll: () => void;
  ask: (sessionId: string, question: string, options?: AskOptions) => Promise<void>;
  /** Removes an assistant message and asks its question again (safe: asking is read-only). */
  retry: (sessionId: string, assistantMessageId: string, topK?: number) => Promise<void>;
  cancel: (sessionId: string) => void;
}

export const ChatSessionsContext = createContext<ChatSessionsContextValue | null>(null);

export function useChatSessions(): ChatSessionsContextValue {
  const value = useContext(ChatSessionsContext);
  if (!value) throw new Error('useChatSessions must be used inside <ChatSessionsProvider>.');
  return value;
}
