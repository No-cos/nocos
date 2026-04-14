# Nocos — Claude Instructions

This file is read by Claude at the start of every session in this repository.
All rules below are mandatory and override default behaviour.

---

## 1. Secrets & Environment Variables

- **Never** hardcode API keys, tokens, passwords, or connection strings anywhere in the codebase.
- All secrets must live in environment variables only. Reference them via `process.env.VARIABLE` (frontend) or `os.getenv("VARIABLE")` (backend).
- Never log, print, or return secret values — not in console.log, not in error messages, not in API responses.
- If you spot a hardcoded secret anywhere in the codebase, flag it immediately and replace it with an env var reference.
- The following variables are sensitive and must never appear as literal values in any file:
  - `GITHUB_TOKEN`
  - `ANTHROPIC_API_KEY`
  - `DATABASE_URL`
  - `REDIS_URL`
  - `EMAIL_SERVICE_API_KEY`

---

## 2. What Never Gets Committed

The `.gitignore` is authoritative. Never commit:
- `.env` files of any kind
- `venv/`, `node_modules/`, `.next/`
- Any file containing a real token, key, or password
- Database dump files or migration snapshots containing real data

If asked to commit something that contains secrets, refuse and explain why.

---

## 3. API Response Safety

- The backend must never return raw database error messages to the client — catch and return a generic structured error.
- User passwords are never stored in plaintext — bcrypt only.
- Email addresses and other PII must never appear in logs.
- The `/api/v1/health` endpoint must not expose internal system details (DB version, server info, etc.) — only a status string.

---

## 4. Frontend Security

- `NEXT_PUBLIC_` variables are exposed to the browser. Only non-sensitive config (e.g. API base URL) should use this prefix.
- Never put `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `DATABASE_URL`, or `EMAIL_SERVICE_API_KEY` in a `NEXT_PUBLIC_` variable.
- All API calls go through the backend — never call the GitHub API or Anthropic API directly from the frontend.

---

## 5. Input Validation

- All user-supplied input (search queries, subscriber emails, form fields) must be validated and sanitised before use.
- The backend uses Pydantic schemas for all request bodies — never bypass schema validation.
- SQL queries must always go through SQLAlchemy ORM methods — never use raw string interpolation in queries.

---

## 6. CORS

- In production (`APP_ENV=production`), the backend only accepts requests from `https://nocos.cc` and `https://www.nocos.cc`.
- Never set `allow_origins=["*"]` in production — this is already gated behind the `is_production` flag in `main.py`. Do not change that logic.

---

## 7. Dependency Safety

- Do not add new dependencies without checking they are actively maintained and have no known critical CVEs.
- Pin versions in `requirements.txt` and `package.json` — no floating `latest` or `*` versions.

---

## 8. Code Review Checklist (before every commit)

Before committing any code, mentally check:
- [ ] No secrets or tokens in the diff
- [ ] No `console.log` or `print()` statements leaking sensitive data
- [ ] Input validated on the backend
- [ ] Error messages are generic (no stack traces to the client)
- [ ] New env vars are added to `backend/.env.example` with empty values and a comment

---

## 9. Project-Specific Context

- **Frontend**: Next.js 14 App Router — lives in `/frontend`
- **Backend**: FastAPI + SQLAlchemy + Alembic — lives in `/backend`
- **AI**: Uses `claude-sonnet-4-5` via the Anthropic SDK for issue description generation
- **Cache**: Redis for GitHub API response caching
- **Scheduler**: APScheduler runs a 6-hour freshness sync job
- **Database**: PostgreSQL in production (Railway), SQLite acceptable for local dev only
- **Domain**: nocos.cc (Vercel for frontend, Railway for backend)
- **GitHub org**: No-cos/nocos — only `iamkingsleey` should be listed as contributor

---

These rules exist to protect the product, its users, and the infrastructure.
When in doubt, be more conservative — security first.
