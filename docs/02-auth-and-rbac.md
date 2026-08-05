# 2. 인증 / RBAC

인증/인가는 **core-service가 유일한 source of truth**다. bff-service는 현재 자체 인증 미들웨어가
없다(아래 "bff-service는 아직 인증이 없다" 참고) — 인증이 필요한 기능은 core-service에 만들거나,
core-service가 검증한 사용자 정보를 bff-service로 전달하는 방식을 직접 설계해야 한다.

## 2.1 전체 흐름

```
[클라이언트] --POST /api/v1/auth/login--> [core-service]
                                              │
                                    BCrypt로 비밀번호 검증
                                              │
                                    RS256 JWT 발급 (roles claim 포함)
                                              │
[클라이언트] <-- { accessToken, tokenType, expiresInSeconds } --┘

[클라이언트] --GET /api/v1/me  (Authorization: Bearer <token>)--> [core-service]
                                              │
                                    JwtDecoder가 서명 검증
                                              │
                                    roles claim → ROLE_-prefixed GrantedAuthority
                                              │
[클라이언트] <-- { username, roles: ["ROLE_USER", "ROLE_ADMIN"] } --┘
```

- 토큰 서명 키(RSA 키페어)는 `JwtKeyConfig`에서 **메모리에서 매번 새로 생성**된다 — core-service를
  재시작하면 이전에 발급된 토큰은 전부 무효가 된다. 로컬 개발/데모용 설정이다. 운영에서 여러 인스턴스를
  띄우거나 재시작 후에도 세션을 유지하려면 고정된 키(환경변수/시크릿 매니저로 주입)로 바꿔야 한다 —
  `JwtKeyConfig`를 수정.
- 토큰 만료는 기본 1시간(`JwtService.expirySeconds()`). Refresh token은 없다 — 필요하면 직접
  추가해야 한다(아직 이 프레임워크 범위 밖).

## 2.2 회원가입/로그인 API

```bash
# 회원가입 — 기본적으로 USER 역할만 부여됨
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" -H "X-Tenant-Id: default" \
  -d '{"username":"alice","password":"alice1234"}'

# 로그인
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" -H "X-Tenant-Id: default" \
  -d '{"username":"alice","password":"alice1234"}'
```

`X-Tenant-Id` 헤더가 없으면 `TenantFilter`가 `TENANT_NOT_RESOLVED`로 막는다(`/actuator`,
`/api/v1/auth/**`는 예외). **주의**: 테넌트 헤더는 지금 "요구되고 저장되기만" 한다 —
`TenantContext`가 스레드로컬에 담기지만 Hibernate `CurrentTenantIdentifierResolver`에는 아직
연결되어 있지 않다. 즉 스키마 분리 멀티테넌시는 **자리만 마련된 상태**고, 실제로 테넌트별로 데이터가
분리되지는 않는다. 진짜 멀티테넌시가 필요하면 이 부분을 직접 구현해야 한다.

## 2.3 새로운 역할(Role) 추가하기

역할은 enum이 아니라 문자열이다 — `user_roles` 테이블(`role VARCHAR(50)`)에 그냥 문자열로 저장된다.
새 역할을 추가하는 데 스키마 변경이나 코드 배포가 필요 없다는 뜻이다.

1. **역할을 부여**: 회원가입 직후에는 항상 `USER`만 붙는다(`AuthController.register()`). 관리자
   승격이나 다른 역할 부여는 별도 절차로 만들어야 한다 — 예를 들어 관리자 전용 API를 하나 만들어서
   `UserRepository`로 조회한 뒤 `user_roles`에 행을 추가하는 식. (지금 프레임워크에는 이 승격 API가
   없다 — 필요하면 `AdminController`처럼 `hasRole('ADMIN')`으로 막은 컨트롤러를 새로 만들 것.)
2. **경로 단위로 역할 요구**: `SecurityConfig.securityFilterChain()`의
   `.requestMatchers("/api/v1/admin/**").hasRole("ADMIN")` 같은 줄을 추가/수정.
3. **메서드 단위로 역할 요구**: 컨트롤러 메서드에 `@PreAuthorize("hasRole('MANAGER')")` 같이 붙인다
   (`AdminController.adminPing()` 예시 참고). `@EnableMethodSecurity`가 이미 켜져 있어서 바로 된다.
4. 프론트/모바일에서 역할에 따라 UI를 다르게 보여주려면 `/api/v1/me`가 내려주는 `roles` 배열
   (`["ROLE_USER", "ROLE_ADMIN"]` 형태, `ROLE_` 접두어 포함)을 그대로 비교하면 된다.

역할 이름을 코드 여러 곳에 흩어 쓰지 말고, 서비스마다 상수 하나로 모아두는 걸 권장한다(지금은
`"ADMIN"`, `"USER"` 리터럴이 몇 군데 흩어져 있다 — 역할이 늘어나면 `Roles.java` 같은 상수 클래스를
만들어 정리할 것).

