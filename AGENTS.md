# AGENTS.md — AI 코딩 에이전트 규칙

이 파일은 사람이 아니라 **이 저장소에서 코드를 생성/수정하는 AI 에이전트**(Feature Developer,
Maintenance 등)를 위한 것이다. 코드를 쓰기 전에 반드시 읽을 것. "왜 이렇게 정했는지"가 궁금하면
`docs/`(사람용 상세 가이드)를 참고하되, 여기 적힌 규칙은 예외 없이 지킬 것 — 특히 응답 포맷과
DB 이식성 규칙은 프레임워크 전체가 이 위에 서 있으므로 절대 깨지 말 것.

## 0. 모든 서비스 공통, 예외 없음

1. **모든 API 응답은 `{ success, data, error }` 표준 포맷을 따른다.**
   `error`는 `{ code, message }`. core-service는 `ApiResponse<T>`
   (`common/ApiResponse.java`), bff-service는 `ApiResponse[T]`(`app/core/responses.py`)를 쓴다.
   새 엔드포인트가 이 포맷을 벗어나면 안 된다.
2. **원시 SQL 문자열을 쓰지 않는다.** JPA는 `@Query(nativeQuery = true)` 금지, SQLAlchemy는
   `session.execute(text("..."))` 금지. ORM/쿼리 빌더 DSL만 쓴다 — 그래야 Postgres/MSSQL/Oracle/
   SQLite 사이를 설정만으로 오갈 수 있다(`docs/03-database.md`).
3. **웹/모바일에서 백엔드를 직접 호출하지 않는다.** 항상 공용 API 클라이언트를 거친다 — 웹은
   `bffClient`/`coreClient`(`frontend/src/shared/api/client.ts`), 모바일은 같은 이름의
   객체(`mobile/lib/core/api_client.dart`). 컴포넌트/화면에서 `fetch`/`axios`/`http` 패키지를
   직접 쓰지 않는다.
4. **색상을 하드코딩하지 않는다.** 웹은 Tailwind 테마 토큰(`globals.css`의 `@theme inline`,
   `bg-background`/`text-foreground`/`text-destructive` 등), 모바일은
   `Theme.of(context).colorScheme`(`core/theme.dart`)만 쓴다. `#fff`, `Color(0x...)` 같은 리터럴
   금지.
5. **새 기능을 추가할 때는 기존 예시 도메인을 복제한다.** 인증 필요 없는 기능 →
   `agent-task`(bff-service + `features/agent-task` + `features/agent_task`) 패턴을 그대로 따라
   할 것. 인증 필요한 기능 → `auth` 도메인 패턴. 구조를 새로 발명하지 말 것. 자세한 실습은
   `docs/04-adding-a-feature.md`.

## 1. core-service (Spring Boot 4 / Java 21)

- 컨트롤러: `@RestController`, 반환 타입은 항상 `ApiResponse<T>`. 예시: `AdminController.java`,
  `AuthController.java`.
- 에러 처리: 컨트롤러/서비스에서 try/catch로 직접 에러 응답을 만들지 않는다. `BusinessException`
  (`common/BusinessException.java`)을 `ErrorCode`(`common/ErrorCode.java`)와 함께 던지면
  `GlobalExceptionHandler`가 표준 포맷으로 변환한다. 새 에러 종류가 필요하면 `ErrorCode`에 항목을
  추가한다 — 즉석에서 문자열을 만들지 않는다.
- 인증/인가: 경로 단위는 `SecurityConfig.securityFilterChain()`의 `requestMatchers(...).hasRole(...)`,
  메서드 단위는 `@PreAuthorize("hasRole('X')")`(`@EnableMethodSecurity` 이미 켜짐). 새 역할은 그냥
  문자열이라 스키마 변경 없이 바로 쓸 수 있다. 자세히: `docs/02-auth-and-rbac.md`.
- DB: JPA 엔티티 + Flyway. 새 마이그레이션은 `db/migration/{postgresql,sqlserver,oracle}/`에
  `V{n}__description.sql` 형식으로 벤더마다 추가(SQLite는 `ddl-auto: update`라 마이그레이션 파일
  불필요). 새 DB를 실제로 검증 안 했다면 "미검증"이라고 코드/PR에 명시할 것 — 확인도 안 하고
  지원한다고 적지 않는다.
- 멀티테넌시: `X-Tenant-Id` 헤더가 `/actuator`, `/api/v1/auth/**` 외 모든 경로에 필수지만
  (`TenantFilter`), **아직 Hibernate 테넌트 리졸버에 연결되어 있지 않다** — 헤더는 요구되지만 실제
  스키마 분리는 안 된다. 이 사실을 모르고 "테넌트별로 데이터가 분리된다"고 가정하는 코드를 쓰지 말 것.

