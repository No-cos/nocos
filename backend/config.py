# config.py
# Central configuration module for the Nocos backend.
# All environment variables are accessed here — never use os.environ directly
# in other modules. This makes it easy to see every config value in one place
# and means we only need to update one file if a variable name changes.

import os
from dotenv import load_dotenv

# Load .env file if it exists (development). In production, variables come
# from the host environment directly and load_dotenv is a no-op.
load_dotenv()


class Config:
    """
    Application configuration loaded from environment variables.

    Required variables (GITHUB_TOKEN, ANTHROPIC_API_KEY, DATABASE_URL) will
    raise an EnvironmentError at startup if missing — this is intentional.
    Failing fast at startup is better than failing silently at runtime.
    """

    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    EMAIL_SERVICE_API_KEY: str = os.getenv("EMAIL_SERVICE_API_KEY", "")
    # Resend requires the sending domain to be verified before emails will deliver.
    # onboarding@resend.dev is Resend's pre-verified address — use it as a safe
    # fallback so emails don't silently fail when EMAIL_FROM is unset or the
    # domain (nocos.io / nocos.cc) has not yet been verified in the Resend dashboard.
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "onboarding@resend.dev")

    # GitLab personal access token — optional.
    # Without it, GitLab scraping runs unauthenticated (~60 req/min).
    GITLAB_TOKEN: str = os.getenv("GITLAB_TOKEN", "")

    # Frontend base URL — used in confirmation email links
    NEXT_PUBLIC_API_URL: str = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3000")

    # Public frontend URL — used in admin emails to link back to approved tasks.
    # Set to https://nocos.cc in production; defaults to localhost for local dev.
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://nocos.cc")

    # Admin secret token for content moderation endpoints.
    # If unset, all admin endpoints return 503. Generate with: openssl rand -hex 32
    ADMIN_SECRET_TOKEN: str = os.getenv("ADMIN_SECRET_TOKEN", "")

    APP_ENV: str = os.getenv("APP_ENV", "development")

    @property
    def is_production(self) -> bool:
        """Returns True when running in production mode."""
        return self.APP_ENV == "production"

    def validate(self) -> None:
        """
        Raise an EnvironmentError at startup if any required variable is missing.

        This prevents the app from starting in an invalid state where API calls
        would fail at runtime rather than immediately on boot.
        """
        required = ["GITHUB_TOKEN", "ANTHROPIC_API_KEY", "DATABASE_URL"]
        missing = [key for key in required if not getattr(self, key)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {missing}. "
                f"Copy .env.example to .env and fill in the values."
            )


# Singleton — import config from this module everywhere
config = Config()
