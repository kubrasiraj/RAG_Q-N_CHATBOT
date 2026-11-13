function positiveNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export const config = {
  appName: 'NOVA DOCS',
  /** Default is same-origin `/api/v1`, served by the Vite proxy in dev. */
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL?.trim() || '/api/v1').replace(/\/+$/, ''),
  /** UI-side limit only. The backend (MAX_DOCUMENT_SIZE_MB) is authoritative. */
  maxUploadMb: positiveNumber(import.meta.env.VITE_MAX_UPLOAD_MB, 20),
} as const;
