# 6. AI 에이전트 연동 설계 (universal_ai_agent_orchestrator)

> **상태: 설계 문서 — 아직 구현 안 됨.** 여기 적힌 건 방향과 순서 합의를 위한 것이고, 실제 코드
> 작업은 이 문서 기준으로 phase별 승인을 받은 뒤 진행한다.

## 0. 배경과 원칙

기존에 `universal_ai_agent_orchestrator`(별도 저장소, `C:\workspace\universal_ai_agent_orchestrator`)가
이미 "자연어 명령 → 코드 작성 → 샌드박스 테스트 → 사람 승인" 루프(`code-build-job` 프리셋)를
갖고 있다. 이 프레임워크(AI Dev Framework)를 새로 뜯어고쳐서 같은 걸 다시 만들 필요는 없다.

**원칙: 오케스트레이터의 기존 프로세스(분석→생성→검증→승인)는 그대로 두고, 이 프레임워크를
오케스트레이터가 실제로 개발 작업을 수행하는 대상 코드베이스로 쓴다.** 새로 만드는 건 두 시스템을
잇는 얇은 연결부와, 오케스트레이터가 원래 안 하던 "승인된 결과를 실제 저장소에 반영하는" 마지막
한 걸음뿐이다.

이 문서는 어느 쪽 저장소를 건드리는 작업인지 절마다 명시한다 — 두 저장소를 오가며 작업하게
되므로 헷갈리기 쉽다.

## 1. 전체 흐름

```
[사람] "회원가입 시 환영 이메일 기능 추가해줘"
   │  (AI Dev Framework의 agent-tasks 화면, 지금 있는 UI 그대로 재사용)
   ▼
[bff-service] ──POST /jobs (template=code-build-job)──▶ [orchestrator API :8000]
   │                                                         │
   │  AgentTaskLog.status를 Run 상태에 맞춰 갱신               │  code-build-v1 워크플로우 실행
   │◀──SSE /runs/{id}/stream 또는 폴링───────────────────────┤  context → write → verify(샌드박스)
   │                                                         │       ↑              ↓
   │                                                         │       └── test_result ┘ (자가치유)
   │                                                         │  review → human 노드(HumanPause)
   ▼                                                         ▼
[사람] 승인/반려 (처음엔 오케스트레이터 자체 UI :3000에서)
   │
   ▼ (승인 시)
[신규] git 커넥터 ──▶ 로컬 checkout에 diff 적용 → 브랜치 생성 → 커밋 → GitHub PR
   │
   ▼
[사람] GitHub에서 PR 리뷰 후 merge (여기는 지금 그대로, 자동 머지 안 함)
```

굵게 "[신규]"라고 표시한 한 곳만 실제로 완전히 새로 짜는 부분이다. 나머지는 기존 오케스트레이터
API를 호출하는 얇은 클라이언트 코드다.

## 2. 컴포넌트별 변경 범위

### 2.1 universal_ai_agent_orchestrator 저장소 쪽

| 항목 | 무엇을 | 얼마나 큰 일인가 |
|---|---|---|
| 샌드박스 허용 명령 확장 | `app/config.py`의 `code_exec_allowed_commands`(기본값 `["pytest","python","python -m pytest","ruff","mypy"]`)에 `./gradlew test`, `npm run build` 등 추가 | **작음** — pydantic Settings 필드라 `.env`의 `APP_CODE_EXEC_ALLOWED_COMMANDS`로 코드 수정 없이 덮어쓸 수 있음 |
| 샌드박스 이미지에 Java/Node 빌드 환경 추가 | `docker/code-sandbox.Dockerfile`을 확장해서 기존 Python 도구 위에 JDK 21 + Gradle, Node를 같은 이미지에 얹는다(이미지가 프로세스당 1개뿐이라 통합 이미지가 유일한 선택지 — 아래 2.1.1) | **크다** — 아래 2.1.1 참고 |
| 소스 읽기 범위 | `.env`의 `APP_HOST_SOURCE_ROOT`/`APP_CODE_READ_ROOTS`를 AI Dev Framework 체크아웃 경로로 설정 | 작음 (설정값) |
| 포트 | `docker-compose.yml`의 `8000`(API)/`3000`(UI)이 우리 bff-service/frontend와 겹침 — 다른 값으로 remap | **작음** (사용자 판단과 일치) |
| [신규] 승인 후 git 저장 커넥터 | 아래 2.1.2 | **가장 큰 일** |

