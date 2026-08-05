# frontend

AI Dev Framework의 웹 프론트엔드 표준. Next.js(App Router) + TypeScript + Tailwind CSS +
shadcn/ui 스타일 컴포넌트로 구성했다. `frontend.md`(원본 스펙 문서)의 구조를 그대로 따른다.

## 폴더 구조

```
src/
├── app/                  # [1] 페이지 라우팅 (새 페이지 추가하는 곳)
│   ├── layout.tsx        # 전사 공통 레이아웃 (GNB, 푸터) + Providers
│   ├── page.tsx          # 메인 화면
│   ├── globals.css       # 디자인 토큰 (색상 등 하드코딩 금지, 여기 변수만 사용)
│   ├── agent-tasks/
│   │   └── page.tsx      # 예시 도메인 페이지
│   └── api/
│       ├── bff/[...path]/route.ts   # bff-service 프록시 (BFF_INTERNAL_URL)
│       └── core/[...path]/route.ts  # core-service 프록시 (CORE_SERVICE_INTERNAL_URL)
├── components/ui/        # [2] 재사용 가능한 순수 UI 부품 (button, input, card, table, dialog)
├── features/             # [3] 도메인별 비즈니스 로직 + UI 결합
│   ├── agent-task/       # bff-service의 agent-tasks API에 실제로 연동된 예시
│   │   ├── components/   # AgentTaskTable.tsx, AgentTaskForm.tsx
│   │   ├── hooks/        # useAgentTasks.ts (TanStack Query)
│   │   └── types.ts
│   └── auth/             # core-service JWT 로그인/회원가입/RBAC 연동
│       ├── AuthContext.tsx   # 토큰 유무(hasToken) 전역 상태
│       ├── components/       # AuthNav.tsx(GNB), AdminPingDemo.tsx(RBAC 데모)
│       ├── hooks/             # useLogin/useRegister/useLogout/useMe/useAdminPing
│       └── types.ts
└── shared/                # [4] 공통 유틸리티
    ├── api/client.ts      # fetch 공통 래퍼 (core/bff의 ApiResponse 포맷 대응)
    ├── api/proxy.ts       # 백엔드 프록시 Route Handler 공통 로직
    └── utils/             # cn(), 날짜 포맷팅 등
```

## 원칙 (AI 에이전트가 새 기능 추가할 때 지켜야 할 것)

1. **API 호출은 항상 `features/<domain>/hooks/`의 TanStack Query 훅을 통해서만.** 컴포넌트 안에서
   직접 `fetch`나 `useEffect`로 데이터를 가져오지 않는다. `useAgentTasks.ts`가 표준 예시.
2. **UI는 `components/ui/`의 기존 부품만 재사용.** 새 화면이 필요하면 거기 있는 Button/Input/
   Card/Table/Dialog를 조합하고, 못 찾겠으면 `components/ui/`에 먼저 추가한다.
3. **색상은 절대 하드코딩(`#FFFFFF` 등) 금지.** `globals.css`의 CSS 변수(`--primary`,
   `--background` 등)만 `bg-primary`, `text-foreground` 같은 Tailwind 유틸리티로 사용한다.
   브랜드 색상을 바꿀 때는 `globals.css`의 변수 값만 바꾸면 전체 화면에 반영된다.
4. 다크모드는 `next-themes`(`app/theme-provider.tsx`)가 관리한다 — 헤더의 `ThemeToggle`
   (`components/ui/theme-toggle.tsx`)이 `<html>`에 `dark`/`light` 클래스를 붙이고 localStorage에
   저장한다. 새 컴포넌트를 만들 때 색상 하드코딩만 안 하면(3번) 다크모드는 자동으로 따라온다.
5. **백엔드는 항상 `bffClient`/`coreClient`(`shared/api/client.ts`)로만 호출.** 브라우저는
   core-service/bff-service의 실제 주소를 절대 모른다 — 아래 "백엔드 연결" 참고.
6. **인증이 필요한 core-service 호출은 `coreClient`만 쓰면 된다.** JWT(Authorization 헤더)와
   테넌트(X-Tenant-Id 헤더)를 자동으로 붙인다 — `shared/auth/token-store.ts`가 로그인 시 저장한
   토큰을 읽는다. 로그인 상태 자체는 `features/auth/hooks/useMe.ts`로 확인한다.

