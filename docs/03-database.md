# 3. 데이터베이스

## 3.1 두 개의 DB, 두 개의 마이그레이션 도구

core-service와 bff-service는 **같은 Postgres 인스턴스 안에서도 서로 다른 데이터베이스**를 쓴다
(`aidevframework` vs `aidevframework_bff`). 일부러 분리했다 — 같은 스키마를 Flyway(core-service)와
Alembic(bff-service)이 같이 건드리면, 어느 쪽이 먼저 도냐에 따라 Flyway가 "낯선 테이블이 이미
있다"며 baseline 에러를 내는 실제 버그가 있었다. 새 DB를 추가할 때도 이 분리 원칙은 그대로 유지할 것.

| | core-service | bff-service |
|---|---|---|
| 도구 | Flyway | Alembic |
| ORM | Hibernate/JPA | SQLAlchemy 2.0 (async) |
| 마이그레이션 위치 | `core-service/src/main/resources/db/migration/{vendor}/` | `bff-service/migrations/versions/` |
| DB (docker-compose 기본) | `aidevframework` | `aidevframework_bff` |

## 3.2 DB 벤더마다 쿼리 문법이 다른 문제 — 어떻게 흡수하는가

**핵심 원칙: ORM/쿼리 빌더 DSL만 쓰고, 원시 SQL 문자열을 직접 쓰지 않는다.** 이 원칙만 지키면
아래 두 계층이 알아서 방언을 흡수해준다.

- **core-service**: Hibernate의 `Dialect`가 JPQL/Criteria/`@Query`를 실행 시점에 연결된 DB에 맞는
  네이티브 SQL로 번역한다. `application-{profile}.yml`의 `spring.jpa.database-platform`이 그
  dialect를 지정한다 (Postgres/MSSQL/Oracle은 Hibernate 내장 dialect, SQLite는
  `hibernate-community-dialect`의 `SQLiteDialect`).
- **bff-service**: SQLAlchemy의 dialect(`postgresql`/`mssql`/`oracle`/`sqlite`)가 같은 역할을 한다.
  `models.py`처럼 `Mapped[...]`/`mapped_column`으로 모델을 짜고 `select()`로 쿼리하는 한 자동으로
  방언이 흡수된다.

**깨지는 경우**: `@Query(nativeQuery = true, value = "SELECT ...")`(JPA)나
`session.execute(text("SELECT ..."))`(SQLAlchemy)처럼 원시 SQL 문자열을 쓰는 순간, 그 코드는 특정
DB 문법에 종속된다. 정말 필요할 때만(복잡한 집계 등) 쓰고, 그 경우 지원하는 DB마다 분기하거나 해당
DB만 지원한다고 문서에 명시할 것.

**Flyway 마이그레이션은 예외**: `V1__init_auth.sql`처럼 순수 SQL로 짜기 때문에 벤더 폴더
(`postgresql/`, `sqlserver/`, `oracle/`)마다 손으로 따로 관리해야 한다 (아래 3.4 참고). 반면
Alembic 마이그레이션(`op.create_table` 등)은 SQLAlchemy DSL이라 이미 방언 독립적이다 — bff-service는
새 DB를 추가해도 마이그레이션 폴더를 벤더별로 나눌 필요가 없다.

## 3.3 지원 DB와 검증 상태

| DB | core-service | bff-service | 상태 |
|---|---|---|---|
| Postgres | ✅ | ✅ | 기본값, 이 프레임워크 자체가 이걸로 계속 검증됨 |
| MSSQL | ✅ (프로파일 있음) | 설정만, 미검증 | 설정/마이그레이션 폴더는 있지만 실제 기동 테스트는 드묾 (이미지가 커서) |
| Oracle | ✅ (프로파일 있음) | 설정만, 미검증 | 위와 동일 |
| SQLite | ✅ (프로파일 있음, 서버리스) | 미지원 | core-service 컨테이너에서 실제 부팅 검증됨. bff-service는 `aiosqlite` 드라이버 설치 안 되어 있음 |

## 3.4 core-service: DB 프로파일 전환하기

**로컬에서 바로 전환** (Spring 프로파일):

