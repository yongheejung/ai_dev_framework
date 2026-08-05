# 1. 새 프로젝트 시작하기

## 1.1 저장소 복제

두 가지 방법이 있다.

**A. 완전히 새 저장소로 시작 (권장)** — 이 프레임워크의 커밋 히스토리를 가져갈 필요가 없는 경우.

```bash
git clone https://github.com/yongheejung/ai_dev_framework.git my-new-project
cd my-new-project
rm -rf .git
git init
git add .
git commit -m "Initial commit from ai_dev_framework"
# GitHub에서 my-new-project 저장소를 새로 만든 뒤
git remote add origin https://github.com/<계정>/my-new-project.git
git push -u origin main
```

**B. 프레임워크 자체를 계속 발전시키면서 그 위에서 바로 작업** — 이번 프로젝트가 프레임워크
개선으로 이어질 수도 있는 경우. 이 저장소에 브랜치를 파서 작업하고, 나중에 프로젝트 고유 코드만
따로 뽑아내는 방식. 여러 프로젝트를 동시에 찍어낼 계획이면 A가 유지보수하기 더 쉽다.

## 1.2 프로젝트 이름 바꾸기 (선택)

**대부분 안 바꿔도 된다.** Helm 배포는 `helm install <프로젝트명> ...`처럼 설치할 때 이름을
주기 때문에(`_helpers.tpl`의 `fullname`이 `.Release.Name`을 그대로 씀) 차트 자체를 고칠 필요가
없다. docker-compose도 컨테이너 이름이 폴더명 기준으로 자동으로 붙을 뿐, 코드 안에 프로젝트명이
박혀있진 않다.

정말 바꾸고 싶다면 아래 위치들이다:

| 위치 | 내용 |
|---|---|
| `core-service/build.gradle.kts` | `group = "com.aidevframework"` — 사내/개인 패키지 네임스페이스로 바꾸고 싶으면 (자바 패키지 전체를 리네이밍해야 해서 IDE의 "Rename Package" 기능을 쓰는 게 안전함) |
| `core-service/settings.gradle.kts` | `rootProject.name = "core-service"` |
| `bff-service/app/core/config.py` | `app_name: str = "bff-service"` |
| `frontend/package.json` | `"name": "frontend"` |
| `frontend/src/app/layout.tsx` | 화면에 보이는 타이틀 "AI Dev Framework" |
| `mobile/pubspec.yaml` | `name: ai_dev_framework_mobile` |
| `helm/ai-dev-framework/Chart.yaml` | `name: ai-dev-framework` — Helm 저장소에 배포하거나 여러 프레임워크 포크를 구분해야 할 때만 |
| 루트 `README.md` | 프로젝트 설명 |

## 1.3 로컬에서 처음 띄우기

필요한 건 Docker Desktop뿐이다 (Java/Node/Python 로컬 설치 없이도 컨테이너 안에서 전부 빌드됨).

```bash
docker compose up -d --build
```

이 한 줄로 뜨는 것:

1. `db` — Postgres (헬스체크 통과할 때까지 다른 서비스는 대기)
2. `core-service` — 부팅 시 Flyway가 마이그레이션을 자동 실행, `admin`/`admin1234` 관리자 계정도
   자동 시딩됨(`DevAdminSeeder`, `prod` 프로파일에서는 비활성화)
3. `bff-service-migrate` — Alembic 마이그레이션을 한 번 돌리고 종료되는 잡
4. `bff-service` — 마이그레이션 잡이 성공해야 시작됨
5. `frontend` — Next.js, 브라우저가 아니라 서버가 내부적으로 core-service/bff-service를 프록시

확인:

```bash
curl http://127.0.0.1:8080/actuator/health   # core-service
curl http://127.0.0.1:8000/health            # bff-service
```

브라우저로 `http://127.0.0.1:3000` 접속 (`localhost`가 아니라 `127.0.0.1` — Windows+Docker
Desktop 환경에서 `localhost`가 이유 없이 안 열리는 경우가 있음, `frontend/README.md` "알려진 이슈"
참고). `admin` / `admin1234`로 로그인해서 관리자 핑 버튼과 에이전트 작업 등록/조회가 되는지 확인하면
전체 스택이 제대로 붙은 것이다.

다른 로컬 포트를 쓰고 싶으면(다른 프로젝트와 충돌 날 때):

```bash
CORE_SERVICE_PORT=18080 BFF_SERVICE_PORT=18000 FRONTEND_PORT=13000 docker compose up -d --build
```

## 1.4 서비스별로 로컬에서 직접 개발하기

전체를 매번 Docker로 재빌드하면서 개발하면 느리다. DB만 Docker로 띄우고 나머지는 로컬에서 직접
띄우는 게 일반적인 개발 루프다.

```bash
docker compose up -d db   # Postgres만
```

- **core-service**: `cd core-service && ./gradlew bootRun` (IDE에서 직접 실행해도 됨)
- **bff-service**: `bff-service/README.md`의 "로컬 실행" 참고 (venv + `uvicorn app.main:app --reload`)
- **frontend**: `cd frontend && npm run dev` — `.env.local`에 `BFF_INTERNAL_URL=http://localhost:8000`,
  `CORE_SERVICE_INTERNAL_URL=http://localhost:8080` 설정. **`localhost`로 접속할 것** (`127.0.0.1`
  아님 — Next.js 16 dev 서버가 `127.0.0.1`발 요청을 cross-origin으로 보고 JS/HMR 리소스를
  막는 경우가 있음. Docker 관련 `127.0.0.1` 우회와 반대 방향이니 헷갈리지 말 것)

## 1.5 다음으로 읽을 것

- 로그인/권한 체계를 이해하려면 → [02-auth-and-rbac.md](02-auth-and-rbac.md)
- 첫 기능을 추가해보려면 → [04-adding-a-feature.md](04-adding-a-feature.md) (가장 실전적인 문서)
