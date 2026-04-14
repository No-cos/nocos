# Changelog

All notable changes to Nocos will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Full landing page UI: Navbar, Hero, Category Marquee, Filter Bar, Search Bar, Issue Grid, Subscribe Section, Footer
- Monorepo scaffold: `/frontend` (Next.js 14 + Tailwind CSS) and `/backend` (FastAPI)
- CSS design token system with full light and dark mode variables
- FastAPI application entry point with versioned routers and CORS config
- Central config module with environment variable validation
- Typed API client and utility helpers for the frontend
- Custom React hooks: `useIssues`, `useProject`, `useDarkMode`
- PostgreSQL schema with `Project`, `Task`, and `Subscriber` models
- Alembic migration setup
- GitHub API client with rate limit handling and Redis cache fallback
- Anthropic client (Claude Sonnet) with description generation prompt template
- `GET /api/v1/health` endpoint
- Open source repository files: `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`, `.env.example`
- GitHub issue and PR templates

---

*Full release notes will be added here as versions are tagged.*
