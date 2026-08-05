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
| 샌드박스 이미지에 Java/Node 빌드 환경 추가 | `docker/code-sandbox.Dockerfile`을 확장해서 JDK 21 + Gradle, Node를 넣는다 | **크다** — 아래 2.1.1 참고 |
| 소스 읽기 범위 | `.env`의 `APP_HOST_SOURCE_ROOT`/`APP_CODE_READ_ROOTS`를 AI Dev Framework 체크아웃 경로로 설정 | 작음 (설정값) |
| 포트 | `docker-compose.yml`의 `8000`(API)/`3000`(UI)이 우리 bff-service/frontend와 겹침 — 다른 값으로 remap | **작음** (사용자 판단과 일치) |
| [신규] 승인 후 git 저장 커넥터 | 아래 2.1.2 | **가장 큰 일** |

#### 2.1.1 왜 "JDK만 넣으면 끝"이 아닌가

`code-build-job` 문서(`GUIDE_DEV_TEAM_KO.md`)에 "샌드박스는 네트워크 차단"이라고 명시돼 있다.
실제로 겪은 사례도 있다 — 기본 `python:3.12-slim` 이미지에 pytest가 없어서 `exit_code: 127`이
났던 것. 즉 **verify 단계에 필요한 건 전부 이미지 빌드 시점에 미리 넣어야 한다.**

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

- 오케스트레이터의 승인 이벤트를 받는 방법 — webhook이 있는지, 아니면 우리 쪽에서
  `/human-tasks/pending` → 승인됨을 폴링으로 감지해야 하는지 확인 필요 (오케스트레이터 코드베이스
  추가 조사 필요, 이 문서 작성 시점엔 미확인)
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
낮다. 다만 오케스트레이터가 웹훅을 지원하는지에 따라 폴링 지연이 걸릴 수 있음 — 확인 필요.

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

**Phase A — 수동 검증 (코드 변경 없음)**
오케스트레이터의 `code-build-job`을 AI Dev Framework의 bff-service 경로에 대해 CLI/웹 UI로 직접
한 번 돌려본다. 기존 Python 샌드박스 그대로 쓰면 되므로 새 작업이 전혀 없다 — "정말 되는지"부터
먼저 눈으로 확인.

**Phase B — REST 연동 (AI Dev Framework 쪽만)**
`orchestrator_client.py` + `agent-tasks` 확장. Job 생성/시작/상태 조회까지만. **승인은 여전히
오케스트레이터 자체 UI에서** — git 반영은 아직 없음.

**Phase C — git 저장 커넥터 (여기서부터 실제로 코드가 저장소에 반영됨)**
2.1.2절. 이 단계부터는 에이전트가 실제 GitHub 저장소에 쓰기 시작하므로, 처음엔 이 커넥터를 좁은
범위(예: bff-service 폴더만)에만 켜두고 며칠 지켜본 뒤 넓히는 걸 권장.

**Phase D — 샌드박스 Java 확장 (core-service까지 대상 확대)**
2.1.1절. Gradle 오프라인 캐시 작업이 있어서 별도 소요 예상 — Phase C가 안정된 뒤 진행.

**Phase E — 선택 사항**
Slack/Telegram 승인 알림 레이어, "2단계 AI 에이전트 연계" 문서의 3단계(Trivy/Dependabot 감지 →
자동 패치 → ArgoCD 배포)까지 확장.

## 4. 열린 질문 (진행 전에 답이 필요함)

1. 오케스트레이터가 Run 승인 이벤트에 대한 **웹훅**을 지원하는가, 아니면 폴링으로 감지해야 하는가?
   (2.1.2절 — 오케스트레이터 코드베이스 추가 조사 필요)
2. git 저장 커넥터를 어느 저장소에 둘지 (2.1.2절 표 — 잠정 권장: bff-service 쪽)
3. GitHub 쓰기 인증 방식 — GitHub App(세분화된 권한, 권장) vs PAT. 커넥터가 실제로 브랜치를 만들고
   PR을 올리므로 이 저장소에 한정된 최소 권한으로 발급해야 함.
4. `code_exec_allowed_commands`에 `./gradlew`류 명령을 추가할 때, 샌드박스 안에서 core-service
   전체가 아니라 **필요한 모듈만** 빌드하게 제한할 방법이 있는지 (빌드 시간/리소스 문제)
5. 두 저장소가 독립적으로 버전 관리되는데, 오케스트레이터 쪽 정의(YAML) 변경 규율(`CLAUDE.md`의
   "version-bump discipline")과 이 프레임워크의 변경을 어떻게 맞물려 릴리스할지

## 5. 다음 행동

Phase A(수동 검증)부터 시작하는 걸 추천 — 코드 변경이 전혀 없고, 지금까지의 설계가 실제로
맞는지 가장 빠르게 확인할 수 있는 단계다.
