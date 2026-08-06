# 02. 프론트엔드–Core API 계약과 갭

## 1. 기본 계약

- Base URL: 로컬 기본값 `http://localhost:8000`
- 인증: `X-API-Key`
- API Key는 개인용 UI의 세션 메모리에만 보관한다. localStorage 영구 저장은 기본 비활성화한다.
- JSON 요청은 `application/json; charset=utf-8`
- 날짜는 UTC ISO 8601로 수신하고 UI에서 로컬 시간으로 표시한다.
- enum은 Core 문자열을 원본으로 유지한다.
- FastAPI의 `422 detail`을 필드 오류와 일반 계약 오류로 나눠 표시한다.
- SSE는 헤더 인증이 필요하므로 기본 `EventSource` 대신 fetch 기반 SSE 클라이언트를 사용한다.

## 2. 현재 API 활용표

| UI 기능 | 현재 API | 판단 |
|---|---|---|
| 시스템 상태 | `GET /health`, `/health/dependencies` | 사용 가능 |
| Workspace | `GET/POST /workspaces`, `GET /workspaces/{id}` | 초기 사용 가능 |
| Project | `GET/POST /projects`, `GET /projects/{id}` | 초기 사용 가능 |
| 프리셋 목록 | `GET /job-templates` | 사용 가능 |
| Team/Agent/Workflow 조회 | `GET /agent-teams`, `/agents`, `/workflows` | 사용 가능 |
| Job 생성/시작/취소 | `POST /jobs`, `POST /jobs/{id}/start`, `/cancel` | 사용 가능 |
| Job 목록/상세 | `GET /jobs`, `GET /jobs/{id}` | 소규모 사용 가능 |
| Run 상세 | `GET /runs/{id}` | 사용 가능 |
| Run 실시간 진행 | `GET /runs/{id}/stream` | 사용 가능, 재연결 보완 필요 |
| 협업 Turn | `GET /runs/{id}/collaboration-turns` | 사용 가능 |
| 승인함/피드백 | `GET /human-tasks/pending`, `POST /runs/{id}/feedback` | 사용 가능 |
| Knowledge 문서 | `GET/POST /knowledge/documents`, content PUT | 사용 가능 |
| Knowledge 검색 | `POST /knowledge/search` | 사용 가능 |
| Artifact 상세 | `GET /artifacts/{id}` | ID를 이미 아는 경우 가능 |
| 비용 | `GET /costs` | 사용 가능 |
| 설정 이력 | `GET /configuration-history/{kind}` | 원시 이력 조회 가능 |

## 3. Phase 1 필수 API 갭(P0)

구현 상태(2026-07-26): 아래 P0 항목은 Core에 반영되었다. 기존 `/jobs` 호환성을 유지하기
위해 UI용 페이지 조회는 `GET /jobs/page`로 제공한다.

### 3.1 Run 목록 조회

현재 공개 API에는 Run 목록이 없다. Job에 연결되지 않은 직접 Run, 복구 Run, 상태별 대시보드를
표현하기 어렵다.

구현:

```http
GET /runs?workspace_id=&project_id=&job_id=&status=&limit=&cursor=
```

응답은 상세의 node/LLM 호출을 제외한 요약 목록과 `next_cursor`를 반환한다.

### 3.2 UI용 Job 목록 필터와 페이지네이션

현재 `/jobs`는 Workspace와 단일 status만 지원하고 전체 배열을 반환한다.

`GET /jobs/page` 구현 필터:

- `project_id`
- `template_id`
- 복수 `status`
- `created_from`, `created_to`
- `query`
- `limit`, `cursor`

응답 형식은 `{items, next_cursor}`이며 기존 `GET /jobs` 배열 응답은 유지한다.

### 3.3 Artifact 목록과 다운로드

현재는 Artifact ID를 알아야 조회할 수 있고, 2MB가 넘으면 내용이 생략된다.

구현:

```http
GET /artifacts?workspace_id=&project_id=&job_id=&run_id=&content_type=&limit=&cursor=
GET /artifacts/{id}/content
```

`/content`는 원본 `Content-Type`, `Content-Disposition`을 갖는 스트리밍 응답이어야 한다.
Artifact metadata에 `run_id`, `node_id`, 사용자 표시명 또는 logical role을 추가하는 것을 권장한다.

### 3.4 UI 부트스트랩 조회

초기 화면이 여러 목록 API를 연속 호출하지 않도록 선택적 집계 API를 둔다.

```http
GET /ui/bootstrap?workspace_id=default
```

최소 응답:

- health summary
- active workspaces/projects
- enabled job templates
- execution modes
- pending approval count
- running/failed/recent job counts

이 API는 편의 계층이며 Core 도메인의 원본이 되어서는 안 된다.

### 3.5 프리셋 UI metadata

현재 `JobTemplateDefinition`에는 UI 표현 정보가 없다.

권장안:

