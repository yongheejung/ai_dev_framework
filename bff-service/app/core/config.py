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
    # universal_ai_agent_orchestrator 연동 (docs/06-ai-agent-integration.md Phase B).
    # X-API-Key는 서버 사이드(이 서비스)에서만 쓰고 브라우저에는 절대 넘기지 않는다.
    orchestrator_base_url: str = "http://localhost:8000"
    orchestrator_api_key: str = ""
    orchestrator_workspace_id: str = "default"
    orchestrator_job_template_id: str = "code-build-job"
    # git 저장 커넥터 (docs/06-ai-agent-integration.md Phase C) — 승인된 Job 결과를 실제 GitHub
    # 저장소에 반영하는 유일한 "쓰기" 경로다. 기본 비활성 — 명시적으로 켜야 동작한다(오케스트레이터의
    # L2/L3 side-effect가 기본 비활성인 것과 같은 안전장치). GITHUB_TOKEN은 절대 로그/에러 메시지에
    # 노출하지 않는다 — 로컬 git push 대신 GitHub REST(Git Data API)만 쓰는 이유이기도 하다.
    git_connector_enabled: bool = False
    github_token: str = ""
    github_owner_repo: str = "yongheejung/ai_dev_framework"
    git_connector_base_branch: str = "main"
    # 처음엔 좁은 범위만 — 이 접두사로 시작하는 경로만 반영한다(Phase C 권장: bff-service 폴더만).
    git_connector_path_prefix: str = "bff-service/"


settings = Settings()