```bash
# Postgres (기본, application.yml)
./gradlew bootRun

# MSSQL
docker compose --profile mssql up -d db-mssql-init
SPRING_PROFILES_ACTIVE=mssql \
  DB_URL="jdbc:sqlserver://localhost:1433;databaseName=aidevframework;encrypt=false" \
  DB_USERNAME=sa DB_PASSWORD='YourStrong!Passw0rd' \
  ./gradlew bootRun

# Oracle
docker compose --profile oracle up -d db-oracle
SPRING_PROFILES_ACTIVE=oracle \
  DB_URL="jdbc:oracle:thin:@localhost:1521/FREEPDB1" \
  DB_USERNAME=aidevframework DB_PASSWORD=aidevframework \
  ./gradlew bootRun

# SQLite (서버 필요 없음, 파일 하나)
SPRING_PROFILES_ACTIVE=sqlite ./gradlew bootRun
```

Docker 컨테이너로 SQLite 프로파일을 띄울 때는 `WORKDIR`이 non-root 사용자 소유인지 반드시 확인할 것
— `core-service/Dockerfile`에 이미 `chown appuser:appuser /app`이 있는데, 이게 없으면
`SQLITE_CANTOPEN` 에러로 즉시 죽는다 (실제로 이 프레임워크 자체에서 한 번 겪은 버그).

**Helm/docker-compose에서 전환**: `helm/ai-dev-framework/values.yaml`의 주석대로,
`postgresql.enabled: false`로 끄고 `coreService.extraEnv`에 `SPRING_PROFILES_ACTIVE`,
`DB_URL`, `DB_USERNAME`, `DB_PASSWORD`를 직접 넣는다. docker-compose는 `core-service` 서비스의
`environment`를 같은 방식으로 바꾸면 된다.

## 3.5 새 마이그레이션 추가하기 (core-service, Flyway)

1. `core-service/src/main/resources/db/migration/{vendor}/` 아래에 각 벤더별로 **같은 내용을 각자
   문법으로** 추가한다. 파일명 규칙은 `V{버전}__{설명}.sql` (예: `V2__add_project_table.sql`).
   버전 번호는 벤더 폴더마다 독립적으로 관리되지만(Flyway가 폴더별로 따로 추적), 실수를 줄이려면
   세 폴더에서 번호를 맞춰가는 걸 권장한다.
2. Postgres만 쓰고 있다면 일단 `postgresql/`에만 추가하고 시작해도 된다 — 나중에 MSSQL/Oracle을
   실제로 붙일 때 그동안 밀린 마이그레이션들을 한 번에 이식하면 된다. 단, SQLite 프로파일은 Flyway를
   아예 안 쓰므로(`ddl-auto: update`) 마이그레이션 파일이 필요 없다 — 엔티티 클래스만 맞으면 자동 반영.
3. 앱을 재시작하면 Flyway가 부팅 시점에 자동으로 실행한다. 수동 실행은 필요 없다.

## 3.6 새 마이그레이션 추가하기 (bff-service, Alembic)

```bash
cd bff-service
# 로컬에 venv+의존성 있으면 바로, 없으면 Docker로:
#   docker run --rm -v $(pwd):/app -w /app python:3.12-slim bash -c \
#     "pip install -r requirements.txt -q && alembic revision --autogenerate -m 'add project table'"
alembic revision --autogenerate -m "add project table"
```

`models.py`에 SQLAlchemy 모델을 먼저 추가한 뒤 위 명령을 돌리면 `migrations/versions/`에
`{번호}_add_project_table.py`가 자동 생성된다(`--autogenerate`가 모델과 현재 DB 스키마 차이를
비교해서 만들어줌) — 생성된 파일은 항상 한 번 눈으로 확인할 것(자동 생성이 완벽하지 않을 때가 있음).
적용은:

```bash
alembic upgrade head
```

docker-compose/Helm에서는 `bff-service-migrate` 잡이 컨테이너 기동 시 자동으로 이 명령을 실행한다.

## 3.7 SQL 문법 차이를 흡수하기 어려운 경우

전문 검색, 재귀 쿼리, DB 전용 함수(예: Postgres의 `jsonb` 연산자, Oracle의 `CONNECT BY`)처럼
ORM으로 표현 안 되는 기능이 필요하면:

1. 정말 필요한지 먼저 재검토 — 애플리케이션 레벨(코드)로 옮길 수 있으면 이식성이 더 좋다.
2. 꼭 필요하면 그 부분만 원시 SQL로 쓰되, 지원 DB를 명시적으로 제한한다는 걸 코드 주석과
   `core-service/README.md`/`bff-service/README.md`에 남긴다.
3. 벤더별로 분기해야 하면 core-service는 `@Query`를 프로파일별 빈으로 분리하거나, bff-service는
   `settings.database_url`을 보고 쿼리를 분기하는 식으로 처리한다.
