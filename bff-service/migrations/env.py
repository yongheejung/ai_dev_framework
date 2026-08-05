import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.db import Base
from app.models import AgentTaskLog  # noqa: F401  autogenerate가 인식하려면 모델을 import해야 한다

# Windows 기본 ProactorEventLoop + asyncpg 조합에서 연결이 중간에 끊기는 알려진 문제가 있어
# SelectorEventLoop로 바꾼다. (리눅스/컨테이너 배포 환경에는 영향 없음)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # db.py 참고: asyncpg의 기본 클라이언트 인증서 탐색이 비-ASCII 홈 경로에서 깨지는 것을 피하려고
    # ssl을 명시적으로 넘긴다.
    connect_args = {"ssl": settings.database_ssl} if settings.database_url.startswith("postgresql+asyncpg") else {}
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
