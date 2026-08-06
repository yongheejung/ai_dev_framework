# 03. 프리셋·팀·워크플로우 연결 및 버전 정책

## 1. 책임 분리

```text
Preset UI metadata ──표현──┐
                           ▼
Job Template ──업무 계약/기본 입력/허용 Workspace
     ├─ Workflow ──단계/게이트/승인/도구
     └─ Agent Team ──역할 슬롯/담당 Agent
                         └─ Agent ──프롬프트/모델/도구/출력 스키마
```

| 구성요소 | 책임 | 포함하지 않는 것 |
|---|---|---|
| Preset UI | 카테고리, 위젯, 배치, 결과/승인 뷰 | 실행 규칙 |
| Job Template | 반복 업무 계약, 기본값, Workflow/Team 연결 | 노드 실행 로직 |
| Workflow | 단계, 의존관계, gate, loop, human, tool | 특정 팀원의 고정 배치 |
| Agent Team | 슬롯과 Agent 배치, 역할 책임 | 실행 순서 |
| Agent | 프롬프트, 모델 프로파일, 출력 스키마, 도구 | 업무 전체 흐름 |

## 2. 슬롯 기반 팀 교체

Workflow는 가능한 한 Agent ID가 아니라 `@slot`을 참조한다. 예:

```yaml
agent_id: "@writer"
```

Team은 슬롯에 실제 Agent를 배정한다.

```yaml
members:
  - slot: writer
    agent_id: document-writer
    role: 작성자
```

UI에서 Agent를 교체할 때 지켜야 할 검증:

1. Workflow가 요구하는 모든 슬롯이 Team에 존재한다.
2. 슬롯은 중복되지 않는다.
3. 배정 Agent가 존재한다.
4. Agent가 Workflow 노드가 요구하는 Tool을 사용할 수 있다.
5. Agent 출력 스키마가 노드의 후속 입력 계약과 호환된다.
6. Workspace 모델 정책과 실행 모드를 만족한다.

## 3. 프리셋 카테고리

카테고리는 탐색과 전용 뷰 선택을 위한 UI 분류이며 Core 실행 의미를 갖지 않는다.

| category | 기본 request view | 기본 result view | 초기 상태 |
|---|---|---|---|
| document | `document-request` | `document-result` | stable |
| development | `development-request` | `code-result` | stable, L2 확인 필요 |
| quant | `quant-request` | `quant-result` | experimental |
| video | `video-request` | `video-result` | optional |

하나의 카테고리에 여러 Job Template이 속할 수 있다. 예를 들어 development 아래에
source-analysis, backend-build, frontend-build를 둔다.

## 4. 버전 불변성

현재 Core는 `(kind, id, version)`을 불변으로 저장하고 같은 버전의 다른 내용을 거부한다.
이 정책을 유지한다.

### 규칙

1. 배포된 정의는 수정하지 않는다.
2. 내용 변경 시 version을 증가시킨다.
3. ID는 개념의 정체성이 바뀔 때만 새로 만든다.
4. UI 변경만 있을 때는 Preset UI metadata 버전만 증가시킬 수 있다.
5. 실행 의미가 바뀌면 관련 Core 정의 버전을 반드시 증가시킨다.
6. 버전 다운그레이드는 신규 publish로 처리하지 않는다.

## 5. 활성 버전과 참조

현재 런타임 Registry는 ID별 최신 로드 정의 하나를 사용한다. Job은 `template_version`을
기록하지만 시작 시점에 `definitions.job_templates.get(job.template_id)`로 현재 Template을
다시 조회한다. 따라서 Job 생성 후 Template이 바뀌면 기록된 version과 실행 시 사용 정의가
달라질 가능성이 있다.

P0 Core 보완에서 다음 권장안을 구현했다.

### 구현안: Job 생성 시 Template bundle snapshot 저장

Job 생성 시 다음을 저장한다.

- `template_snapshot`
- `workflow_ref: {id, version}`
- `team_ref: {id, version} | null`
- 선택적으로 `ui_ref`

Job 시작은 저장된 참조의 정확한 버전을 로드하고 Run snapshot에 넣는다. 이렇게 하면 Inbox에
오래 대기한 Job도 생성 당시 계약대로 실행된다.

### 대안

