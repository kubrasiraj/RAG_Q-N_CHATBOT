/** Mirrors app/schemas/document.py of the backend. */
export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface DocumentItem {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  page_count: number | null;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
}

export interface DocumentList {
  items: DocumentItem[];
  total: number;
}
