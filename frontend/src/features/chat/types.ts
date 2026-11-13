/** Mirrors app/schemas/qa.py of the backend (QARequest, QAResponse, QASource). */
export interface QASource {
  source_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  chunk_index: number;
  similarity: number;
  excerpt: string;
}

export interface QARequest {
  question: string;
  top_k: number;
}

export interface QAResponse {
  answer: string;
  sources: QASource[];
  insufficient_context: boolean;
}

/** Browser-only chat model. The backend has no conversation endpoints. */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  sources?: QASource[];
  insufficientContext?: boolean;
  /** Set on an assistant message when the request failed. */
  error?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export const DEFAULT_TOP_K = 5;
export const MAX_QUESTION_LENGTH = 2000;
export const MIN_QUESTION_LENGTH = 3;
