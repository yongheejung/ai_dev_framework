# core-service

AI Dev Framework의 Core Business Framework (Spring Boot 4 / Java 21).
트랜잭션 처리, 멀티테넌시, 표준 보안(JWT+RBAC), 공통 응답/예외 처리를 담당하는 엔진 계층.

## 패키지 구조

```
com.aidevframework.core
├── CoreServiceApplication.java
├── common/     표준 응답(ApiResponse), 에러 코드, 공통 예외 처리
├── config/     SecurityConfig (JWT 인증 + RBAC 인가 규칙)
├── tenant/     멀티테넌시(스키마 분리) 컨텍스트 및 필터
├── auth/       자체 회원가입/로그인/JWT 발급, User 엔티티
└── api/        예시 컨트롤러 (ping, me, admin)
```

이 패키지들은 AI 에이전트(기능 개발)가 새 기능을 추가할 때 반드시 준수해야 하는
"코딩 표준"의 기준점이다. 새 도메인 패키지는 `com.aidevframework.core.<domain>` 형태로 추가하고,
응답은 항상 `ApiResponse`, 실패는 항상 `BusinessException`을 통해 표현한다.

## 인증 / RBAC

자체 발급 JWT(RS256) 방식이다. 외부 OIDC Provider(Keycloak/Auth0/Cognito 등)를 쓰기로 결정하면
`JwtKeyConfig`의 `JwtDecoder`만 해당 Provider의 `jwk-set-uri`를 보게 바꾸면 되고, `SecurityConfig`의
인가 규칙(`hasRole` 등)은 그대로 재사용 가능하다.

```bash
# 회원가입 (기본 role: USER)
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" -d '{"username":"alice","password":"alice1234"}'

# 로그인 -> JWT 발급
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" -d '{"username":"alice","password":"alice1234"}'

# 발급받은 토큰으로 호출 (X-Tenant-Id는 auth 경로 제외 모든 API에 필수)
curl http://localhost:8080/api/v1/me \
  -H "Authorization: Bearer <accessToken>" -H "X-Tenant-Id: demo"

# RBAC 데모: ADMIN 역할만 허용
curl http://localhost:8080/api/v1/admin/ping \
  -H "Authorization: Bearer <accessToken>" -H "X-Tenant-Id: demo"
```

개발 편의용으로 `admin` / `admin1234` (ADMIN+USER 역할) 계정이 기동 시 자동 시딩된다
(`DevAdminSeeder`, `prod` 프로파일에서는 비활성화). **운영 배포 전에 반드시 비밀번호를 바꾸거나 시더를 제거할 것.**

**401/403도 표준 `ApiResponse` 포맷을 지킨다.** Spring Security가 인증/인가 자체를 거부하는 경우
(토큰 없음, 역할 부족)는 컨트롤러에 도달하기 전에 발생해서 `GlobalExceptionHandler`(컨트롤러 안에서
던진 `BusinessException`을 잡는 것)를 거치지 않는다 — 기본값은 본문 없는 401/403이다. 프론트엔드
연동 중 이걸로 클라이언트의 JSON 파싱이 깨지는 실제 문제를 겪어서, `SecurityConfig`에 커스텀
`AuthenticationEntryPoint`/`AccessDeniedHandler`를 추가해 이 경로도 `{success:false, error:{code,message}}`
포맷으로 응답하게 만들었다. 새로운 보안 예외 처리를 추가할 때도 이 포맷을 벗어나지 않도록 할 것.

## 로컬 실행

```bash
# 1. 로컬 DB 기동 (루트의 docker-compose 사용)
docker compose up -d db

# 2. 애플리케이션 실행
./gradlew bootRun
```

확인:

```bash
curl -H "X-Tenant-Id: demo" http://localhost:8080/api/v1/ping
curl http://localhost:8080/actuator/health
```

## DB 다중 지원 (Postgres / MSSQL / Oracle / SQLite)

