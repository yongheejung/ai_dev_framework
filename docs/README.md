# AI Dev Framework 사용 가이드

여기 있는 문서들은 "이 프레임워크가 어떻게 만들어졌는가"가 아니라 **"이 프레임워크로 실제 새
프로젝트를 어떻게 만드는가"**를 다룬다. 아키텍처/구현 배경은 각 서비스 폴더의 README
(`core-service/README.md`, `bff-service/README.md`, `frontend/README.md`, `mobile/README.md`,
`helm/ai-dev-framework/README.md`)에 있으니 필요할 때 같이 참고할 것.

## 목차

1. [새 프로젝트 시작하기](01-getting-started.md) — 이 저장소를 새 프로젝트로 복제하고 처음 띄우기까지
2. [인증 / RBAC](02-auth-and-rbac.md) — JWT 로그인 흐름, 역할(Role) 추가, 새 API를 인증/인가로 보호하는 법
3. [데이터베이스](03-database.md) — DB 프로파일 전환(Postgres/MSSQL/Oracle/SQLite), 마이그레이션 추가하는 법
4. [새 기능(도메인) 추가하기](04-adding-a-feature.md) — core-service/bff-service/frontend/mobile에 같은 패턴으로 기능 하나를 처음부터 끝까지 추가하는 실습
5. [배포](05-deployment.md) — docker-compose 로컬 배포, Helm으로 K8s 배포, dev/staging/prod 환경 분리, CI

## 먼저 알아둘 것

- **표준 응답 포맷**: core-service(Spring Boot)와 bff-service(FastAPI) 모두
  `{ "success": boolean, "data": T | null, "error": { "code": string, "message": string } | null }`
  형태로 응답한다. 프론트/모바일이 어느 백엔드를 호출하든 같은 방식으로 처리할 수 있게 하기 위한
  의도적인 통일이다. 새 API를 만들 때도 이 포맷을 깨지 말 것.
- **역할 분담**: core-service = 트랜잭션이 걸리는 핵심 비즈니스 로직 + 인증/인가의 소스 오브 트루스.
  bff-service = AI 에이전트 연동, 가벼운 조회/집계, core-service가 굳이 안 알아도 되는 자체 데이터.
  "이게 core-service 일인가 bff-service 일인가" 애매하면 — 트랜잭션/정합성이 중요하면 core, 아니면 bff.
- **브라우저/모바일 앱은 백엔드 주소를 모른다(웹만)**: 웹 프론트는 항상 `/api/core/*`, `/api/bff/*`로만
  호출하고 Next.js 서버가 실제 백엔드로 프록시한다 (`04-adding-a-feature.md`, `05-deployment.md` 참고).
  모바일은 서버 사이드 프록시가 없어서 빌드 시점에 실제 백엔드 주소를 주입해야 한다.
