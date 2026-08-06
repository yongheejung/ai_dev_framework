# 01. UI 정보구조와 화면 명세

## 1. 설계 원칙

### 일반 모드와 구성 모드를 분리한다

- **일반 모드**: 프리셋 선택, 입력, 실행, 진행 확인, 승인, 결과물 확인
- **구성 모드**: Team/Agent/Workflow/Template 조회 및 버전형 변경

일상 화면에는 Agent 프롬프트, Workflow 노드 JSON, 모델 엔드포인트 같은 설정을 노출하지
않는다. 사용자는 필요할 때만 구성 모드로 전환한다.

### 공통 골격과 프리셋 전용 뷰를 분리한다

네 프리셋 모두 Job/Run/Human Task/Artifact 생명주기는 공유한다. 요청 폼, 결과 뷰어,
승인 문맥만 다르게 구성한다.

```text
App Shell
├─ Dashboard
├─ New Job
│  └─ PresetRenderer
├─ Jobs
│  └─ Job/Run Detail
│     ├─ CommonTimeline
│     ├─ PresetResultView
│     └─ ApprovalPanel
├─ Approvals
├─ Knowledge
├─ Artifacts
└─ Configuration
   ├─ Presets
   ├─ Teams
   ├─ Agents
   └─ Workflows
```

## 2. 전역 탐색 구조

| 메뉴 | 주요 목적 | Phase |
|---|---|---|
| 홈 | 상태와 오늘 할 일 파악 | 1 |
| 새 작업 | 프리셋을 선택해 Job 생성 | 1 |
| 작업 | Job/Run 목록과 상세 | 1 |
| 승인함 | Human Task 검토 및 피드백 | 1 |
| 지식 | 문서 적재·검색·Collection 관리 | 2 |
| 결과물 | Artifact 검색·미리보기·다운로드 | 2 |
| AI 팀 설정 | Team/Agent 배치와 버전 변경 | 4 |
| 작업 절차 | Workflow 읽기/검증/고급 편집 | 4/6 |
| 환경 설정 | 모델·실행 모드·상태 | 4 |

Workspace와 Project는 독립 메뉴보다 상단 전역 선택기로 둔다. 선택된 Workspace가 모든
목록·프리셋·지식·결과물의 범위를 결정하고, Project는 선택 필터다.

## 3. 공통 화면

### 3.1 홈

표시:

- API, PostgreSQL, Ollama/모델 상태
- 실행 중, 승인 대기, 실패, 완료 작업 수
- 최근 작업
- 승인 대기 바로가기
- 최근 7일 토큰/비용 요약
- 프리셋 빠른 시작 카드

상태 조회 실패와 “실행 결과 없음”을 구분한다. API 장애 시 생성/승인 동작을 비활성화한다.

### 3.2 새 작업

1. 네 개의 큰 카테고리 카드 선택
2. 해당 카테고리의 Job Template 선택
3. Workspace/Project 확인
4. 스키마 기반 입력 및 프리셋 전용 필드 입력
5. 실행 모드·제목·우선순위 설정
6. Job 생성
7. 입력 요약 확인 후 Job 시작

`POST /jobs`와 `POST /jobs/{id}/start`를 분리해 생성 후 검토 가능하게 한다. 한 번에
“생성하고 시작”하는 UI를 제공하더라도 내부적으로 두 API를 순차 호출한다.

### 3.3 작업 목록

필터:

- Workspace, Project
- 프리셋 카테고리/Template
- 상태
- 기간
- 제목 검색

행 표시:

- 제목, 프리셋, 상태, 우선순위
- 생성/갱신 시각
- Run 진행 상태
- 승인 대기 여부
- 최종 결과물 존재 여부

### 3.4 Job/Run 상세

공통 영역:

- Job 메타데이터와 입력
- 현재 상태와 오류 요약
- Workflow 노드 타임라인
- Agent/Tool 실행 기록
- 협업 Turn
- 토큰·지연·비용
- Human Task
- Artifact
- 실행 당시 설정 스냅샷

실시간 표시는 `GET /runs/{run_id}/stream`을 사용한다. SSE가 종료되거나 끊어지면
`GET /runs/{run_id}`로 최종 상태를 재동기화한다.

### 3.5 승인함

승인 카드에는 최소 다음을 보여준다.

- 작업 제목과 프리셋
- 승인 노드 메시지
- 승인 대상 결과 요약
- 관련 Artifact/코드 diff/테스트/렌더 미리보기
- 만료 시각
- 승인 또는 반려 의견

`approve: false`의 의미가 Workflow별로 “수정 루프” 또는 “종료”일 수 있으므로 버튼 문구를
고정하지 않는다. Workflow/UI metadata에서 `반려 후 수정` 또는 `반려 후 종료`를 표시한다.

### 3.6 구성 탐색기