Job 시작 시 현재 정의로 재검증하고 사용자에게 “정의가 변경됨”을 알린 뒤 Job 입력을
마이그레이션한다. 개인용 초기 버전에는 복잡하므로 권장하지 않는다.

## 6. Run 재현성과 표시

Run 상세의 원본은 현재 Registry가 아니라 `workflow_snapshot`과 `configuration_snapshot`이다.

UI 표시 규칙:

- 과거 Run의 Team/Agent/Workflow 이름과 구성은 snapshot에서 읽는다.
- 현재 설정과 다른 경우 `실행 당시 vN · 현재 vM` 배지를 표시한다.
- 재실행은 두 동작을 구분한다.
  - **동일 설정으로 재실행**: snapshot 버전 bundle 사용
  - **현재 설정으로 새 작업**: 최신 Template으로 새 Job 생성

## 7. 변경 단위와 publish

팀 구성을 바꾸면 하나의 정의만 바뀌어도 연결 검증이 필요하다. 구성 UI는 다음 변경 세션을
하나의 bundle로 다룬다.

```text
Configuration Draft
├─ changed Agent definitions
├─ changed Team definition
├─ changed Workflow definition
├─ changed Job Template definition
└─ changed Preset UI definition
```

Publish 절차:

1. 최신 정의를 기준으로 draft 생성
2. 변경
3. 구조 검증
4. 참조/슬롯/도구/부작용/모델 정책 통합 검증
5. 변경 diff 확인
6. 각 변경 정의에 새 version 부여
7. bundle 원자 publish
8. 활성 버전 전환

현재 API는 개별 POST만 제공하므로 초기 구성 UI는 읽기 전용으로 두고, bundle validate/publish가
구현된 후 편집을 활성화한다.

## 8. 롤백

불변 이력을 삭제하거나 과거 레코드를 덮어쓰지 않는다.

롤백은 과거 payload를 복제하여 **더 높은 새 version**으로 publish한다.

예:

```text
team document-team v3에 문제 발생
→ v2 payload를 복제
→ document-team v4로 publish
→ 활성 버전을 v4로 전환
```

이 방식은 Core의 downgrade 거부 정책과 감사 이력을 모두 보존한다.

## 9. 호환성 수준

변경 화면은 diff에 다음 수준을 표시한다.

| 수준 | 예 | 처리 |
|---|---|---|
| UI only | 도움말, 필드 순서 | UI metadata만 배포 |
| Compatible | 선택 입력 추가, Agent 교체 | 새 버전 + 통합검증 |
| Migration required | 필수 입력 추가, 출력 키 변경 | 기존 Template 복제 또는 migration |
| Breaking | 슬롯 삭제, 노드 ID 변경, 승인 제거 | 새 Template ID 권장 |

특히 실행 중 재개는 node ID와 snapshot에 의존하므로 Workflow의 node ID 변경은 breaking으로
취급한다.

## 10. 일반 모드에서 허용할 설정

일반 사용자는 Job 실행 시 다음만 변경할 수 있다.

- Workspace/Project
- Template이 허용한 입력
- 실행 모드
- 제목, 설명, 우선순위

Team, Agent, Workflow를 Run 시작 화면에서 임시 교체하지 않는다. 실험적 교체가 필요하면
구성 모드에서 새 Team/Template 버전을 publish한다. 이 경계가 재현성과 문제 추적을 단순하게 한다.

## 11. Phase별 구성 기능

### Phase 1

- Template/Team/Agent/Workflow 관계 읽기 전용
- snapshot 기반 Run 표시
- 현재 버전과 실행 버전 표시

### Phase 2~3

- 프리셋 UI metadata 관리
- Template 복제
- 호환성 경고

### Phase 4

- Team 슬롯별 Agent 교체
- draft, validate, diff, publish
- 버전 이력과 롤백

### Phase 6

- Workflow 시각 편집
- 입력/출력 계약 연결 검사
- 실행 전 시뮬레이션과 회귀 평가

## 12. 구현 전 Core 수정 권고

1. ✅ Job에 Template/Workflow/Team과 전체 실행 설정 bundle snapshot 저장
2. 정의별 정확 버전 조회 API
3. configuration bundle 통합검증 API
4. Preset UI metadata 저장/조회
5. publish의 원자성 확보
6. 변경자 필드는 개인용으로 `local-user` 고정이라도 감사 메타데이터에 기록
