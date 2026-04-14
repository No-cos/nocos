# models/base.py
# Shared SQLAlchemy declarative base.
# All models import Base from here so Alembic can discover them all
# from a single metadata object when generating migrations.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared base class for all SQLAlchemy models.

    Importing Base here and using it across all model files ensures Alembic
    sees every table in one metadata object. Never create a second Base —
    models on a different Base are invisible to autogenerate migrations.
    """
    pass
