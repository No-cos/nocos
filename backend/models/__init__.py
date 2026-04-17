# models/__init__.py
# Exports all models so they can be imported cleanly from other modules.
# Also ensures all model classes are registered on Base.metadata before
# Alembic runs — import order here matters for foreign key resolution.

from models.base import Base
from models.project import Project
from models.task import Task
from models.subscriber import Subscriber
from models.program import Program

__all__ = ["Base", "Project", "Task", "Subscriber", "Program"]
