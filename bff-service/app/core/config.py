from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "bff-service"
    core_service_base_url: str = "http://localhost:8080"
    tenant_header: str = "X-Tenant-Id"
    # 콤마로 구분된 origin 목록. 프론트엔드(frontend/) 개발 서버가 브라우저에서 직접 호출할 수 있게 한다.
    cors_origins: str = "http://localhost:3000"
    # 같은 Postgres 인스턴스지만 core-service(Flyway)와는 다른 DB를 쓴다 — 같은 스키마를 공유하면
    # Flyway와 Alembic 마이그레이션 순서에 따라 Flyway가 "낯선 테이블이 이미 있다"며 에러를 낸다.
    # MSSQL/Oracle/SQLite로 바꾸려면 드라이버 패키지를 설치하고 DATABASE_URL만 바꾸면 된다
    # (예: sqlite+aiosqlite:///./bff.db, mssql+aioodbc://..., oracle+oracledb_async://...).
    database_url: str = "postgresql+asyncpg://aidevframework:aidevframework@localhost:5432/aidevframework_bff"
    # 로컬 개발용 Postgres는 SSL을 안 쓴다. 운영 DB에 SSL이 필요하면 true로 바꾼다.
    database_ssl: bool = False


settings = Settings()