## 2.4 새 API를 인증/인가로 보호하기

**core-service**:

```java
@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {

    @GetMapping
    // 이미 인증만 되어 있으면 통과 (SecurityConfig의 .anyRequest().authenticated() 기본 규칙)
    public ApiResponse<List<ProjectResponse>> list(Authentication authentication) {
        ...
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")   // 관리자만
    public ApiResponse<Void> delete(@PathVariable String id) {
        ...
    }
}
```

인증 안 된 요청은 자동으로 401(`UNAUTHORIZED`), 역할이 안 맞으면 403(`FORBIDDEN`) — 둘 다
`SecurityConfig`에 등록된 `AuthenticationEntryPoint`/`AccessDeniedHandler`가 표준 `ApiResponse`
JSON 포맷으로 응답한다. `permitAll()`로 열어둔 경로가 아닌 이상 따로 인증 체크 코드를 짤 필요가
없다.

**bff-service는 아직 인증이 없다.** `agent_tasks.py`의 엔드포인트들은 토큰 없이 누구나 호출 가능하다.
bff-service에 인증이 필요한 기능을 추가하려면 둘 중 하나를 골라야 한다:

- **core-service와 같은 JWT를 bff-service도 검증** — core-service가 공개하는 JWK(공개키)로
  FastAPI 미들웨어/dependency를 만들어 토큰을 검증. (`JwtKeyConfig`가 지금 매 재시작마다 키를
  새로 만들기 때문에, 이 방식을 쓰려면 먼저 2.1에서 언급한 "고정 키" 작업이 선행되어야 안정적으로
  동작한다.)
- **core-service를 거쳐서만 인증된 사용자 정보를 받음** — bff-service가 직접 JWT를 검증하지 않고,
  core-service가 프론트/모바일 요청을 검증한 뒤 내부 호출로 bff-service를 부르는 구조. 지금
  `CORE_SERVICE_BASE_URL` 설정은 있지만 실제 호출 클라이언트는 아직 구현 안 되어 있다
  (`bff-service/README.md`의 "아직 안 된 것" 참고).

프로젝트 성격에 따라 고를 것 — 에이전트 작업 데이터처럼 사용자별로 안 나뉘어도 되면 지금처럼 열어둬도
되고, 사용자별 데이터라면 위 둘 중 하나를 반드시 먼저 구현해야 한다.

## 2.5 프론트엔드/모바일에서 인증 붙이기

이미 `agent-task` 도메인과 같은 패턴을 `auth` 도메인이 보여주고 있다 — 새 화면에서 로그인 상태가
필요하면 그대로 재사용하면 된다.

**웹**: `frontend/src/features/auth/`
- `AuthContext.tsx` — `hasToken` boolean을 전역으로 제공 (React Context)
- `hooks/useMe.ts` — TanStack Query로 `/api/core/v1/me` 조회, 로그인 여부/역할 확인용
- `hooks/useLogin.ts`, `useLogout.ts`, `useRegister.ts` — 각각 mutation
- 컴포넌트에서 `coreClient`(자동으로 `Authorization`, `X-Tenant-Id` 헤더 붙음, `shared/api/client.ts`)로
  호출하면 토큰 관리를 신경 쓸 필요 없음

**모바일**: `mobile/lib/features/auth/`
- `providers/auth_provider.dart` — Riverpod `AsyncNotifier`, 웹의 `AuthContext`+`useMe`에 대응
- `data/auth_repository.dart` — `coreClient`로 로그인/회원가입/`/me` 호출
- 토큰은 `core/token_store.dart`(`flutter_secure_storage`)에 저장 — 웹의 `localStorage` 기반
  `shared/auth/token-store.ts`에 대응하는 자리지만 모바일에서는 더 안전한 시큐어 스토리지를 씀

두 경우 다 **직접 `fetch`/`http` 패키지로 토큰을 헤더에 수동으로 안 붙인다** — 반드시
`coreClient`/`bffClient`를 거쳐서 인증 헤더 처리를 한곳에 모아둔다. 이렇게 해야 나중에 토큰
갱신 로직(refresh token 등)을 추가할 때 호출부를 전부 고칠 필요가 없다.

## 2.6 운영 환경 체크리스트

- `SPRING_PROFILES_ACTIVE=prod`로 core-service를 띄워서 `DevAdminSeeder`(admin/admin1234 자동
  생성)가 비활성화되게 할 것 — Helm `values-prod.yaml`에 이미 반영되어 있음.
- `JwtKeyConfig`를 고정 키 방식으로 바꿀 것(2.1 참고) — 안 그러면 배포/재시작마다 전체 사용자
  세션이 끊긴다.
- CORS(`bff-service`의 `cors_origins`)는 실제 프론트 도메인만 허용하도록 좁힐 것.
