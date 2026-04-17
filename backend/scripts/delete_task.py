"""
delete_task.py — one-time script to remove a specific task from the database.

Target:
  repo:  chaoss/chaoss-africa
  title: "Design website assets"

Usage (run from the backend/ directory so imports resolve):
  python scripts/delete_task.py

The script prints the full task record before deleting so you can
confirm it is the correct one. Press Enter to confirm, Ctrl-C to abort.
"""

import sys
import os

# Allow running from the backend/ directory directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from models.task import Task
from models.project import Project


TARGET_OWNER = "chaoss"
TARGET_REPO  = "chaoss-africa"
TARGET_TITLE = "Design website assets"


def main() -> None:
    session = SessionLocal()
    try:
        task = (
            session.query(Task)
            .join(Task.project)
            .filter(
                Project.github_owner == TARGET_OWNER,
                Project.github_repo  == TARGET_REPO,
                Task.title           == TARGET_TITLE,
            )
            .first()
        )

        if task is None:
            print(
                f"No task found matching:\n"
                f"  repo:  {TARGET_OWNER}/{TARGET_REPO}\n"
                f"  title: {TARGET_TITLE!r}\n"
                "Nothing was deleted."
            )
            return

        # Print full record for confirmation
        print("Found task — please confirm this is the correct record:")
        print(f"  id:              {task.id}")
        print(f"  title:           {task.title}")
        print(f"  repo:            {task.project.github_owner}/{task.project.github_repo}")
        print(f"  review_status:   {task.review_status}")
        print(f"  is_active:       {task.is_active}")
        print(f"  source:          {task.source}")
        print(f"  created_at:      {task.created_at}")
        print(f"  github_issue_url:{task.github_issue_url}")
        print()

        confirm = input("Type 'yes' to delete, anything else to abort: ").strip().lower()
        if confirm != "yes":
            print("Aborted — nothing was deleted.")
            return

        session.delete(task)
        session.commit()
        print(f"Deleted task {task.id} — '{task.title}'")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
