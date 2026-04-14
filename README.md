# Nocos

**Discover and Contribute to Your Favourite Open Source Project.**

Nocos is a two-sided discovery platform for open source. Non-technical contributors — designers, writers, translators, researchers, and community managers — find curated, non-code issues they can work on. Maintainers get visibility and non-technical help they rarely find elsewhere. AI keeps content fresh and readable.

**Live at:** [nocos.cc](https://nocos.cc)

---

## The Problem

Open source has a non-technical contribution problem. Designers, writers, translators, researchers, and community managers want to contribute but have nowhere to start. GitHub issue trackers are built for engineers. Non-technical contributors bounce because there is no structured path in.

## The Solution

Nocos curates non-code issues from GitHub, generates readable descriptions where maintainers have left them empty, and presents them in a clean discovery interface built specifically for non-technical contributors.

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

## Local Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL
- Redis

### 1. Clone the repo

```bash
git clone https://github.com/No-cos/nocos.git
cd nocos
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and fill in your values (see comments in .env.example)
```

### 3. Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head       # Run database migrations
uvicorn main:app --reload  # Starts on http://localhost:8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev  # Starts on http://localhost:3000
```

### 5. Verify

- Frontend: [http://localhost:3000](http://localhost:3000)
- API health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide.

---

## License

MIT License — see [LICENSE](LICENSE).