#### 2.1.1 왜 "JDK만 넣으면 끝"이 아닌가

`code-build-job` 문서(`GUIDE_DEV_TEAM_KO.md`)에 "샌드박스는 네트워크 차단"이라고 명시돼 있다.
실제로 겪은 사례도 있다 — 기본 `python:3.12-slim` 이미지에 pytest가 없어서 `exit_code: 127`이
났던 것. 즉 **verify 단계에 필요한 건 전부 이미지 빌드 시점에 미리 넣어야 한다.**

**추가로 확인한 제약 (코드 확인 완료) — 이미지는 프로세스당 1개뿐, Python용/Java용을 자동으로
나눠 쓸 수 없다.** `app/config.py:43`의 `code_exec_image`는 문자열 필드 하나이고,
`app/main.py:93`의 `code_executor = build_code_executor(settings)`가 API 프로세스 기동 시 **딱
한 번** 이 값으로 `DockerRunner`를 만들어 전역 싱글턴으로 쓴다(`app/sandbox.py:164`,
`build_docker_argv`가 매 실행마다 이 하나의 `image`를 그대로 씀). job_template이나 team 단위로
이미지를 바꿔 쓰는 기능은 없다. 그래서 core-service(Java)까지 지원하려면 선택은 둘 중 하나다:

- **(권장, 채택) 하나의 "뚱뚱한" 통합 이미지** — 지금 `docker/code-sandbox.Dockerfile`(Python +
  pytest/ruff/mypy) 위에 JDK 21 + Gradle(오프라인 캐시)을 같은 이미지에 얹는다.
  `code_exec_allowed_commands`에도 `pytest`류와 `./gradlew`류를 동시에 넣는다. JDK와 Python
  런타임은 서로 충돌하지 않으므로 한 이미지 안에 공존 가능 — **오케스트레이터 코어 코드 변경
  없음**, Dockerfile 확장 + `.env` 설정값 변경만으로 끝난다. bff-service(Python) 검증과
  core-service(Java) 검증 둘 다 같은 프로세스·같은 이미지로 처리된다.
- (기각) 이미지를 job/team별로 선택 가능하게 `CodeExecService`/`build_code_executor`를 확장하는
  것 — 더 유연하지만 오케스트레이터 코어(`app/sandbox.py`)를 건드려야 해서, 이 문서 0절의 원칙
  ("오케스트레이터는 범용 엔진으로 남기고, 얇은 연결부만 새로 만든다")과 맞지 않는다. 언어를 자주
  오가는 게 아니라면 통합 이미지로 충분.

`code.read`(컨텍스트 읽기)와 `code_exec_allowed_commands`(허용 명령)는 이미 완전히 언어
무관이다 — 전자는 glob/grep 기반 텍스트 도구라 `.java` content-type도 이미 매핑돼 있고
(`app/tools.py:235`), 후자는 `.env`로 덮어쓰는 리스트일 뿐이다. `context_globs`를
`["src/main/java/**/*.java"]`로, `test_command`를 `"./gradlew test"`로 바꾸는 정도면 되고, 이미
`code-build-backend-job.yaml`이 보여주는 패턴 그대로 `code-build-core-job.yaml`(Java 범위
프리셋)을 하나 더 만들면 된다 — **이것도 코드 변경 없이 YAML 하나 추가**로 끝나는 일이라 Phase D
와 별개로 먼저 만들어 둘 수 있다(이미지가 준비되기 전에는 `run` 단계에서 막힐 뿐 등록 자체는
가능).

Gradle은 첫 빌드 때 인터넷에서 의존성을 받아오는 게 기본 동작인데, 네트워크가 막힌 샌드박스
안에서는 그게 안 된다. 그래서:

1. 이미지 밖(빌드 스테이지)에서 core-service를 한 번 정상적으로 빌드해서 `~/.gradle/caches`를
   채운다.
