from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from app.domain.base import Base
from app.domain.models import (
    AuditEvent,
    Device,
    DeviceBootstrapRecord,
    DeviceCredential,
    Entity,
    EntityState,
    ProvisioningSession,
    Room,
    Site,
    SystemSetting,
    User,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        from app.core.config import get_settings

        settings = get_settings()
        ensure_sqlite_parent_dir(settings.database_url)
        connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        _engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
    return _engine


def ensure_sqlite_parent_dir(database_url: str) -> None:
    if database_url.startswith("sqlite:///./"):
        db_path = Path(database_url.removeprefix("sqlite:///./"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    elif database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        if db_path.parent:
            db_path.parent.mkdir(parents=True, exist_ok=True)


def build_alembic_config(database_url: str) -> AlembicConfig:
    project_root = Path(__file__).resolve().parents[2]
    config = AlembicConfig(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def init_db() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    ensure_sqlite_parent_dir(settings.database_url)
    command.upgrade(build_alembic_config(settings.database_url), "head")


def close_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
