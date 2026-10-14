from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models.

    Defined now so future domain models share a single base. At this stage no
    table exists; schema is managed exclusively by Alembic.
    """