2. 그 캐시 디렉터리를 샌드박스 이미지에 `COPY`한다.
3. 샌드박스 안에서 실행되는 `./gradlew test`는 `--offline` 플래그를 강제하거나
   `org.gradle.offline=true`를 `gradle.properties`에 넣어서 네트워크 접근 자체를 시도하지 않게
   한다.

Node/npm으로 frontend까지 확장하려면 같은 이유로 `node_modules`를 이미지에 미리 넣거나 npm
오프라인 캐시가 필요하다.

**유지보수 비용**: core-service의 `build.gradle.kts` 의존성이 바뀔 때마다 이 샌드박스 이미지도
다시 구워야 한다. 처음엔 수동으로 하고, 안정화되면 CI로 자동화하는 걸 권장.

#### 2.1.2 [신규] 승인 후 git 저장 커넥터

오케스트레이터 문서에 명시된 대로 **"승인해도 원본 저장소는 바뀌지 않는다 — 결과는 Artifact
저장소에 저장된다."** 이게 지금 오케스트레이터의 의도된 안전장치다. 여기에 실제 git 반영을
붙이는 건 에이전트에게 "코드베이스에 실제로 쓸 수 있는 권한"을 주는 것과 같으므로, 별도의 새
자동 승인 경로를 만들지 말고 **기존 승인 단계(human 노드, `POST /runs/{id}/feedback`)의 결과로
트리거**한다.

필요한 것:

- 오케스트레이터의 승인 이벤트를 받는 방법 — **확인 완료: webhook 없음.** `README.md`/
  `ARCHITECTURE_V04.md`에 webhook은 "다음 단계"로 명시돼 있고, `app/` 전체에 webhook 관련 코드가
  없다. 대신 `GET /human-tasks/pending`(전체 폴링)과 `GET /runs/{run_id}/stream`(SSE, 내부적으로도
  2초 간격 DB poll을 SSE로 변환하는 것뿐 — 진짜 push 아님)이 있다. 다만 SSE 스트림은
  `WAITING_HUMAN` 상태를 종료 이벤트로 취급해 스트림을 끊어버리므로(`app/main.py`
  `_TERMINAL_RUN_VALUES`), "승인 대기 진입"은 알려주지만 그 뒤 "승인됨"은 스트림이 이미 끝난
  뒤라 못 잡는다 — bff-service가 스트림 종료 후 별도로 재오픈하거나 `GET /runs/{id}`를 짧게
  폴링해서 최종 상태를 확인해야 한다. **권장**: `/human-tasks/pending` 전체 폴링 대신, Job 생성
  시점에 이미 아는 `run_id` 하나만 스트림으로 지켜보고 종료 후 그 run만 폴링하는 방식.
- 승인된 Run의 Artifact(diff)를 가져오는 API 호출 (`GET /artifacts/{id}/content` 등, 정확한
  스키마는 `code-build-job` 결과 계약 — `docs/ui/02_API_CONTRACT_AND_GAPS.md`의 "개발" 섹션
  `{plan, changes:[{path,diff}], tests, reviews, artifact_refs}` 참고)
- `changes[].diff`를 로컬 git 체크아웃에 적용 (`git apply`)
- 브랜치 생성 → 커밋 → push
- GitHub PR 생성 (PyGithub 또는 `gh` CLI 호출)
- PR 링크를 사람에게 다시 알림 (Slack/Telegram, 또는 처음엔 그냥 오케스트레이터/우리 UI에 표시)

**어디에 둘지는 아직 미정 — 결정 필요**:

| 옵션 | 장점 | 단점 |
|---|---|---|
| 오케스트레이터 저장소 안 (예: `app/agents/git_connector.py`) | 오케스트레이터의 승인 이벤트에 바로 훅 걸기 쉬움 | 오케스트레이터가 "AI Dev Framework 전용" 로직을 알게 됨 — 범용성 훼손 |
| AI Dev Framework의 bff-service 안 (`app/agents/`) | 프레임워크가 자기 코드에 대한 책임을 스스로 짐, 다른 타겟 프로젝트에도 재사용 가능 | 오케스트레이터의 승인 이벤트를 폴링 등으로 별도로 감지해야 함(웹훅이 없다면) |