기본은 Postgres. 프로파일만 바꾸면 다른 DB로 그대로 뜬다 — 엔티티/Repository/컨트롤러 코드는 전혀 안 바뀐다.

| DB       | 프로파일               | 로컬 기동                                             |
|----------|------------------------|--------------------------------------------------------|
| Postgres | (기본, 프로파일 없음)  | `docker compose up -d db`                               |
| MSSQL    | `mssql`                 | `docker compose --profile mssql up -d db-mssql-init`   |
| Oracle   | `oracle`                 | `docker compose --profile oracle up -d db-oracle`      |
| SQLite   | `sqlite`                 | 컨테이너 불필요 (파일 기반)                             |

```bash
# 예: MSSQL로 실행
SPRING_PROFILES_ACTIVE=mssql \
  DB_URL="jdbc:sqlserver://localhost:1433;databaseName=aidevframework;encrypt=false" \
  DB_USERNAME=sa DB_PASSWORD='YourStrong!Passw0rd' \
  ./gradlew bootRun

# 예: SQLite로 실행 (제일 가볍다 — 서버 없이 프로젝트 루트에 파일 하나 생김)
SPRING_PROFILES_ACTIVE=sqlite ./gradlew bootRun
```

Flyway 마이그레이션 위치는 `spring.flyway.locations: classpath:db/migration/{vendor}` — `{vendor}`가
datasource 방언에 따라 `postgresql`/`sqlserver`/`oracle`로 자동 치환된다. 새 DB를 추가하려면
`db/migration/<vendor>/`에 동일한 스키마의 마이그레이션만 추가하면 된다.

**SQLite는 예외**: Flyway 최신 버전(12.x)이 SQLite 커뮤니티 모듈을 지원하지 않아서(구버전 10.x에 멈춰 있음),
`sqlite` 프로파일에서는 Flyway를 끄고 Hibernate `ddl-auto=update`로 스키마를 자동 생성한다
(`application-sqlite.yml` 참고). 그만큼 SQLite는 로컬 개발/데모 전용이고 운영에는 권장하지 않는다.

**NoSQL 확장 지점**: 아직 구현하지 않았다. 필요해지면 `spring-boot-starter-data-mongodb`를 추가하고
`com.aidevframework.core.<domain>.nosql` 같은 패키지에 `@Document` 클래스 + `MongoRepository`를 두면 된다.
Spring Data JPA(관계형)와 Spring Data MongoDB는 서로 다른 영속성 컨텍스트라 같은 서비스 안에 공존 가능하다.

**Boot 4 주의사항**: Flyway 자동 설정이 `spring-boot-jdbc`에 포함되어 있지 않고 `spring-boot-flyway`
모듈로 분리되어 있다. `flyway-core`만 추가하면 마이그레이션이 조용히 스킵되니(에러 없이 그냥 안 돎)
반드시 `org.springframework.boot:spring-boot-flyway`도 같이 추가해야 한다(`build.gradle.kts`에 이미 반영됨).

### DB마다 쿼리 문법이 다른 문제 — 이미 Hibernate가 통역해준다

4개 DB를 붙이면서 "DB마다 SQL 문법이 다른데 이거 다 따로 짜야 하나" 걱정할 수 있는데, **JPA/Hibernate를
쓰는 한 이미 해결되어 있다.** `UserRepository extends JpaRepository`처럼 메서드 이름으로 만든 쿼리나
JPQL(`@Query("select u from User u where ...")`), Criteria API는 Hibernate가 현재 연결된 DB의
**Dialect**(`PostgreSQLDialect`/`SQLServerDialect`/`OracleDialect`/`SQLiteDialect`)에 맞는 네이티브
SQL로 번역해서 실행한다. `LIMIT`/`OFFSET` vs `TOP`/`ROWNUM`, 문자열 결합, 페이징 방식 같은 차이를
전부 대신 처리해준다 — 이번에 4개 DB를 전환해가며 붙여봤지만 도메인 코드(엔티티/Repository/컨트롤러)는
단 한 줄도 안 바꿨다.

