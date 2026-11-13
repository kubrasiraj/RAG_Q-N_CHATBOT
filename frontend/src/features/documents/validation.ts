import { formatBytes } from '@/lib/utils';

export const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.txt'] as const;
export const ACCEPT_ATTRIBUTE = ACCEPTED_EXTENSIONS.join(',');

/**
 * UX-only pre-check so people get instant feedback. The backend validates type, size, emptiness
 * and file integrity again and remains the authority.
 */
export function validateFile(file: Pick<File, 'name' | 'size'>, maxMb: number): string | null {
  const dot = file.name.lastIndexOf('.');
  const extension = dot >= 0 ? file.name.slice(dot).toLowerCase() : '';
  if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(extension)) {
    return 'Unsupported file type. Use PDF, DOCX or TXT.';
  }
  if (file.size === 0) return 'This file is empty.';
  if (file.size > maxMb * 1024 * 1024) {
    return `File is ${formatBytes(file.size)}. The limit is ${maxMb} MB.`;
  }
  return null;
}

export function fileKind(filename: string): 'PDF' | 'DOCX' | 'TXT' | 'FILE' {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.pdf')) return 'PDF';
  if (lower.endsWith('.docx')) return 'DOCX';
  if (lower.endsWith('.txt')) return 'TXT';
  return 'FILE';
}