지금 판단으로는 **bff-service 쪽 권장** — 오케스트레이터는 범용 엔진으로 남기고, "이 결과를
GitHub에 반영한다"는 타겟 프로젝트별 정책은 타겟 프로젝트(AI Dev Framework)가 갖는 게 결합도가
낮다. **웹훅은 없는 것으로 확인됨** — SSE 스트림(최대 ~2초 지연) + 스트림 종료 후 짧은 폴링
조합으로 감지 지연을 최소화한다(위 열린 질문 1 참고). 순수 폴링보다는 확실히 빠르다.

### 2.2 AI Dev Framework 저장소 쪽 (이 저장소)

| 항목 | 상태 |
|---|---|
| AI가 참조할 코딩 표준 | ✅ 이미 있음 — `AGENTS.md` (오케스트레이터의 `context` 단계에 주입할 자료로 그대로 쓸 수 있음) |
| 새 기능 추가 패턴 | ✅ 이미 있음 — `docs/04-adding-a-feature.md` (write 단계가 따라갈 템플릿) |
| 응답 포맷/에러 처리 표준 | ✅ 이미 있음 — 표준 `ApiResponse`, `GlobalExceptionHandler` |
| 테스트 명령 | ✅ 이미 있음 — `./gradlew test`(core), `pytest`(bff), `npm run lint && npm run build`(frontend) — verify 단계가 그대로 실행하면 됨 |
| [신규] 오케스트레이터 API 클라이언트 | `bff-service/app/agents/orchestrator_client.py` — `X-API-Key`(`ORCHESTRATOR_API_KEY` 환경변수, 절대 브라우저에 노출 안 함)로 `POST /jobs`, `/jobs/{id}/start`, `GET /runs/{id}` 등 호출 |
| [신규] `agent-tasks`를 실제 위임으로 연결 | 지금 `AgentTaskLog`는 DB에 기록만 하는 데모다. 생성 시 오케스트레이터에 실제로 Job을 위임하고, `status`를 Run 상태와 동기화하도록 확장 |
| [신규] `.env` | `ORCHESTRATOR_BASE_URL`, `ORCHESTRATOR_API_KEY` 추가 |

## 3. 단계별 롤아웃 순서 (제안)

**Phase A — 수동 검증 ✅ 완료 (2026-08-06), 파이프라인/로직 정상 확인**
오케스트레이터의 `code-build-job`을 AI Dev Framework의 bff-service 경로(`APP_HOST_SOURCE_ROOT`,
`docker-compose.dev.yml` 오버레이)에 대해 API로 직접 돌려봤다. 결과:

- **파이프라인 자체는 문제 없음** — Job 생성 → 노드 그래프 진행(`code.read` context/spec 파싱) →
  `write`(에이전트) → `verify`(`code.exec`, docker.sock 경유 실제 샌드박스 실행) → `review`
  (verify 결과·파일을 근거로 판정) → `approve`(human 노드, `WAITING_HUMAN`으로 정확히 정지)까지
  오류 없이 끝까지 흘렀고, 노드 간 데이터 전달도 정확했다(review가 verify의 실제 `exit_code`를
  근거로 CRITICAL/HIGH를 정확히 짚음).
- **로컬 모델(qwen3:8b, CPU-only) 품질은 이번엔 범위 밖** — 이 PC에 NVIDIA GPU가 없어(Intel 내장
  그래픽뿐, `model_endpoints.yaml`의 `accelerator: nvidia-gpu` 라벨은 실제와 불일치) CPU 추론만
  가능했고, 결과물 품질 저하(요청과 무관한 내용 생성)가 있었다. 이건 하드웨어 제약으로 갈음하고
  로직 검증과는 분리해서 판단.
- **부수적으로 발견해 고친 기존 버그 2건**(오늘 변경과 무관한 사전 존재 이슈, 최신 소스로 재빌드하며
  드러남):
  1. `examples/agents/code-writer.yaml`/`code-reviewer.yaml` — 내용은 바뀌었는데 `version`을 안
     올려서 DB의 기존 정의와 충돌(`DefinitionVersionConflict`). 버전 2→3으로 올려 해결.
  2. `video.montage` 도구가 `APP_MEDIA_INPUT_ROOTS`가 비어 있으면 등록 안 되는데, 그걸 참조하는
     워크플로우가 있어 시작 자체가 막힘. 더미 경로로 채워 해결.
