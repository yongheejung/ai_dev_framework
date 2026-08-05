from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# asyncpg가 SSL 미지정 시 기본 클라이언트 인증서 경로(홈 디렉터리 하위)를 탐색하는데,
# 사용자 홈 경로에 비-ASCII 문자가 섞여 있으면 이 탐색 과정에서 인코딩 에러가 난다.
# ssl 여부를 명시적으로 넘겨서 그 탐색 자체를 건너뛴다.
_connect_args = {"ssl": settings.database_ssl} if settings.database_url.startswith("postgresql+asyncpg") else {}

engine = create_async_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
