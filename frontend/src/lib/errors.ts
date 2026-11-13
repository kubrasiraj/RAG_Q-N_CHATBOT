import axios from 'axios';

/** Every failed request is normalised into this shape. It never carries stack traces or raw bodies. */
export class ApiError extends Error {
  readonly status?: number;
  readonly code?: string;
  readonly retryAfterSeconds?: number;

  constructor(message: string, options: { status?: number; code?: string; retryAfterSeconds?: number } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = options.status;
    this.code = options.code;
    this.retryAfterSeconds = options.retryAfterSeconds;
  }
}

interface ParsedDetail {
  message?: string;
  code?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/** FastAPI returns `detail` as a string, a `{code, message}` object, or a list of validation errors. */
export function parseDetail(data: unknown): ParsedDetail {
  if (!isRecord(data)) return {};
  const detail = data.detail;
  if (typeof detail === 'string') return { message: detail };
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (isRecord(item) && typeof item.msg === 'string' ? item.msg.replace(/^Value error, /, '') : null))
      .filter((m): m is string => m !== null);
    return messages.length > 0 ? { message: messages.join(' ') } : {};
  }
  if (isRecord(detail)) {
    return {
      message: typeof detail.message === 'string' ? detail.message : undefined,
      code: typeof detail.code === 'string' ? detail.code : undefined,
    };
  }
  return {};
}

const STATUS_FALLBACKS: Record<number, string> = {
  400: 'The request was not accepted. Please check it and try again.',
  401: 'Your session is not valid. Please sign in again.',
  403: 'You do not have permission to do that.',
  404: 'The requested item was not found.',
  413: 'The file is too large.',
  415: 'That file type is not supported.',
  422: 'Some of the submitted information is not valid.',
  429: 'Too many requests. Please wait a moment and try again.',
};

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isCancel(error)) return new ApiError('Request cancelled.', { code: 'CANCELED' });

  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      return new ApiError('The request took too long. Please try again.', { code: 'TIMEOUT' });
    }
    if (!error.response) {
      return new ApiError('Cannot reach the server. Check your connection and that the backend is running.', {
        code: 'NETWORK',
      });
    }
    const { status, data, headers } = error.response;
    const detail = parseDetail(data);
    const retryHeader = Number(headers?.['retry-after']);
    const message =
      detail.message ??
      STATUS_FALLBACKS[status] ??
      (status >= 500 ? 'The server ran into a problem. Please try again shortly.' : 'Something went wrong.');
    return new ApiError(message, {
      status,
      code: detail.code,
      retryAfterSeconds: Number.isFinite(retryHeader) && retryHeader > 0 ? retryHeader : undefined,
    });
  }

  return new ApiError('Something went wrong. Please try again.');
}
