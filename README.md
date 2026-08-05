# AI Dev Framework

1인 개발자가 여러 프로젝트를 빠르게 찍어낼 수 있도록 만드는 하이브리드 개발 프레임워크.
전체 비전은 [README.MD.txt](README.MD.txt) 참고.

## 구성

```
core-service/       Spring Boot 4 / Java 21 — 비즈니스 로직, DB 트랜잭션, JWT+RBAC 인증
bff-service/        FastAPI — AI 에이전트 연동, 가벼운 BFF, 자체 DB 처리
frontend/           Next.js 표준 웹 프론트엔드 (frontend.md 스펙 기반)
mobile/             Flutter 모바일 앱 (구조/코드 작성됨, 빌드는 미검증 — mobile/README.md 참고)
docker-compose.yml  로컬 전체 스택 (Postgres + core-service + bff-service + frontend)
helm/ai-dev-framework/  helm install [프로젝트명] 한 번으로 K8s에 전체 스택 배포하는 차트
postgres-init/      로컬 Postgres 최초 기동 시 bff-service 전용 DB를 만드는 초기화 스크립트
```

## 빠른 시작 (로컬, Docker Compose)

```bash
docker compose up -d --build
```

이 한 줄로 Postgres, core-service(8080), bff-service(8000), frontend(3000)가 전부 뜬다. 다른 포트를
쓰고 싶으면 `CORE_SERVICE_PORT`/`BFF_SERVICE_PORT`/`FRONTEND_PORT`/`DB_PORT` 환경변수로 덮어쓰면 된다.

확인:

```bash
curl http://localhost:8080/actuator/health
curl http://localhost:8000/health
```

브라우저로 프론트엔드(`http://localhost:3000`)가 이유 없이 안 열리면, 일부 Windows+Docker Desktop
환경에서 `localhost` 대신 `http://127.0.0.1:3000`으로 접속해볼 것 (`frontend/README.md`의
"알려진 이슈" 참고 — 이 환경에서 실제로 재현/우회 확인함). 프론트엔드 → 백엔드 호출은 Next.js
서버가 컨테이너 내부에서 프록시하므로 이 이슈의 영향을 받지 않는다.

## 빠른 시작 (쿠버네티스, Helm)

```bash
helm install myproject ./helm/ai-dev-framework
```

DB + core-service + bff-service + frontend + Ingress가 한 번에 뜬다. 자세한 내용은 `helm/ai-dev-framework/README.md`.

각 서비스 상세(로컬 개발 방식, DB 프로파일 전환, 인증 사용법 등)는 `core-service/README.md`,
`bff-service/README.md`, `frontend/README.md` 참고.

## 사용 가이드

"이 프레임워크로 실제 새 프로젝트를 어떻게 만드는가"는 [`docs/`](docs/README.md)에 주제별로
정리되어 있다:

- [새 프로젝트 시작하기](docs/01-getting-started.md)
- [인증 / RBAC](docs/02-auth-and-rbac.md)
- [데이터베이스](docs/03-database.md)
- [새 기능(도메인) 추가하기](docs/04-adding-a-feature.md)
- [배포](docs/05-deployment.md)

## 진행 단계

- [x] Phase 1 — core-service JWT + RBAC 자체 인증
- [x] Phase 2 — DB 다중 지원 (Postgres/MSSQL/Oracle/SQLite, bff-service SQLAlchemy+Alembic)
- [x] Phase 3 — Docker 표준화 (Dockerfile, `docker compose up`으로 전체 스택 기동)
- [x] Phase 4 — Helm Chart (`helm install [프로젝트명]`으로 DB+백엔드+Ingress 한 번에 배포)
- [x] Phase 5 — 프론트엔드 표준 (Next.js + Tailwind + shadcn/ui, `features/agent-task`로 bff-service와
      실제 연동 검증. Flutter 모바일 앱은 아직 시작 안 함)
- [x] Phase 6 — 환경 분리(Helm `values-{dev,staging,prod}.yaml`) + 프론트엔드-백엔드 접속 설정화
      (Route Handler 프록시로 브라우저가 백엔드 주소를 몰라도 되게 함, 이미지 재빌드 없이 환경 전환) +
      DB 쿼리 방언 추상화 가이드 (Hibernate/SQLAlchemy가 이미 그 역할을 함)
- [x] Phase 7 — 프론트엔드 core-service JWT/RBAC 연동(`/login`, 관리자 핑 데모) + 테마 토글 버튼
      (next-themes) + Flutter 모바일 앱 구조/코드 작성 (SDK 미설치로 빌드는 미검증 — `mobile/README.md`
      "다음 단계" 참고)
