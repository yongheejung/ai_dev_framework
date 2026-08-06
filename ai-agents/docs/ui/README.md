# 개인용 AI 오케스트레이터 UI — Phase 0 설계

상태: **설계 기준선 확정안**  
대상 Core: **Universal AI Agent Orchestrator v0.8.4.1**  
범위: 개인용 로컬 운영 UI. 인증·멀티테넌시·클라우드 배포는 제외한다.

## 1. 목적

이 UI는 Core를 대체하거나 프리셋을 프론트엔드 코드에 고정하지 않는다. 기존 Core의
`Workspace → Project → Job Template → Agent Team + Workflow → Job → Run → Artifact`
구조를 사람이 일상적으로 사용할 수 있도록 표현하는 운영 계층이다.

Phase 0의 핵심 결정은 다음과 같다.

1. **실행의 기본 단위는 Job**이다. `/runs` 직접 실행은 고급/진단 기능으로만 둔다.
2. **프리셋은 Job Template의 UI 표현**이다. 별도의 실행 엔진 개념을 만들지 않는다.
3. **팀은 역할 슬롯과 Agent의 결합**이며 UI에서 교체할 수 있어야 한다.
4. **Workflow는 처리 절차**, Team은 담당자, Job Template은 반복 업무 계약을 담당한다.
5. 일반 JSON Schema 입력은 자동 렌더링하고, 문서·개발·퀀트·영상의 특수 입력과 결과만
   플러그형 UI 컴포넌트로 확장한다.
6. 모든 Run은 시작 시점의 정의 스냅샷으로 표시하며, 이후 설정 변경이 과거 Run 화면을
   바꾸지 않게 한다.
7. 개인용이라도 코드 저장·승인·베이스라인 승격 같은 중요 동작은 명시적으로 확인한다.

## 2. 설계 문서

- [정보구조와 화면 명세](./01_INFORMATION_ARCHITECTURE.md)
- [프론트엔드–Core API 계약과 갭](./02_API_CONTRACT_AND_GAPS.md)
- [프리셋·팀·워크플로우 연결 및 버전 정책](./03_CONFIGURATION_AND_VERSIONING.md)

## 3. 범위

### Phase 1 공통 셸 구현 완료

- 공통 앱 셸과 시스템 상태
- 프리셋 카탈로그
- Workspace/Project 선택
- Agent Team/Workflow/Template 읽기 전용 조회

Docker 기반 `frontend/` 운영 콘솔로 구현되었다. 접속 주소는 `http://localhost:3000`이며,
Nginx reverse proxy가 API Key를 서버 측에서 주입한다.

### Phase 2 문서작성팀 흐름 구현 완료

- 문서 전용 요청 폼과 실행 수준 선택
- Job 생성·시작
- Job/Run 상세와 SSE 진행 표시
- Markdown 결과 미리보기
- Human 승인·반려와 수정 의견
- 최종 Artifact 다운로드

### Phase 3 시스템 개발팀 흐름 구현 완료

- 읽기 전용 소스 분석과 코드 생성 요청 모드 분리
- 허용된 소스 루트 내부 폴더 찾기·검색·선택
- 선택 폴더의 소스 Glob 자동 생성, 분석 초점, 상세 명세 입력
- Quality 코드 생성과 테스트 명령·Artifact 경로 설정
- 파일별 생성 코드와 샌드박스 테스트 출력
- 분석/코드 결과 승인·반려
- 승인된 분석 보고서와 코드 Artifact 다운로드

### 후속 단계

1. 팀 구성 변경과 정의 버전 관리
2. 퀀트 자문팀 분석 화면
3. 동영상 제작팀 자산·렌더 화면
4. 필요한 경우에만 Workflow 시각 편집기

### 명시적으로 제외

- 로그인/회원 관리
- 완전한 SaaS 권한 격리
- 인터넷 공개 배포
- 브라우저 기반 IDE 또는 영상 편집기
- 첫 버전의 Workflow 드래그앤드롭 편집
- 퀀트 주문 실행 및 자동 전략 배포

### Phase 4 공통 작업공간·참조 조사 기반 구현 완료

- 문서·개발 작업이 동일한 참고 폴더 선택 모델을 재사용
- Knowledge, 참고 파일, 지정 URL, 선택적 웹 검색을 공통 근거 묶음으로 통합
- 로컬 검색 서비스가 출처 URL을 보존하며 네 AI 팀에 재사용 가능
- 문서 유형 선택과 Markdown/PDF/PowerPoint 다중 출력 지원
- 문서와 개발 결과를 지정한 프로젝트 하위 폴더로 분리 저장
- 웹 연결 또는 일부 URL 조회 실패 시 경고를 남기고 나머지 근거로 계속 작업

## 4. 용어

| UI 용어 | Core 개념 | 의미 |
|---|---|---|
| 프리셋 | `JobTemplateDefinition` + UI metadata | 사용자에게 보이는 반복 업무 시작점 |
| AI 팀 | `AgentTeamDefinition` | 역할 슬롯과 Agent 배치 |
| 작업 절차 | `WorkflowDefinition` | 노드와 의존관계로 정의된 실행 절차 |
| 작업 | `JobRecord` | 제목·우선순위·입력·상태를 가진 업무 Inbox 항목 |
| 실행 | `RunRecord` | Job이 실제 Workflow를 수행한 기록 |
| 승인 요청 | `HumanTaskRecord` | 사람이 승인·반려해야 재개되는 지점 |
| 결과물 | Artifact | 문서, 코드, JSON, 이미지, 영상 등의 산출물 |
| 직접 실행 | Use Case 또는 Workflow 기반 `/runs` | 관리자 진단·테스트용 실행 |

## 5. 완료 판정

Phase 0는 다음 조건을 만족하면 완료로 본다.

- 화면과 Core 도메인 사이의 책임 경계가 정의되어 있다.
- 네 프리셋의 요청·진행·결과·승인 차이가 명시되어 있다.
- 프론트엔드 구현에 필요한 현재 API와 부족한 API가 우선순위별로 구분되어 있다.
- 팀/Agent 교체가 Workflow와 기존 Run을 깨뜨리지 않는 버전 규칙이 정의되어 있다.
- Phase 1이 추가 제품 결정을 요구하지 않고 착수 가능한 수준으로 분해되어 있다.