- Core 모델에 선택 필드 `ui: dict[str, Any] | None`을 직접 넣지 않는다.
- 별도 `PresetUiDefinition`과 `GET /preset-ui`를 추가한다.
- `(template_id, template_version)`에 결합한다.
- metadata가 없으면 JSON Schema 기본 폼과 generic 결과 화면으로 동작한다.

별도 계층을 두면 Core 실행 모델이 프론트엔드 프레임워크에 종속되지 않는다.

### 3.6 SSE 재연결 계약

현재 SSE는 변경 이벤트만 보내고 이벤트 ID가 없다. 연결이 끊기면 누락 복원이 불가능하다.

구현된 보완:

- 각 이벤트에 단조 증가 `id`
- `Last-Event-ID` 또는 `after` 지원
- heartbeat 이벤트
- `end`에 최종 status 포함

Phase 1에서는 재연결 후 `GET /runs/{id}` 전체 동기화로 폴백할 수 있다.

## 4. Phase 2 필수 API 갭(P1)

### Knowledge

- Collection 목록/문서 수 집계
- 문서 상세
- 문서 삭제 또는 archive
- 업로드 진행/실패 상태
- 중복 문서 정책

권장:

```http
GET /knowledge/collections?workspace_id=
GET /knowledge/documents/{id}
DELETE /knowledge/documents/{id}
```

삭제는 첫 버전에서 영구삭제보다 archive를 우선한다.

### 승인 문맥

현재 Human Task는 message와 run 식별자 중심이다. UI가 승인 대상을 추측하지 않도록 다음
필드를 노드 정의 또는 Task 응답에 추가한다.

- `approval_kind`: document, code_write, quant_review, preview_render, final_render
- `subject_refs`: node output path 또는 artifact IDs
- `rejection_behavior`: revise, stop
- `risk_level`

### Artifact와 Run 연결

현재 Artifact metadata에 `job_id`는 있으나 `run_id`가 없다. 동일 Job 재실행 또는 향후 재시도를
구분하기 위해 `run_id`, `node_id`를 저장해야 한다.

## 5. 구성 모드 API 갭(P1/P2)

현재 POST 등록 API는 불변 `(kind, id, version)`을 보장하고 같은 버전의 다른 내용은 충돌시킨다.
좋은 기반이지만 편집 UI에는 다음이 부족하다.

```http
GET  /definitions/{kind}/{id}
GET  /definitions/{kind}/{id}/versions
GET  /definitions/{kind}/{id}/versions/{version}
POST /definitions/validate
POST /definitions/{kind}/{id}/clone
POST /configuration-bundles/validate
POST /configuration-bundles/publish
```

필요 기능:

- 저장 전 구조/참조/슬롯/Tool/Side Effect/Workspace 모델 정책 사전검증
- Team + Agent + Workflow + Template 묶음 검증
- 현재 활성 버전과 과거 버전 구분
- diff 응답
- draft와 publish 분리

현재 목록 API는 최신 활성 정의만, configuration-history는 모든 원시 버전을 반환하므로
구성 UI에서 직접 조합하지 말고 전용 조회 계약을 추가하는 편이 안전하다.

## 6. 프리셋별 데이터 계약

### 문서

- 요청: 현재 `document-job` 스키마로 시작 가능
- 추가 권장: output formats, length, tone, must_include, exclude
- 결과: Workflow output의 안정적인 `document`, `citations`, `issues`, `artifact_refs` 경로 필요

### 개발

- 요청: context_globs, output_dir, goal, acceptance criteria, test command
- 결과 표준화 권장:

```json
{
  "plan": {},
  "changes": [{"path": "", "diff": ""}],
  "tests": [{"command": "", "exit_code": 0, "stdout": "", "stderr": ""}],
  "reviews": [],
  "artifact_refs": []
}
```

### 퀀트

- 데이터 소스/기간/지표 입력 스키마를 명시
- 결과에 metrics, series, warnings, assumptions, recommendations를 안정적인 키로 제공
- 실제 거래 실행 도구는 계약 범위에서 제외

### 영상

- 자산 업로드 API와 media Artifact 역할 식별 필요
- 렌더 작업의 progress, preview, final을 구분
- 대용량 Artifact 스트리밍 다운로드 필수

## 7. 오류 표현

프론트엔드는 HTTP status만으로 사용자 메시지를 만들지 않는다.

권장 오류 봉투:

```json
{
  "error": {
    "code": "JOB_INPUT_SCHEMA_VIOLATION",
    "message": "입력값을 확인해 주세요.",
    "fields": [{"path": "inputs.goal", "message": "최소 3자입니다."}],
    "retryable": false,
    "details": {}
  }
}
```

기존 `detail` 문자열은 호환 유지하되 신규 UI API부터 구조화 오류를 제공한다.

## 8. 구현 우선순위

1. Run 목록, Job 필터/페이지네이션
2. Artifact 목록/다운로드
3. Preset UI metadata
4. SSE 복원 또는 상세 재동기화 규칙
5. 승인 문맥
6. Knowledge Collection
7. 구성 사전검증/버전 조회
8. 퀀트·영상 전용 계약