## 2. bff-service (FastAPI, Python)

- 라우터: `app/api/v1/<domain>.py`에 작성, `app/main.py`에 `app.include_router(...)`로 등록.
  응답 모델은 `ApiResponse[YourPydanticModel]`.
- 모델: `app/models.py`에 `Mapped`/`mapped_column`으로 SQLAlchemy 모델 정의.
- 마이그레이션: `alembic revision --autogenerate -m "..."` 후 생성된 파일을 반드시 검토하고
  `alembic upgrade head`. core-service와 다른 DB(`aidevframework_bff`)를 쓴다 — 공유 스키마에
  손대지 말 것.
- **인증이 아직 없다.** `agent-tasks` 같은 기존 엔드포인트는 토큰 검증 없이 열려 있다. 사용자별
  데이터가 필요한 기능을 추가하기 전에 반드시 `docs/02-auth-and-rbac.md` 2.4절을 읽고 인증 방식을
  먼저 정할 것 — `request`에 인증된 사용자 정보가 들어있다고 가정하고 코드를 짜면 안 된다.

## 3. frontend (Next.js / React / Tailwind / TanStack Query)

- 새 도메인: `features/<domain>/{types.ts, hooks/, components/}` + `app/<domain>/page.tsx`.
  `features/agent-task/`를 그대로 복제해서 이름만 바꾸는 게 표준 절차.
- 서버 상태는 TanStack Query(`useQuery`/`useMutation`)로만 관리한다 — `useState`+`useEffect`로
  직접 fetch하지 않는다.
- UI는 `components/ui/`의 공용 파츠(`Button`/`Input`/`Card`/`Table`/`Dialog`)만 쓴다. 없는
  파츠가 필요하면 `components/ui/`에 새로 추가하고 재사용 가능하게 만든다 — 화면 코드 안에 즉석으로
  스타일링된 엘리먼트를 박지 않는다.
- 백엔드 주소를 절대 하드코딩/노출하지 않는다 — 브라우저는 `/api/core/*`, `/api/bff/*`로만
  호출하고 Next.js 서버(Route Handler, `app/api/{bff,core}/[...path]/route.ts`)가 프록시한다.
- `frontend/AGENTS.md`(Next.js가 자동 관리, 지우지 말 것)도 같이 읽을 것 — 이 프로젝트가 쓰는
  Next.js 16의 버전 특이사항(예: `middleware.ts` → `proxy.ts`, `rewrites()`는 빌드타임 고정이라
  런타임 프록시에 못 씀)이 정리되어 있다.

## 4. mobile (Flutter)

- 새 도메인: `features/<domain>/{models/, data/, providers/, screens/}`.
  `features/agent_task/`를 그대로 복제.
- 서버 상태는 Riverpod `AsyncNotifier`로만 관리 (웹의 TanStack Query에 대응).
- 색상은 `Theme.of(context).colorScheme`만. 브랜드 색을 바꾸려면 `core/theme.dart`의
  `_seedColor` 한 줄만 바꾸면 된다 — 화면마다 색을 따로 정의하지 않는다.
- **`android/`/`ios/` 네이티브 프로젝트가 아직 커밋되어 있지 않다.** 로컬에서 `flutter build`가
  바로 안 될 수 있다 — `mobile/README.md` 참고. CI(`.github/workflows/mobile-ci.yml`)는
  `flutter create --platforms=...`로 그때그때 스캐폴딩해서 빌드를 검증한다.

## 5. 작업 전/후 체크리스트

- [ ] 응답이 `{success, data, error}` 포맷을 따르는가
- [ ] 원시 SQL, 하드코딩된 색상, 공용 클라이언트를 우회한 직접 HTTP 호출이 없는가
- [ ] 인증이 필요한 기능인데 bff-service에 넣으려 한다면, 2절의 "인증이 아직 없다" 경고를 읽고
      의도적으로 그런 것인가
- [ ] core-service DB 스키마를 건드렸다면 최소 `postgresql/` 마이그레이션은 추가했는가
- [ ] 테스트가 실제로 통과하는가: `./gradlew test`(core-service) / `pytest`(bff-service) /
      `npm run lint && npm run build`(frontend)
- [ ] 새로 만든 게 아니라 기존 예시 도메인(`agent-task` 또는 `auth`) 구조를 그대로 따라 했는가

## 6. 더 필요하면

사람이 읽는 상세 버전(왜 이렇게 만들었는지, 배포 방법, 명령어 예시)은 `docs/README.md`부터 시작.
막히면 프롬프트/RAG에 이 파일 전체를 넣거나, 해당 절만 골라서 넣어도 된다 — 이 문서는 그 용도로
쓰라고 만든 것이다.
