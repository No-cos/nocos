# Contributing to Nocos

Thank you for your interest in contributing to Nocos! This guide will walk you through everything you need to get set up and make your first contribution.

If anything is unclear, open an issue and we'll improve this guide.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS, TypeScript |
| Backend | Python 3.11+, FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| Cache | Redis |
| AI | Anthropic SDK (Claude Sonnet) |
| Scheduler | APScheduler |

---

## Prerequisites

Before you start, make sure you have the following installed:

- **Node.js 18+** — [nodejs.org](https://nodejs.org)
- **Python 3.11+** — [python.org](https://www.python.org)
- **PostgreSQL** — [postgresql.org](https://www.postgresql.org)
- **Redis** — [redis.io](https://redis.io)

---

## Table of Contents

1. [Fork and clone the repo](#1-fork-and-clone-the-repo)
2. [Install dependencies](#2-install-dependencies)
3. [Set up your .env file](#3-set-up-your-env-file)
4. [Run the project locally](#4-run-the-project-locally)
5. [Run tests](#5-run-tests)
6. [Commit message convention](#6-commit-message-convention)
7. [Open a pull request](#7-open-a-pull-request)
8. [Need help?](#8-need-help)

---

## 1. Fork and clone the repo

1. Click **Fork** at the top right of [github.com/No-cos/nocos](https://github.com/No-cos/nocos)
2. Clone your fork locally:

```bash
git clone https://github.com/<your-username>/nocos.git
cd nocos
```

3. Add the upstream remote so you can pull in future changes:

```bash
git remote add upstream https://github.com/No-cos/nocos.git
```

---

## 2. Install dependencies

### Backend (Python 3.11+)

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend (Node.js 18+)

```bash
cd frontend
npm install
```

---

## 3. Set up your .env file

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and fill in the required variables. See the comments in `.env.example` for instructions on where to get each value.

**Required for most development work:**
- `GITHUB_TOKEN` — [Create a Personal Access Token](https://github.com/settings/tokens) with `public_repo` scope
- `ANTHROPIC_API_KEY` — [Get your key](https://console.anthropic.com)
- `DATABASE_URL` — PostgreSQL connection string

---

## 4. Run the project locally

### Backend

```bash
cd backend
source venv/bin/activate
alembic upgrade head        # Apply database migrations
uvicorn main:app --reload   # API at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm run dev   # App at http://localhost:3000
```

### Verify everything is working

- Frontend: [http://localhost:3000](http://localhost:3000)
- API health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) → `{"status": "ok"}`
- API docs (development only): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 5. Run tests

### Backend

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm run test
```

Tests must pass before opening a pull request.

---

## 6. Commit message convention

Nocos uses [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>: <short description in present tense>
```

| Type | When to use |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `chore` | Maintenance, config, dependency updates |
| `docs` | Documentation only |
| `test` | Tests only |
| `refactor` | Code change with no feature or bug fix |
| `style` | Formatting only (no logic change) |

**Examples:**

```bash
git commit -m "feat: add tag filter bar to discovery grid"
git commit -m "fix: prevent duplicate issues on GitHub sync"
git commit -m "docs: add setup instructions to README"
```

---

## 7. Open a pull request

1. Create a branch for your work:

```bash
git checkout -b feat/your-feature-name
```

2. Make your changes, commit them, and push:

```bash
git push origin feat/your-feature-name
```

3. Open a pull request against the `main` branch of `No-cos/nocos`
4. Fill in the PR template — describe what you changed and why
5. A maintainer will review your PR and provide feedback

---

## 8. Need help?

- Open an issue at [github.com/No-cos/nocos/issues](https://github.com/No-cos/nocos/issues)
- Tag your issue with `good-first-issue` if you think it's beginner-friendly

We're happy to help — no question is too small.