첫 구현은 읽기 전용이다.

- Template → Workflow/Team 연결
- Team → 슬롯/Agent 연결
- Workflow → 노드/필요 슬롯/Tool/부작용 수준
- Agent → 모델 프로파일/도구/출력 스키마
- 현재 버전과 과거 버전

## 4. 프리셋별 화면 계약

### 4.1 문서작성팀

요청:

- 목표, 문서 종류, 대상 독자
- Knowledge Collection과 참고 문서
- 지시사항, 분량, 문체, 필수/제외 항목
- 출력 형식

진행:

- 근거 검색 → 초안 → 비평 → 수정 → 승인 → 저장
- 검색된 근거와 인용 커버리지 표시

결과:

- Markdown/HTML 문서 미리보기
- 주장 유형(FACT/INFERENCE/RECOMMENDATION/UNKNOWN)
- 인용 근거, reviewer 이슈, 보존 항목
- DOCX/PDF 등 Artifact

승인:

- 문서 전체 미리보기와 미해결 이슈를 함께 표시
- 수정 의견을 구조화하지 못할 경우 자유 텍스트로 전달

### 4.2 시스템 개발팀

요청:

- 작업 유형: 분석/기능/버그/리팩터링/테스트
- 대상 소스 범위, 읽기/쓰기 범위
- 요구사항과 완료 조건
- 테스트 명령과 기술 제약
- 실제 파일 저장 여부

진행:

- 소스 분석 → 계획 → 생성 → L2 샌드박스 테스트 → 리뷰 → 승인 → 저장

결과:

- 변경 계획
- 파일별 before/after 또는 unified diff
- 테스트 명령, exit code, stdout/stderr
- 코드/보안 리뷰와 위험
- 생성 Artifact와 실제 저장 대상

승인:

- 코드 저장 전 별도 중요 확인
- 대상 경로, diff, 테스트 결과가 없으면 승인 버튼 비활성화

### 4.3 퀀트 자문팀

요청:

- 요청 유형: 성과 진단/리스크/개선 후보/파이프라인 감사
- 데이터 소스, 전략, 분석 기간, 벤치마크
- 비용/슬리피지, IS/OOS 구간, 핵심 지표
- 위험 한도와 가정

진행:

- 데이터 확인 → 성과 분석 → 실행 리스크 → ML 무결성 → OOS 게이트 → 자문안

결과:

- 지표 카드와 시계열/낙폭 차트
- 데이터 품질과 누수·과최적화 경고
- 검토자별 판단
- 사실/가정/불확실성/개선 제안

승인:

- “자문 결과 확인”이며 주문 실행이나 전략 자동 배포와 연결하지 않는다.
- e2e 검증 완료 전 UI에 `실험적` 배지를 표시한다.

### 4.4 동영상 제작팀

요청:

- 영상 목적, 플랫폼, 화면비, 해상도, 길이
- 대본/주제와 이미지·영상·음원 자산
- 장면, 자막, 브랜드, 출력 옵션

진행:

- 기획 → 대본 → 스토리보드 → 자산 점검 → 미리보기 렌더 → 승인 → 최종 렌더

결과:

- 대본과 장면 목록
- 사용 자산과 누락 경고
- 저해상도 미리보기
- 렌더 로그와 최종 영상 Artifact

승인:

- 미리보기 승인과 최종 렌더 승인을 구분할 수 있어야 한다.
- 초기에는 타임라인 편집기가 아니라 장면별 수정 의견만 지원한다.

## 5. 폼/결과 확장 구조

`input_schema`는 데이터 계약이고 `ui_schema`는 표현 계약이다. Core의 JSON Schema를
프론트엔드가 임의로 재정의하지 않는다.

```ts
type PresetUiDefinition = {
  schemaVersion: 1;
  category: "document" | "development" | "quant" | "video";
  icon: string;
  requestView: string;
  resultView: string;
  approvalView: string;
  fieldOrder?: string[];
  fields?: Record<string, {
    widget?: string;
    label?: string;
    help?: string;
    section?: string;
    advanced?: boolean;
  }>;
};
```

기본 위젯은 text, textarea, select, number, boolean, date, file을 제공한다. 특수 위젯은
`knowledge-collection`, `source-scope`, `test-command`, `date-range`, `metric-selector`,
`media-assets`로 등록한다.

알 수 없는 위젯은 오류로 중단하지 않고 JSON Schema 기본 위젯으로 폴백한다.

## 6. Phase 1 화면 완료 조건

다음 사용자 여정이 한 번에 성공해야 한다.

```text
홈에서 상태 확인
→ 프리셋 선택
→ Job 입력 및 생성
→ 실행 시작
→ SSE로 노드 진행 확인
→ 승인함에서 결과 검토
→ 승인 또는 반려
→ 최종 상태와 Artifact 확인
```
