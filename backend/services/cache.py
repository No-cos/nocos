# services/cache.py
# Application-level Redis cache for API response caching.
# Distinct from the GitHub client's internal cache (which caches raw API
# responses). This module caches serialised API responses so the database
# is not queried on every request for hot data.
#
# Cache key patterns (from SKILLS.md Section 9):
#   project:{owner}:{repo}   — 1 hour  (project info)
#   issues:{label}:{page}    — 30 min  (issue lists by label)
#   issue:{github_id}        — 30 min  (single issue detail)
#
# All methods fail silently — a Redis outage degrades to uncached DB queries,
# not an error response to the user.

import json
import logging
from typing import Any, Optional

import redis

from config import config

logger = logging.getLogger(__name__)

# TTL constants in seconds — matches SKILLS.md Section 9
TTL_PROJECT = 3600       # 1 hour
TTL_ISSUE_LIST = 1800    # 30 minutes
TTL_ISSUE_DETAIL = 1800  # 30 minutes
TTL_FEATURED = 604800    # 7 days — featured projects refreshed weekly


class AppCache:
    """
    Application-level Redis cache for serialised API responses.

    All get/set operations fail silently so a Redis outage degrades
    gracefully to uncached database queries.

    Usage:
        cache = AppCache()
        data = cache.get("issue:12345")
        if data is None:
            data = fetch_from_db(...)
            cache.set("issue:12345", data, TTL_ISSUE_DETAIL)
    """

    def __init__(self) -> None:
        self._redis = self._connect()

    def _connect(self) -> Optional[redis.Redis]:
        """
        Connect to Redis. Returns None if Redis is unavailable.

        Redis is optional — the app runs without it, just without caching.
        This is the expected state in local development without Redis running.
        """
        try:
            r = redis.from_url(config.REDIS_URL, decode_responses=True)
            r.ping()
            logger.info("App cache connected to Redis")
            return r
        except Exception:
            logger.warning(
                "App cache could not connect to Redis — running without cache"
            )
            return None

    def get(self, key: str) -> Optional[Any]:
        """
        Return a cached value, or None if the key is missing or Redis is down.

        Args:
            key: Redis key string

        Returns:
            Deserialised Python object, or None
        """
        if not self._redis:
            return None
        try:
            value = self._redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning("Cache get failed", extra={"key": key, "error": str(e)})
            return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store a value in Redis with the given TTL (seconds).

        Args:
            key:   Redis key string
            value: Python object (must be JSON-serialisable)
            ttl:   Time-to-live in seconds
        """
        if not self._redis:
            return
        try:
            self._redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning("Cache set failed", extra={"key": key, "error": str(e)})

    def delete(self, key: str) -> None:
        """
        Remove a key from the cache.

        Used when a task or project is updated so stale data is not served.

        Args:
            key: Redis key to remove
        """
        if not self._redis:
            return
        try:
            self._redis.delete(key)
        except Exception as e:
            logger.warning("Cache delete failed", extra={"key": key, "error": str(e)})

    def invalidate_issue(self, github_issue_id: int) -> None:
        """
        Remove the cached response for a single issue detail.

        Called by the sync job when an issue's description is regenerated
        so the next request gets fresh data from the database.

        Args:
            github_issue_id: The GitHub issue ID used in the cache key
        """
        self.delete(f"issue:{github_issue_id}")

    def invalidate_project(self, owner: str, repo: str) -> None:
        """
        Remove the cached project info for a repository.

        Called when the sync job updates a project's activity status so
        the next request picks up the new values.

        Args:
            owner: GitHub repository owner
            repo:  GitHub repository name
        """
        self.delete(f"project:{owner}:{repo}")


# Module-level singleton — import app_cache from this module everywhere
app_cache = AppCache()