- **타임아웃 조정**: `config/model_endpoints.yaml`의 `windows-ollama` `timeout_sec`을 300 → 1200으로
  올림(CPU 추론이 300초 안에 안 끝남). GPU 호스트로 옮기면 낮춰도 됨.

CLI/웹 UI 대신 API를 직접 호출했고("정말 되는지" 확인이 목적이라 UI는 생략), 기존 Python 샌드박스
이미지를 그대로 못 쓰고 `docker/code-sandbox.Dockerfile`을 빌드해야 했던 점, `.env`가 디스크에
없어서 복원해야 했던 점은 이 저장소 자체의 로컬 운영 이슈였고 워크플로우 설계와는 무관.

> **범위 주의(코드 확인 완료)**: `examples/workflows/code_build.yaml`의 `verify`(code.exec) 노드는
> `$nodes.write.files` — 즉 `@coder`가 이번에 새로 쓴 파일만 격리 샌드박스에 주입한다. bff-service
> 기존 코드베이스 전체가 마운트되는 게 아니다. `context`(code.read)는 작성자에게 읽기 참고자료로만
> 최대 40개 파일을 보여줄 뿐 실행 환경엔 들어가지 않는다. 따라서 Phase A의 첫 시도는 기존 모듈을
> import하지 않는 **완전히 독립적인 함수 하나**로 목표를 좁혀서 돌려볼 것 — 기존 서비스 로직을
> 수정하는 목표를 주면 의존 파일이 없어 `pytest`가 `ImportError`로 실패할 가능성이 높다. 이 한계가
> Phase C(git 커넥터, diff를 실제 체크아웃에 적용)에서 어떻게 완화되는지도 같이 설계해야 한다 —
> diff 적용 후에는 로컬 체크아웃 전체를 대상으로 실제 `pytest`를 한 번 더 돌리는 검증 스텝이
> 필요할 수 있다(오케스트레이터 샌드박스가 아니라 우리 쪽 CI에서).

**Phase B — REST 연동 ✅ 완료 (2026-08-06)**
`orchestrator_client.py`(`create_job`/`start_job`/`get_job`) + `agent-tasks` 확장
(`POST /agent-tasks`가 생성 즉시 위임, `POST /agent-tasks/{id}/sync`로 상태 동기화, 위임 실패는
요청을 실패시키지 않고 `status=DELEGATION_FAILED`+`delegation_error`로 남김). 실제 오케스트레이터
API로 E2E 검증 완료 — 진짜 작업을 생성해 실제 `job_id`/`run_id`를 받고, `QUEUED`→`RUNNING`이
오케스트레이터 쪽 기록과 정확히 일치하는 것까지 확인, 마지막에 취소로 정리. 유닛 테스트
4건(`test_orchestrator_client.py`) 포함 bff-service 전체 스위트 통과. **승인은 여전히 오케스트레이터
자체 UI에서** — git 반영은 아직 없음(Phase C).

**Phase C — git 저장 커넥터 (여기서부터 실제로 코드가 저장소에 반영됨)**
2.1.2절. 이 단계부터는 에이전트가 실제 GitHub 저장소에 쓰기 시작하므로, 처음엔 이 커넥터를 좁은
범위(예: bff-service 폴더만)에만 켜두고 며칠 지켜본 뒤 넓히는 걸 권장.

**Phase D — 샌드박스 Java 확장 (core-service까지 대상 확대)**
2.1.1절. Gradle 오프라인 캐시 작업이 있어서 별도 소요 예상 — Phase C가 안정된 뒤 진행.

**Phase E — 유지보수 파이프라인 ("2단계 AI 에이전트 연계.docx" 반영)**

