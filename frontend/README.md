# NOVA DOCS frontend

React + TypeScript + Vite + Tailwind frontend for the Document Q&A RAG backend in this repository.
Design system: **Obsidian Emerald** (dark). All colors are tokens in `src/styles/globals.css`.

The backend is untouched. Everything lives in `frontend/`.

## Run it (Windows PowerShell)

Backend (from the repository root, as you already do):

```powershell
docker compose up -d
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8000
```

Frontend (second terminal):

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. Register an account and upload a document. It is processed automatically; the status on the Documents page goes Pending, Processing, Completed.

## Document processing

Uploading a file saves it and creates a record with status `pending`. The backend then processes it in the
background (FastAPI `BackgroundTasks`, see `app/services/document_background.py`):
`pending` then `processing` then `completed`, or `failed` if anything goes wrong. A document can be used for
answers only once it is `completed`.

The Documents page shows the real status from the API. It re-checks every 3 seconds while something is
`processing`, every 5 seconds while something is `pending`, and stops as soon as every document is
`completed` or `failed`. There are no fake progress bars. The first document after a backend start can take
longer because the embedding model loads (and downloads on the very first run).

### Limitations of this first version

- Background tasks are not durable. If the backend restarts or auto-reloads while a document is being
  processed, that document can stay in `processing` (or `pending` if it never started). For production,
  move this to a real job queue.
- The API does not expose why a document failed; the reason is only in the backend log.

### Optional fallback script

`scripts/process_pending.py` reuses the backend's `process_document()` by hand. You only need it for documents
that are stuck in `pending` or `failed` (for example uploaded before automatic processing existed).
Run it from the **repository root** in the backend's Poetry environment:

```powershell
poetry run python .\frontend\scripts\process_pending.py --email you@example.com --dry-run
poetry run python .\frontend\scripts\process_pending.py --email you@example.com
# optional: --retry-failed  --document-id <uuid>  --limit 3  --yes  --verbose
```

It authenticates with the backend's `authenticate_user()` (hidden password prompt), processes only that
user's documents, skips ones already `processing`, and prints the real status read back from the database.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with `/api` proxied to the backend |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint |
| `npm test` | Vitest (component and logic tests with mocked API modules) |
| `npm run build` | Type check + production build into `dist/` |
| `npm run preview` | Serve the production build (proxy applies here too) |

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Where the Vite dev/preview server forwards `/api` |
| `VITE_API_BASE_URL` | `/api/v1` (same origin) | Set only if the browser should call the API directly (requires backend CORS) |
| `VITE_MAX_UPLOAD_MB` | `20` | UI-side file size check. Keep equal to the backend's `MAX_DOCUMENT_SIZE_MB` |

## Backend endpoints used

| Feature | Endpoint |
|---|---|
| Register | `POST /api/v1/auth/register` `{email, password}` |
| Login | `POST /api/v1/auth/login` `{email, password}` returns `{access_token, token_type}` |
| Current user | `GET /api/v1/auth/me` |
| Upload | `POST /api/v1/documents/upload` (multipart field `file`) |
| List | `GET /api/v1/documents/?skip&limit` returns `{items, total}` |
| Detail | `GET /api/v1/documents/{id}` |
| Delete | `DELETE /api/v1/documents/{id}` (204) |
| Ask | `POST /api/v1/qa/ask` `{question (3-2000 chars), top_k (1-10)}` returns `{answer, sources[], insufficient_context}` |
| Health | `GET /api/v1/health`, `GET /api/v1/health/db` |

## Not supported by the backend (and therefore not faked)

- Durable background jobs, a failure reason for failed documents (see Document processing).
- Server-side conversation history: chat sessions are **local to this browser** and labelled as such.
- Streaming answers: `/qa/ask` returns one JSON response, so none is simulated.
- Document download or preview, failure reasons for failed documents, a max-upload-size endpoint,
  refresh tokens, profile editing, password change.
- CORS: the backend has no CORS middleware. Development uses the Vite proxy. For production, serve the
  built `dist/` and the API from the same origin (reverse proxy) or ask for a CORS change.

## Security notes

- Auth is a bearer JWT (30 minute expiry, no refresh, no cookies), so the token has to live in JavaScript.
  It is kept in memory and mirrored to `sessionStorage` (cleared when the tab closes, survives reloads).
  **Trade-off:** any XSS could read it. Mitigations: never in `localStorage`, never logged, Markdown output
  is sanitized and raw HTML is not rendered, links use `rel="noopener noreferrer nofollow"`, a strict
  Content-Security-Policy is recommended at the host (see below).
- Passwords are only held in form state during submission.
- A 401 on any protected request, or the token's expiry time, ends the session and clears cached data.
- Route guards are UX only. The backend enforces ownership and authorization on every call.
- File type and size checks in the browser are UX only; the backend validates again.
- Local chat sessions are stored in `localStorage` per user id and contain answers and source excerpts.
  Use Settings, Delete all local chats on shared computers.
- Errors shown to users come from the API's curated messages or generic fallbacks, never stack traces.

## Deployment recommendations

- Host `dist/` on any static host or CDN and route `/api/*` to the backend through the same origin
  (Nginx, Caddy, Cloudflare, Vercel or Netlify rewrites). That avoids CORS entirely.
- Add security headers at the host: `Content-Security-Policy` (`default-src 'self'; img-src 'self' data:`),
  `X-Content-Type-Options`, `Referrer-Policy`, and HTTPS only.
- Before going to production, replace the in-process background task with a durable job queue.

## Structure

```
frontend/
  scripts/process_pending.py     optional fallback for stuck documents
  src/
    app/            providers, router
    components/     ui/ (Button, Dialog, ...), layout/ (AppShell), common/
    features/       auth/, dashboard/, documents/, chat/, settings/
    lib/            api-client, auth (token), errors, config, utils
    styles/         globals.css (design tokens)
    test/           test setup and helpers
```