## 백엔드 연결 (dev/staging/prod 전환, 종속성 낮추기)

브라우저는 항상 같은 출처(origin)의 `/api/bff/*`, `/api/core/*`만 호출한다. 이 경로는 Next.js 서버의
Route Handler(`app/api/bff/[...path]/route.ts`, `app/api/core/[...path]/route.ts`)가 받아서
`BFF_INTERNAL_URL` / `CORE_SERVICE_INTERNAL_URL` 환경변수가 가리키는 실제 백엔드로 요청마다 그대로
전달(프록시)한다.

이렇게 하면:
- **프론트엔드 코드가 백엔드 주소를 몰라도 된다** — `shared/api/client.ts`의 `bffClient`/`coreClient`는
  항상 상대 경로(`/api/bff/v1/...`)만 사용한다.
- **환경별로 이미지를 다시 빌드할 필요가 없다** — 컨테이너를 띄울 때 `BFF_INTERNAL_URL`/
  `CORE_SERVICE_INTERNAL_URL` 값만 바꾸면 dev/staging/prod가 전환된다 (`docker-compose.yml`은
  도커 네트워크 DNS 이름을, Helm 차트는 K8s Service DNS 이름을 자동으로 넣어준다).

**주의**: `next.config.ts`의 `rewrites()`로 구현하려다가 실패한 적이 있다 — `rewrites()`는
`next build` 시점에 한 번 평가되어 라우트 매니페스트에 박히기 때문에, 컨테이너를 실행할 때
환경변수를 바꿔도 반영되지 않는다(직접 겪음). 그래서 요청마다 실행되는 Route Handler로 구현했다
(`shared/api/proxy.ts`가 공통 로직).

## 인증 (core-service JWT + RBAC)

`/login` 페이지에서 로그인/회원가입 둘 다 된다 (개발용 계정: `admin` / `admin1234`, ADMIN 역할 포함).
흐름은 이렇다:

1. `useLogin()`이 `coreClient.post("/auth/login", ...)` 호출 → 받은 JWT를
   `shared/auth/token-store.ts`(localStorage)에 저장하고 `AuthContext`의 `hasToken`을 true로 바꾼다.
2. `hasToken`이 true가 되는 순간 `useMe()`(`coreClient.get("/me")`)가 활성화되어 사용자 정보(아이디,
   역할)를 가져온다 — 헤더의 `AuthNav`가 이 값을 보고 로그인 상태를 표시한다.
3. 이후 모든 `coreClient` 호출에 JWT가 자동으로 실린다. 토큰이 만료/무효화되면(`/me`가 401을 주면)
   자동으로 로그아웃 처리된다.
4. 홈 화면의 "관리자 핑" 버튼(`AdminPingDemo`)이 core-service의 RBAC(`hasRole("ADMIN")`)을 실제로
   호출해서 보여준다 — admin 계정은 성공, 일반 계정은 403을 그대로 화면에 표시한다.

**core-service 쪽에서 같이 고친 것**: Spring Security가 인증/인가 자체를 거부하는 401/403은
컨트롤러에 도달하기 전에 발생해서 `GlobalExceptionHandler`(BusinessException 기반)를 안 거친다.
기본값은 본문 없는 401/403이라 프론트가 `res.json()`에서 파싱 에러로 죽었다 — core-service
`SecurityConfig`에 커스텀 `AuthenticationEntryPoint`/`AccessDeniedHandler`를 추가해서 이 경로도
표준 `ApiResponse` 포맷을 지키게 만들었다(`core-service/README.md` 참고).

## 로컬 실행

```bash
npm install
npm run dev
```

기본값(`http://localhost:8000` / `:8080`)으로 충분하면 `.env.local` 없이 바로 된다. bff-service가
다른 포트/호스트에 있으면 `.env.local`에 `BFF_INTERNAL_URL`/`CORE_SERVICE_INTERNAL_URL`을 설정한다.

bff-service가 먼저 떠 있어야 한다 (루트에서 `docker compose up -d db bff-service-migrate bff-service`,
또는 `bff-service/README.md` 참고).

### 알려진 이슈 1: `npm run dev`는 반드시 `localhost`로 접속 (127.0.0.1 아님)