원문서(루트의 `2단계 AI 에이전트 연계.docx`)는 "LangGraph/CrewAI로 새로 구축"을 전제하는데, 이건
그대로는 안 된다 — `README.md`에 CrewAI/LangGraph Runtime은 "미설치, 지정 시 워크플로우 등록
단계에서 거부"라고 명시돼 있다. 대신 문서가 원하는 동작(컨텍스트 주입→생성→샌드박스 검증→
self-healing 재수정→사람 승인)은 `code-build-v1`의 `revise_cycle` 루프가 **이미 그대로 구현하고
있다.** 항목별 대조:

| 원문서 항목 | 상태 |
|---|---|
| 컨텍스트 주입(코딩표준 상시 제공) | ✅ 이미 있음(`AGENTS.md`+`code.read`) |
| Trivy/Dependabot 감지 → AI 호출 | ✅ 코어 변경 없음 — GitHub Actions가 `POST /jobs`만 호출(오케스트레이터 밖→안 방향이라 "웹훅 없음" 제약과 무관). `goal`에 CVE 설명만 채우면 기존 `code-build-job`을 그대로 호출해도 됨 — 전용 job_template은 선택사항 |
| 테스트 실패 시 self-healing 재수정 | ✅ 이미 있음, 코드 변경 0 — `revise_cycle`(`max_iterations`) |
| **[신규 갭, 코드 확인 완료]** self-healing이 "기존 저장소 전체" 기준으로 동작해야 함 | ❌ 지금 구조로는 안 됨 — 아래 참고, 진짜 코드 변경 필요한 유일한 항목 |
| Telegram/Slack 승인 알림 | ✅ 가능, 신규 얇은 커넥터(웹훅 없어 폴링/SSE 필요 — 2.1.2절) |
| 승인 시 main 자동 병합 + 자동 배포 | ⚠️ **[정정]** 원문서는 ArgoCD를 가정하지만 이 프레임워크의 실제 배포 도구는 `docs/05-deployment.md` 기준 **Helm**(ArgoCD 아님). 방향 자체는 합의됨(사람 승인 → 자동배포, 문제 시 롤백) — 아래 "자동배포·롤백" 참고 |

**신규 갭 상세 — `code.exec`는 "새로 쓴 파일"만 검증하지 "기존 저장소" 전체를 검증하지 않는다.**
`examples/workflows/code_build.yaml`의 `verify` 노드는 `files: $nodes.write.files`만 격리
샌드박스에 스테이징한다(`app/sandbox.py`의 `CodeExecService.run`도 `files` 인자만 받아 임시
디렉터리에 풂 — 기존 저장소를 마운트하는 경로가 없음). "완전히 새로운 독립 함수 작성"에는 문제
없지만(Phase A가 검증할 시나리오), **유지보수 시나리오(예: `build.gradle.kts`의 라이브러리
버전만 올리고 저장소 전체가 여전히 컴파일·테스트되는지 확인)에는 구조적으로 안 맞는다** — 에이전트가
수정한 파일 하나만 빈 디렉터리에 던져놓고 `./gradlew test`를 돌리면 나머지 소스가 없어 무조건
실패한다. `code.read`의 스냅샷 상한(`max_files: 40`, `max_total_chars: 40000`)도 실제 저장소
전체를 LLM 왕복으로 우회하기엔 너무 작다.

해결하려면 `code.exec`(또는 새 tool)가 `code_read_roots`의 실제 파일을 샌드박스 스테이징
디렉터리에 먼저 깔고, 그 위에 `write.files`를 오버레이해서 실행하도록 확장해야 한다 — 이건
"오케스트레이터 코어를 안 건드린다"는 원칙에서 유일하게 벗어나는, 그러나 유지보수 파이프라인이
실제로 동작하려면 꼭 필요한 항목이다. 워크플로우의 4단계 루프 *형태*(작성→검증→리뷰→승인)는
그대로 두고, `verify` 노드 하나의 스테이징 방식만 넓히는 좁은 범위의 변경.

**자동배포·롤백 (합의된 방향 + 전제조건)**

"사람이 승인하면 자동배포하고, 문제 생기면 롤백"이라는 방향 자체는 이미
`docs/05-deployment.md` §5.7이 그리고 있던 CI 패턴(main push 시 staging 자동배포, prod는 수동
승인 후 배포)과 일치한다 — 새로운 리스크 모델이 아니다. 다만 실제 안전망이 되려면 순서가 중요:

