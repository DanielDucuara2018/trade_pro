import logging
import os
from typing import Optional

from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from alembic.command import upgrade
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from trade_pro.config import Config
from trade_pro.model.base import mapper_registry

logger = logging.getLogger(__name__)

ALEMBIC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic"
)


def get_engine(suffix: Optional[str] = None) -> Engine:
    sqlalchemy_url = f"postgresql://{Config.database.user}:{Config.database.password}@{Config.database.host}:{Config.database.port}/{Config.database.database}"
    if suffix:
        sqlalchemy_url += suffix
    return create_engine(sqlalchemy_url)


def check_db_connection() -> None:
    conn = get_engine().connect()
    conn.close()


def init() -> sessionmaker:
    logger.info("Initialising postgres connection")
    engine = get_engine()
    return sessionmaker(bind=engine)


def open_session(
    session_factory: sessionmaker,
) -> Session:
    return session_factory()


def get_alembic_config(conn):
    config = AlembicConfig()
    # pylint: disable=unsupported-assignment-operation
    config.attributes["connection"] = conn
    config.set_section_option("alembic", "script_location", ALEMBIC_PATH)
    script = ScriptDirectory.from_config(config)
    context = MigrationContext.configure(conn)
    script_head = script.get_current_head()
    current_head = context.get_current_revision()

    return config, script, context, script_head, current_head


def get_missing_revisions(conn):
    _, script, _, script_head, current_head = get_alembic_config(conn)
    return [s for s in script.iterate_revisions(script_head, current_head)]


def create(conn):
    # Create tables
    mapper_registry.metadata.create_all(bind=conn)
    # Mark the db patchs as applied
    _, script, context, script_head, _ = get_alembic_config(conn)
    context.stamp(script, script_head)


def update(conn, table_name, dry_run=False):
    """Apply missing revisions to the database."""
    config, _, _, script_head, current_head = get_alembic_config(conn)

    exists = True
    try:
        with conn.begin_nested():
            conn.execute(f"""SELECT 1 FROM {table_name} LIMIT 1""")
    except ProgrammingError:
        exists = False

    if not dry_run:
        if not exists:
            create(conn)

        if current_head != script_head:
            upgrade(config, "head")
    else:
        return get_missing_revisions(conn)


def initialize(update_schema: bool = False) -> None:
    logger.info("Checking database connection")
    check_db_connection()
    logger.info("Checking alembic migrations")
    engine = get_engine(suffix="?target_session_attrs=read-write")
    with engine.connect() as conn:
        applied_revisions = update(
            conn, Config.database.ref_table, dry_run=not update_schema
        )

    if applied_revisions and update_schema:
        raise RuntimeError("Database is not up-to-date")


session = open_session(init())
