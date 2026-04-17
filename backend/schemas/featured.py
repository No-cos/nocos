# schemas/featured.py
# Pydantic response schema for the /api/v1/featured endpoint.

from typing import List, Optional
from pydantic import BaseModel


class FeaturedProjectResponse(BaseModel):
    """
    A single project in the featured section.

    Returned inside the most_active or new_promising lists by GET /api/v1/featured.
    All fields match the featured_projects DB table (model/featured_project.py).
    """

    repo_full_name: str
    """owner/repo slug — e.g. "vercel/next.js" """

    name: str
    """Human-readable repository name"""

    description: str
    """Short repository description from GitHub (may be empty string)"""

    language: Optional[str]
    """Primary programming language, e.g. "TypeScript" (null if not set)"""

    stars: int
    """Total star count at snapshot time"""

    stars_gained_this_week: Optional[int]
    """Stars gained in the past 7 days — populated for new_promising only"""

    forks: int
    """Fork count at snapshot time"""

    open_issues_count: int
    """Open issue count at snapshot time"""

    homepage: Optional[str]
    """Project homepage URL (null if not set)"""

    license: Optional[str]
    """SPDX license identifier, e.g. "MIT" (null if repo has no license)"""

    topics: List[str]
    """GitHub topic tags, e.g. ["react", "typescript"]"""

    weekly_commits: int
    """Total commits across all branches for the past week (0 for new_promising)"""

    avatar_url: str
    """Owner / organisation avatar URL"""

    github_url: str
    """Full GitHub HTML URL, e.g. "https://github.com/owner/repo" """

    category: str
    """Which featured slot: "most_active" or "new_promising" """
