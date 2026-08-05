# bff-service

AI Dev Framework의 Gateway/BFF 레이어 (FastAPI). 프론트엔드 ↔ core-service(Spring Boot) 중계와
AI 에이전트 연동(비동기, LLM API 호출)을 담당한다. core-service처럼 트랜잭션 중심 비즈니스 로직을 짊어지진
않지만, 자체적으로 필요한 데이터(예: 에이전트 작업 이력)는 직접 DB에 읽고 쓴다.

## 구조

```
app
├── main.py          FastAPI 앱 진입점
├── models.py         SQLAlchemy 모델 (AgentTaskLog)
├── core/
│   ├── config.py    환경설정 (pydantic-settings)
│   ├── db.py        비동기 SQLAlchemy 엔진/세션
│   └── responses.py core-service와 동일한 표준 응답(ApiResponse) 포맷
├── api/v1/          버전별 라우터 (ping, agent-tasks)
└── agents/          기존 멀티 AI 에이전트 시스템 연동 지점 (다음 단계)
migrations/          Alembic 마이그레이션
```

core-service의 `ApiResponse`와 필드가 동일하다 (`success` / `data` / `error{code,message}`).
프론트엔드가 core-service를 직접 부르든 bff-service를 거치든 같은 방식으로 응답을 처리할 수 있게 하기 위함.

## DB

기본은 core-service와 같은 Postgres **인스턴스**지만, DB는 별도(`aidevframework_bff`)다.
Flyway(core-service)와 Alembic(bff-service)이 같은 스키마를 공유하면 어느 쪽 마이그레이션이 먼저
도냐에 따라 Flyway가 "낯선 테이블이 이미 있다"며 baseline 에러를 내는 실제 버그가 있었다 — DB를
분리해서 그 경합 자체를 없앴다. `agent_task_log` 테이블은 core-service의 User 테이블과 완전히 별개로
**bff-service가 직접 소유**하는 데이터 — BFF 레이어도 자체 DB 처리가 가능함을 보여주는 예시다.

```bash
# 회원가입/로그인 없이 바로 확인 가능한 예시 엔드포인트
curl -X POST http://localhost:8000/api/v1/agent-tasks \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"feature-developer","instruction":"알림 기능 추가"}'

curl http://localhost:8000/api/v1/agent-tasks
```

다른 DB로 바꾸려면 드라이버 패키지를 설치하고 `DATABASE_URL`만 바꾸면 된다
(예: SQLite `sqlite+aiosqlite:///./bff.db`, MSSQL `mssql+aioodbc://...`, Oracle `oracle+oracledb_async://...`).
지금은 Postgres 경로만 실제로 검증되어 있다 — core-service만큼 4개 DB를 전부 붙여보진 않았다
(BFF는 가벼운 레이어라 우선순위가 낮다고 판단).

### DB마다 쿼리 문법이 다른 문제

`models.py`의 `AgentTaskLog`처럼 SQLAlchemy ORM/Core로 쿼리를 짜는 한(`select()`, `Session.query`,
`op.create_table` 등), SQLAlchemy의 dialect(`postgresql`/`mssql`/`oracle`/`sqlite`)가 알아서 각 DB에
맞는 네이티브 SQL로 번역한다 — core-service의 Hibernate Dialect와 정확히 같은 역할이다. `migrations/`의
Alembic 마이그레이션도 원시 SQL이 아니라 `sa.Column`/`op.create_table` 같은 SQLAlchemy DSL로 썼기
때문에, core-service의 Flyway 마이그레이션(DB마다 손으로 따로 쓴 SQL)과 달리 **이 스키마는 이미
방언 독립적이다** — 새 DB를 추가해도 `migrations/versions/`를 따로 만들 필요가 없다(대신 SQLAlchemy의
방언별 컬럼 타입 매핑이 100% 완벽하진 않으니, 실제로 새 DB를 붙일 때는 생성된 스키마를 한 번 확인할 것).

**지켜야 할 규칙**: `session.execute(text("SELECT ..."))`처럼 원시 SQL 문자열을 직접 쓰지 말 것.
그 순간 그 쿼리는 특정 DB 문법에 종속된다.

### Windows에서 로컬로 직접 실행할 때 주의

Windows 네이티브 Python + Docker Desktop 조합에서 `asyncpg`가 연결 도중 끊기는 알려진 문제가 있다
(일반 TCP는 되는데 asyncpg의 프로토콜 핸드셰이크만 리셋됨). WSL2 안에서 실행하거나, 아래 Docker 섹션처럼
리눅스 컨테이너로 띄우면 문제없다.

## Docker

```bash
docker build -t bff-service:local .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://aidevframework:aidevframework@host.docker.internal:5432/aidevframework_bff" \
  bff-service:local
```

멀티스테이지 빌드, non-root(`appuser`)로 구동된다. 이미지 자체는 마이그레이션을 실행하지 않으므로
컨테이너 기동 전에 `alembic upgrade head`를 한 번 돌려야 한다 — 루트의 `docker-compose.yml`에는
`bff-service-migrate` 1회성 잡으로 이미 반영되어 있다. 전체 스택은 루트에서
`docker compose up -d --build` 한 번이면 된다.

## 로컬 실행

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash 기준
pip install -r requirements-dev.txt

cp .env.example .env

# DB 기동 (루트의 docker-compose)
docker compose up -d db

# 마이그레이션
alembic upgrade head

# 앱 실행
uvicorn app.main:app --reload --port 8000
```

확인:

```bash
curl -H "X-Tenant-Id: demo" http://localhost:8000/api/v1/ping
curl http://localhost:8000/health
```

테스트:

```bash
pytest
```

## 아직 안 된 것 (다음 단계)

- core-service 호출 클라이언트 (httpx 기반) 미구현 — 지금은 순수 BFF 골격만 있음
- 기존 멀티 AI 에이전트 시스템 연동 미구현 — `app/agents/`에 붙일 예정, 연동 방식은 기존 시스템 설명 받은 후 결정
- 인증: core-service와 동일 JWT를 검증하는 미들웨어 없음 (지금은 agent-tasks API가 인증 없이 열려 있음)
- Postgres 외 DB(MSSQL/Oracle/SQLite)는 문서만 있고 실제 검증은 안 됨