`next dev`는 개발 서버 리소스(JS 청크, HMR 웹소켓)에 대한 cross-origin 요청을 기본적으로 막는다.
`http://127.0.0.1:3001`로 접속하면 페이지 뼈대(SSR HTML)는 뜨지만 JS 번들 로딩이 전부 막혀서
**클릭이든 뭐든 아무 상호작용도 안 되는데 콘솔에 에러도 안 뜬다** — 서버 로그(`Blocked cross-origin
request...`)에만 남는다. 직접 겪었다(테마 토글 버튼이 반응 없어서 한참 원인 찾음). 로컬 dev 서버는
꼭 `http://localhost:<port>`로 접속할 것 — 필요하면 `next.config.ts`에 `allowedDevOrigins`를 추가해서
다른 호스트도 허용할 수 있다.

### 알려진 이슈 2: Docker로 띄운 서비스는 Windows에서 `127.0.0.1`로 접속

위와 정반대 상황이라 헷갈리지 않게 구분한다 — 이건 `docker compose`/Helm(kind)로 띄웠을 때
얘기다. 이 환경(Windows + Docker Desktop)에서는 브라우저가 Docker로 노출된 포트를
`http://localhost:<port>`로 호출하면 503이 나고, 같은 요청을 `curl`로 host에서 보내면 성공하며,
`http://127.0.0.1:<port>`로 바꾸면 브라우저에서도 성공하는 현상을 확인했다(원인 미확정). 지금은
브라우저가 프론트엔드 자기 자신의 포트만 호출하므로(백엔드 프록시는 서버 쪽에서 일어남) 영향 범위가
줄었다 — 그래도 프론트엔드 페이지 자체가 이유 없이 안 열리면 `http://127.0.0.1:<FRONTEND_PORT>`로
접속해볼 것.

## 검증한 내용

`npm run build`(TypeScript 컴파일 + 프로덕션 빌드), `npm run lint` 통과 확인. 실제 브라우저/`curl`로
`/api/bff/v1/agent-tasks`, `/api/core/v1/ping`(X-Tenant-Id 헤더 포함) 프록시가 실제 백엔드까지
왕복하는 것을 확인했고, `/agent-tasks` 페이지에서 폼 제출 → 프록시 경유 POST → 목록 자동 갱신까지
확인했다. `<html>`에 `dark` 클래스를 넣어 다크모드 전환도 확인했다. kind(Kubernetes in Docker)에
Helm 차트로 실제 배포해서 `kubectl port-forward`와 두 프록시 경로까지 전부 재검증했다.

**잡은 버그**: Docker/Kubernetes가 컨테이너 환경변수 `HOSTNAME`을 파드/컨테이너 이름으로 자동
채워 넣는데, Next.js standalone 서버가 이 값을 바인드 주소로 써버려서 `0.0.0.0`이 아니라 그 이름
(사실상 파드 고유 IP)에만 리슨하게 됐다. Service/Ingress/Docker 포트 매핑을 통한 실제 트래픽은
파드 IP로 바로 붙기 때문에 멀쩡히 동작했지만, `kubectl port-forward`(loopback 경유)는 계속
`ECONNREFUSED`였다 — kind로 원인을 좁혀서 확인했고, `Dockerfile`의 `CMD`에서
`HOSTNAME=0.0.0.0`을 명시해서 고쳤다.

로그인/회원가입/로그아웃/RBAC(관리자 핑 성공·403)도 실제 core-service(Postgres 포함, docker-compose)에
붙여서 브라우저로 전체 플로우를 확인했다. 이 과정에서 잡은 버그 2개:

- **로그아웃해도 화면이 안 바뀜**: `queryClient.setQueryData(key, undefined)`를 TanStack Query가
  "갱신 없음"으로 무시해버려서, 토큰은 지워져도 캐시된 사용자 정보가 안 지워지고 있었다.
  `removeQueries`로 교체해서 고쳤다(`useLogout.ts`).
- **RBAC 403을 받으면 화면이 깨짐**: 위 "인증" 절의 core-service `SecurityConfig` 수정으로 해결.

## 아직 안 된 것

- 테마 토글 버튼 이외의 테마 커스터마이징 UI(브랜드 색상 설정 화면 등) 없음
- Flutter 모바일 앱 — `frontend.md` 스펙에는 있으나 아직 시작 안 함
