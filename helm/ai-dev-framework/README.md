# ai-dev-framework Helm Chart

Postgres + core-service + bff-service + frontend + Ingress를 한 번에 배포한다.

```bash
helm install myproject ./helm/ai-dev-framework
```

`myproject`가 그대로 모든 리소스 이름의 접두사가 된다 (`myproject-core-service`, `myproject-postgresql` ...).
새 프로젝트를 만들 때마다 release 이름만 바꿔서 재사용하면 된다.

로컬 이미지(`core-service:local`, `bff-service:local`, `frontend:local`)를 쓰므로, kind로 테스트할
때는 먼저 `kind load docker-image core-service:local`/`bff-service:local`/`frontend:local`로
클러스터에 로드해야 한다. 실제 배포에서는 `--set coreService.image.repository=... --set
coreService.image.tag=...` (bffService/frontend도 동일)로 레지스트리 이미지를 가리키면 된다.

**frontend는 이미지 재빌드 없이 환경 전환 가능**: 브라우저는 core-service/bff-service 주소를
전혀 모른다 — frontend 컨테이너 안의 Next.js Route Handler가 `BFF_INTERNAL_URL`/
`CORE_SERVICE_INTERNAL_URL`(이 차트가 자동으로 이 릴리스의 Service DNS로 채워줌)을 보고 요청마다
프록시한다. 그래서 `frontend:local` 이미지 하나로 dev/staging/prod 어디든 그대로 쓸 수 있다
(자세한 원리는 `frontend/README.md`의 "백엔드 연결" 참고).

## 환경별 배포 (dev/staging/prod)

`values-dev.yaml`/`values-staging.yaml`/`values-prod.yaml`은 기본 `values.yaml` 위에 얹는
오버레이다. release 이름과 `-f` 파일 조합으로 환경을 나눈다:

```bash
helm install myproject-dev ./helm/ai-dev-framework -f helm/ai-dev-framework/values-dev.yaml

helm install myproject-staging ./helm/ai-dev-framework \
  -f helm/ai-dev-framework/values-staging.yaml \
  --set postgresql.password=<시크릿>

helm install myproject ./helm/ai-dev-framework \
  -f helm/ai-dev-framework/values-prod.yaml \
  --set postgresql.password=<시크릿> \
  --set coreService.image.tag=<릴리스 태그> --set bffService.image.tag=<릴리스 태그> \
  --set frontend.image.tag=<릴리스 태그>
```

비밀번호나 실제 이미지 태그처럼 값이 바뀌는 것/커밋하면 안 되는 것은 `-f` 파일에 안 넣고
`--set`이나 CI 시크릿으로 주입한다 — `values-prod.yaml` 안에 주석으로 표시해뒀다.
`values-prod.yaml`은 내장 Postgres 대신 관리형 DB(RDS/Cloud SQL 등)로 옮기는 방법도 주석으로 안내한다.

core-service는 환경 프로파일과 DB 프로파일을 동시에 켤 수 있다 (Spring은 `SPRING_PROFILES_ACTIVE`에
콤마로 여러 개를 넣으면 전부 활성화된다) — 예: `SPRING_PROFILES_ACTIVE=prod,mssql`이면 운영
설정(`DevAdminSeeder` 비활성화 등) + MSSQL 접속을 동시에 적용. `values-prod.yaml`은
`coreService.extraEnv`로 `SPRING_PROFILES_ACTIVE=prod`를 이미 넣어뒀다.

## 확인

```bash
kubectl port-forward svc/myproject-core-service 8080:80
kubectl port-forward svc/myproject-bff-service 8000:80
curl http://localhost:8080/actuator/health
curl http://localhost:8000/health
```

## 알아둘 것

- **DB 분리**: core-service(Flyway)와 bff-service(Alembic)는 같은 Postgres 인스턴스 안에서도
  서로 다른 DB(`aidevframework` / `aidevframework_bff`)를 쓴다. 같은 스키마를 공유하면 어느 쪽
  마이그레이션이 먼저 도냐에 따라 Flyway가 "낯선 테이블이 이미 있다"며 baseline 에러를 내는 실제
  버그가 있었다 — 이 차트를 검증하다가 발견했다. 두 번째 DB는 Postgres 컨테이너의
  `docker-entrypoint-initdb.d` 초기화 스크립트(`postgresql-init-configmap.yaml`)로 최초 기동 시
  1회만 생성된다.
- **마이그레이션 순서**: bff-service-migrate는 `helm.sh/hook`이 아니라 그냥 Job이다 — Postgres가
  이 차트 안에서 같이 뜨기 때문에(pre-install hook은 다른 리소스보다 먼저 실행되어 Postgres가
  아직 없을 때 뜬다), 대신 `wait-for-postgres` initContainer로 기다린다. Job 이름에
  `{{ .Release.Revision }}`을 붙여서 `helm upgrade` 때마다 새로 실행되게 했다(Alembic은 멱등적).
- **DB 교체**: `postgresql.enabled: false`로 끄고 `coreService.extraEnv`/`bffService.extraEnv`로
  외부 DB 접속 정보를 직접 넣으면 된다 (core-service는 해당 DB 프로파일도 같이 지정해야 함 —
  `core-service/README.md`의 DB 다중 지원 참고).
- **Ingress**: 클러스터에 ingress 컨트롤러(nginx 등)가 이미 떠 있다고 가정한다. 브라우저가 직접
  거치는 건 frontend 하나뿐이라(백엔드 호출은 frontend 컨테이너 안에서 서버 사이드로 프록시됨)
  `/` 전체를 frontend로 보내고, `/api/v1/agent-tasks`만 bff-service 직접 호출(curl/Postman 등)용으로
  남겨뒀다.

## 실제 검증한 내용

kind(Kubernetes in Docker)에 실제로 설치해서: 전체 파드 Ready, 마이그레이션 Job 정상 완료,
core-service JWT 로그인+RBAC(`/api/v1/admin/ping`), bff-service DB 읽기/쓰기(`/api/v1/agent-tasks`)를
포트포워딩으로 직접 호출해 확인했다. `helm upgrade`(재배포)와 옵션 없는 깨끗한 `helm install`도
재현 테스트했다. Ingress는 오브젝트 생성까지만 확인했고(클러스터에 컨트롤러가 없어서), 실제
컨트롤러를 통한 라우팅까지는 테스트하지 않았다 — 표준 `networking.k8s.io/v1 Ingress` 스펙이라
리스크는 낮다고 판단.