**지켜야 할 규칙 하나뿐**: `@Query(nativeQuery = true)`나 `JdbcTemplate`으로 원시 SQL 문자열을 직접
쓰지 말 것. 그 순간부터 그 쿼리는 특정 DB 문법에 종속되고, 다른 DB로 바꾸면 깨진다. 정말 원시 SQL이
필요한 특수한 케이스가 아니면 JPQL/메서드 이름 쿼리/Criteria API만 쓰면 이 프레임워크 안에서는
DB를 갈아 끼워도 코드가 그대로 간다.

**예외 — 스키마 마이그레이션(Flyway)은 다르다.** Flyway는 "그냥 이 SQL을 실행해라"는 도구라 방언을
대신 번역해주지 않는다. 그래서 `db/migration/<vendor>/`마다 SQL을 따로 손으로 썼다(Oracle만
`VARCHAR2` 때문에 갈라짐, 나머지 3개는 거의 동일 스크립트). 대안으로 Hibernate `ddl-auto=update`를
쓰면 엔티티에서 스키마를 자동 생성해 완전히 방언 독립적이 되지만, 마이그레이션 이력/롤백 안전성을
포기하는 셈이라 — 이 프레임워크는 운영 안전성을 우선해서 Flyway를 유지하기로 했다(SQLite만 예외적으로
`ddl-auto=update`를 쓰는 이유는 위 참고).

## 환경 분리 (dev/staging/prod)

Spring은 `SPRING_PROFILES_ACTIVE`에 프로파일을 콤마로 여러 개 넣으면 전부 동시에 활성화된다.
DB 종류(`mssql`/`oracle`/`sqlite`)와 환경(`prod`)은 서로 독립적인 축이라 조합해서 쓴다:

```bash
# 운영 + MSSQL
SPRING_PROFILES_ACTIVE=prod,mssql ...

# 운영 + 기본 Postgres (DB 프로파일 생략 가능)
SPRING_PROFILES_ACTIVE=prod ...
```

지금 `prod` 프로파일이 실제로 바꾸는 건 `DevAdminSeeder`(admin 계정 자동 시딩) 비활성화 하나뿐이다.
환경별로 로그 레벨/actuator 노출 범위 등을 더 다르게 하고 싶으면 `application-prod.yml`을 추가하면
된다 — DB 프로파일 파일들(`application-mssql.yml` 등)과 같은 방식으로 동작한다.
Helm으로 배포할 때는 `helm/ai-dev-framework/values-prod.yaml`이 `coreService.extraEnv`로
`SPRING_PROFILES_ACTIVE=prod`를 이미 넣어준다.

## Docker

```bash
docker build -t core-service:local .
docker run --rm -p 8080:8080 \
  -e DB_URL=jdbc:postgresql://host.docker.internal:5432/aidevframework \
  -e DB_USERNAME=aidevframework -e DB_PASSWORD=aidevframework \
  core-service:local
```

멀티스테이지 빌드(JDK로 빌드 → JRE로 실행), non-root(`appuser`)로 구동된다. SQLite JDBC 드라이버가
glibc 기준 네이티브 라이브러리를 번들하고 있어서 런타임 베이스는 alpine이 아니라 debian 계열(`eclipse-temurin:21-jre`)이다.
루트의 `docker compose up -d --build`로 Postgres까지 포함해서 한 번에 띄우는 게 제일 편하다.

## 아직 안 된 것 (다음 단계)

- 멀티테넌시: `TenantContext`만 있고, Hibernate `CurrentTenantIdentifierResolver` 연결은 아직 없음 (스키마별 데이터소스 라우팅 필요)
- NoSQL(Mongo) 실제 구현 — 위 확장 지점 문서만 있고 코드는 없음
- Helm Chart — Phase 4에서 진행
- 이미지 크기(현재 ~650MB, 4개 DB 드라이버 전부 포함) — 필요하면 jlink 커스텀 런타임으로 줄일 수 있음
