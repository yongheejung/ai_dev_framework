# 5. 배포

## 5.1 세 가지 배포 방식

| 방식 | 용도 |
|---|---|
| `docker compose up` | 로컬 개발/데모, 단일 서버에 그냥 올려도 되는 소규모 운영 |
| `helm install` (kind/minikube) | 배포 전 로컬에서 K8s 매니페스트 검증 |
| `helm install` (실제 클러스터) | dev/staging/prod 배포 |

## 5.2 이미지 태그와 환경 분리의 핵심 아이디어

**프론트엔드 이미지는 dev/staging/prod가 전부 동일하다.** 브라우저는 `/api/core/*`, `/api/bff/*`
경로로만 호출하고, Next.js 서버(컨테이너 안)가 `BFF_INTERNAL_URL`/`CORE_SERVICE_INTERNAL_URL`
환경변수를 **요청마다** 읽어서 실제 백엔드로 프록시한다(`frontend/src/shared/api/proxy.ts`,
`app/api/{bff,core}/[...path]/route.ts`). Next.js의 `next.config.ts`의 `rewrites()`는 빌드
시점에 고정되어 이 용도로 못 쓴다는 걸 이미 확인했음 — 그래서 굳이 Route Handler로 만든 것이다.
결과적으로 **환경을 바꿀 때 프론트 이미지를 다시 빌드할 필요가 없다** — 배포 시점의 환경변수만
다르면 됨. `helm/ai-dev-framework/templates/frontend-deployment.yaml`이 이 두 값을 해당 릴리스의
Service DNS 이름으로 자동으로 채워준다.

core-service/bff-service 이미지는 환경마다 다른 태그를 쓴다(`values-staging.yaml`의
`tag: "staging"`, `values-prod.yaml`의 `tag: "REPLACE_WITH_RELEASE_TAG"`) — 이 둘은 실제
비즈니스 로직이 들어있어서 dev/staging/prod에 서로 다른 버전이 떠 있을 수 있어야 하기 때문이다.

## 5.3 docker-compose로 배포

```bash
docker compose up -d --build
```

포트 충돌 시(다른 프로젝트가 이미 8080/8000/3000/5432를 쓰고 있을 때):

```bash
CORE_SERVICE_PORT=18080 BFF_SERVICE_PORT=18000 FRONTEND_PORT=13000 DB_PORT=15432 \
  docker compose up -d --build
```

간단한 단일 서버 운영이면 이대로 systemd나 크론으로 `docker compose up -d`를 관리해도 되지만,
여러 인스턴스로 스케일하거나 무중단 배포가 필요해지면 5.4의 Helm으로 넘어갈 것.

## 5.4 Helm으로 배포

로컬 검증용 클러스터가 없다면 [kind](https://kind.sigs.k8s.io/)로 하나 만든다 (별도 설치 없이
정적 바이너리 하나면 됨):

```bash
kind create cluster --name my-project

# 로컬에서 docker-compose로 이미 빌드한 이미지를 재사용하려면 태그를 맞추고 kind에 로드
docker tag ai_dev_framework-core-service:latest core-service:local
docker tag ai_dev_framework-bff-service:latest bff-service:local
docker tag ai_dev_framework-frontend:latest frontend:local
kind load docker-image core-service:local bff-service:local frontend:local --name my-project
```

배포:

```bash
helm install myproject ./helm/ai-dev-framework
kubectl get pods   # 전부 Running/Completed 될 때까지 대기
kubectl get jobs    # bff-service-migrate가 Complete인지 확인
```

로컬 확인 (포트포워딩):

```bash
kubectl port-forward svc/myproject-core-service 8080:80 &
kubectl port-forward svc/myproject-bff-service 8000:80 &
kubectl port-forward svc/myproject-frontend 3000:80 &
```

**같은 이름으로 여러 개 못 띄운다** — `helm install`의 첫 번째 인자(릴리스 이름)가 모든 리소스 이름의
접두어가 된다(`_helpers.tpl`). 같은 네임스페이스에 두 번째 프로젝트를 올리려면 다른 이름으로:
`helm install myproject2 ./helm/ai-dev-framework`.

업그레이드/롤백:

```bash
helm upgrade myproject ./helm/ai-dev-framework --set coreService.image.tag=v1.2.0
helm rollback myproject   # 직전 리비전으로
```

제거:

```bash
helm uninstall myproject
kind delete cluster --name my-project   # 로컬 테스트 클러스터였다면
```

## 5.5 dev / staging / prod 환경 오버레이

`values.yaml`이 기본값이고, `values-{dev,staging,prod}.yaml`이 환경별 차이만 담은 오버레이다.
`-f`로 겹쳐서 적용한다(뒤에 오는 파일이 우선):