1. **선행 조건 — 승인 시점의 근거를 먼저 강화한다.** 위 "신규 갭"(`code.exec`가 전체 저장소
   기준으로 검증하지 않는 문제)을 안 고치면, 사람이 승인한 diff가 실제로는 전체 저장소 기준
   검증이 안 된 채로 배포까지 갈 수 있다. 롤백은 최후 수단이지 검증 부실을 상쇄하는 장치가
   아니므로, ① `code.exec` 검증 범위 확장 → ② 승인 → ③ Helm 자동배포 → ④ 헬스체크/롤백 순서를
   지킨다.
2. **롤백은 자동 발동이 아니다.** `helm rollback myproject`(05-deployment.md §5.4)는 명령
   자체는 빠르지만 사람이 실행해야 한다. 배포 직후 자동 헬스체크(readiness 실패·에러율 급증 시
   Slack/Telegram 즉시 알림)가 없으면 결국 사람이 계속 지켜보고 있어야 하므로, 최소한 헬스체크
   실패 알림은 자동배포와 세트로 필요.
3. **범위를 좁게 시작한다.** 이 자동배포 권한은 처음부터 전체(신규 기능 생성 등)에 열지 말고,
   원문서 3단계가 의도한 좁은 범위(의존성 버전업 등 기계적 패치)에만 먼저 적용 — 지금까지의
   Phase 순서 원칙과 동일. staging은 (오케스트레이터 승인 → Helm 자동배포 → 헬스체크 실패 시
   알림+수동 롤백), prod는 05-deployment.md가 이미 그려둔 대로 별도 사람 승인 단계를 하나 더
   둔다.

## 4. 열린 질문 (진행 전에 답이 필요함)

1. ~~오케스트레이터가 Run 승인 이벤트에 대한 **웹훅**을 지원하는가~~ **[해결됨]** 웹훅 없음.
   `run_id` 단위 SSE 스트림(`/runs/{id}/stream`) + 스트림 종료(WAITING_HUMAN) 후 짧은 폴링 조합으로
   감지. 상세는 2.1.2절.
2. ~~git 저장 커넥터를 어느 저장소에 둘지~~ **[결정됨]** bff-service 쪽, **ai-dev-framework
   전용으로 좁게** 만든다. 기존 프로젝트(WMS, stock_advisor)는 이번 파이프라인의 대상이 아니고
   지금 방식(오케스트레이터의 `source-analysis-job`/`code-build-job`을 직접 호출, git 반영은
   사람이 수동으로) 그대로 유지한다. 앞으로 만들 신규 프로젝트만 (a) ai-dev-framework를 뼈대로
   이번 파이프라인을 쓰거나 (b) 프레임워크 없이 오케스트레이터 기존 흐름만 쓰는 두 경로 중 택1.
   범용 추상화(타겟 저장소를 job_template 입력값으로 파라미터화 등)는 지금 설계하지 않는다 —
   WMS/stock_advisor를 실제로 이 파이프라인에 편입할 필요가 생기는 시점에 그때 뽑아낸다.
3. GitHub 쓰기 인증 방식 — GitHub App(세분화된 권한, 권장) vs PAT. 커넥터가 실제로 브랜치를 만들고
   PR을 올리므로 이 저장소에 한정된 최소 권한으로 발급해야 함.
4. `code_exec_allowed_commands`에 `./gradlew`류 명령을 추가할 때, 샌드박스 안에서 core-service
   전체가 아니라 **필요한 모듈만** 빌드하게 제한할 방법이 있는지 (빌드 시간/리소스 문제)
5. 두 저장소가 독립적으로 버전 관리되는데, 오케스트레이터 쪽 정의(YAML) 변경 규율(`CLAUDE.md`의
   "version-bump discipline")과 이 프레임워크의 변경을 어떻게 맞물려 릴리스할지

## 5. 다음 행동

Phase A(수동 검증)부터 시작하는 걸 추천 — 코드 변경이 전혀 없고, 지금까지의 설계가 실제로
맞는지 가장 빠르게 확인할 수 있는 단계다.
