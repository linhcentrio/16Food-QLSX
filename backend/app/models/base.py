import uuid

from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy import MetaData


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class cho tất cả SQLAlchemy models."""

    metadata = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        return cls.__name__.lower()

    @staticmethod
    def generate_uuid() -> uuid.UUID:
        return uuid.uuid4()


def uuid_pk() -> Mapped[uuid.UUID]:
    """Helper function để tạo UUID primary key column."""
    return mapped_column(
        default=Base.generate_uuid,
        primary_key=True
    )