```bash
# dev
helm install myproject-dev ./helm/ai-dev-framework -f helm/ai-dev-framework/values-dev.yaml

# staging — CI가 실제로 만든 이미지 태그로 --set 덮어쓰는 걸 권장
helm install myproject-staging ./helm/ai-dev-framework \
  -f helm/ai-dev-framework/values-staging.yaml \
  --set coreService.image.tag=<빌드 SHA/태그> \
  --set bffService.image.tag=<빌드 SHA/태그> \
  --set frontend.image.tag=<빌드 SHA/태그> \
  --set postgresql.password=<시크릿 매니저 값>

# prod
helm install myproject ./helm/ai-dev-framework \
  -f helm/ai-dev-framework/values-prod.yaml \
  --set coreService.image.tag=<릴리스 태그> \
  --set bffService.image.tag=<릴리스 태그> \
  --set frontend.image.tag=<릴리스 태그> \
  --set postgresql.password=<시크릿 매니저 값>
```

**`postgresql.password`는 절대 values 파일에 커밋하지 않는다.** `--set`으로 매번 넘기거나
`helm-secrets`/`sealed-secrets` 같은 도구로 관리할 것. `values-prod.yaml`은 이미
`coreService.extraEnv`에 `SPRING_PROFILES_ACTIVE=prod`를 넣어서 `DevAdminSeeder`(admin/admin1234
자동 생성)를 비활성화하도록 되어 있다 — 운영 관리자 계정은 별도 절차로 만들 것.

**관리형 DB로 옮기기** (RDS/Cloud SQL/Azure Database 등): `postgresql.enabled: false`로 끄고
`coreService.extraEnv`/`bffService.extraEnv`로 해당 DB 접속 정보(`DB_URL`/`DATABASE_URL` 등)를
직접 넣는다. core-service는 DB 벤더에 맞는 Spring 프로파일(`SPRING_PROFILES_ACTIVE`)도 같이
바꿔야 한다 — 3.4절 참고.

## 5.6 Ingress / 도메인

`values-{staging,prod}.yaml`의 `ingress.host`를 실제 도메인으로 바꾼다. 클러스터에
`ingress-nginx` 컨트롤러가 이미 떠 있다고 가정한다(`ingress.className: nginx`) — 플랫폼 차원에서
한 번만 설치해두면 되고, 프로젝트마다 새로 설치할 필요 없음. TLS는 `cert-manager`를 붙였다는 전제로
`values-prod.yaml`에 예시 annotation이 주석으로 남아있다.

## 5.7 CI/CD

지금 저장소에는 모바일용 GitHub Actions(`.github/workflows/mobile-ci.yml`)만 있다 — 웹
백엔드(core-service/bff-service)/프론트엔드용 CI는 아직 없다. 새로 만든다면 일반적인 흐름은:

1. PR/push 시 `core-service`(`./gradlew test`), `bff-service`(`pytest`), `frontend`
   (`npm run lint`, `npm run build`) 각각 검증
2. main 브랜치 push 시 세 이미지를 빌드해서 레지스트리(GHCR 등)에 `git sha`나 semver 태그로 푸시
3. `helm upgrade`에 그 태그를 `--set`으로 넘겨서 staging에 자동 배포, prod는 수동 승인 후 같은
   방식으로 배포

`mobile-ci.yml`이 이미 "왜 이렇게 짰는지"(플랫폼 스캐폴딩이 저장소에 없어서 CI가 그 자리에서
`flutter create`로 만든다는 점 등)를 주석으로 남겨뒀으니, 새 워크플로우를 짤 때 같은 톤으로 이유를
남겨두는 걸 권장한다 — 나중에 "왜 이렇게 했더라"를 다시 알아내는 비용이 제일 크다.

## 5.8 배포 전 체크리스트

- [ ] `SPRING_PROFILES_ACTIVE=prod` (또는 그에 준하는 설정)로 개발용 시드 계정 비활성화했는가
- [ ] JWT 서명 키를 고정 키로 바꿨는가 (`02-auth-and-rbac.md` 2.1, 2.6 참고 — 안 하면 배포마다 전체 로그아웃됨)
- [ ] DB 비밀번호 등 시크릿이 values 파일에 평문으로 커밋되지 않았는가
- [ ] CORS(`bff-service`)가 실제 프론트 도메인으로 좁혀졌는가
- [ ] Ingress host/TLS가 실제 도메인으로 설정됐는가
- [ ] `bff-service-migrate` Job이 매 배포마다 정상적으로 Complete 되는지 확인했는가
