# 01. 현행 시스템 분석서 (As-Is)

- 대상: Universal AI Agent Orchestrator `v0.8.4.1`
- 분석 기준일: 2026-08-04
- 분석 범위: `app/` 29개 모듈(11,010 LOC), `config/`, `migrations/`, `mcp_server/`, `frontend/`, `examples/`
- 목적: **"회사 데이터를 연결하는 한국형 AI 업무 플랫폼"**으로 확장하기 위한 현행 데이터 계층 성숙도 진단

---

## 1. 시스템 개요

### 1.1 한 줄 정의

YAML로 정의된 멀티 에이전트 워크플로를 노드 그래프 엔진 위에서 실행하고, 인간 승인·품질 평가·통제된 협업을 거쳐 산출물을 만드는 오케스트레이터.

### 1.2 기술 스택

| 계층 | 기술 | 비고 |
|---|---|---|
| API | FastAPI, Pydantic v2 | `app/main.py` 1,669 LOC, 라우트 74개 |
| 실행 엔진 | 자체 노드 그래프 (`app/engine.py`) | 9개 노드 타입, 체크포인트/재개 지원 |
| 영속 | PostgreSQL + pgvector, async SQLAlchemy | `app/repository.py` 1,448 LOC + 인메모리 구현 |
| LLM | LiteLLM (Ollama 로컬 기본 + Claude/Gemini fallback) | `config/model_profiles.yaml` 슬롯 패턴 |
| 프런트 | React + Vite (단일 `App.tsx` 1,300 LOC) | 로컬 운영자 UI |
| 배포 | Docker Compose, Windows PowerShell 스크립트 | `docker-compose.yml`, `scripts/windows/` |
| 확장 | MCP 서버 (`mcp_server/server.py`) | 외부 에이전트 연동 |

### 1.3 핵심 설계 원칙 (그대로 계승해야 할 자산)

1. **정의는 코드가 아니라 데이터** — 에이전트·워크플로·팀·프리셋 전부 `examples/**` YAML. 동작 변경은 대부분 Python 수정 없이 가능.
2. **3계층 프리셋 모델** — `job_templates`(실행 계약) + `preset_ui`(화면) + `workflows`/`teams`(파이프라인). 둘이 서로를 id+version으로 참조해야만 카드가 노출됨.
3. **슬롯 패턴** — 워크플로가 역할 슬롯(`@planner`)으로 에이전트를 참조. 바인딩만 바꾸면 로컬/프런티어 모델 교체.
4. **구조는 계약, 텍스트는 증거** — `template_parser.py`/`spec_parser.py`가 문서 양식·시방서·테이블정의서를 **LLM 없이 결정적으로** 파싱해 에이전트가 반드시 지켜야 할 골격으로 주입. 자유 텍스트는 신뢰하지 않는 증거로만 취급.
5. **부작용 등급(L0~L3)** — 도구마다 `side_effect_level`을 두고 실행 컨텍스트의 `allowed_side_effect_level`로 상한을 강제.
6. **설정 동결** — Job 생성 시 `configuration_bundle`에 템플릿/워크플로/팀/설정을 SHA-256으로 동결. 이후 레지스트리가 바뀌어도 READY Job은 변하지 않음.
7. **버전 승급 규율** — 정의 YAML 내용이 바뀌면 `version` 필수 증가. 같은 버전·다른 내용은 `409 Conflict`.

> 이 7가지는 데이터 커넥터 계층을 설계할 때도 **그대로 적용해야 하는 제약**이다. 커넥터를 "그냥 Python 클래스 추가"로 만들면 이 시스템의 일관성이 깨진다.

---

## 2. 현행 데이터 연결 계층 정밀 진단

사용자가 제시한 6개 고도화 항목 기준으로 현재 상태를 평가한다.

| # | 요구 항목 | 현재 상태 | 성숙도 |
|---|---|---|---|
| 1 | PostgreSQL 연결 | 구현됨 (읽기전용, 보안 가드 양호) | **B** |
| 1 | MSSQL 연결 | **없음** — `driver: Literal["postgresql"]`로 타입 차단 | **F** |
| 1 | Oracle 연결 | **없음** — 동일 | **F** |
| 2 | 엑셀·CSV 업로드 | CSV는 "그냥 텍스트"로 RAG 인제스트. 엑셀 미지원 | **D** |
| 3 | PDF·Word 문서 분석 | PDF(pypdf)·DOCX 텍스트 추출 가능. HWP/HWPX·PPTX·OCR 없음 | **C** |
| 4 | 폴더 단위 문서 검색 | 폴더 **읽기**는 되지만 **검색 인덱스와 분리**됨 | **D** |
| 5 | API 연결 | `web.fetch`/`web.search`만 존재. 범용 REST/OpenAPI 커넥터 없음 | **F** |
| 6 | 데이터 소스별 접근 권한 | Workspace 단위 allowlist 1단계만. 사용자·테이블·컬럼·행 단위 전무 | **D** |

### 2.1 DB 연결 (`app/datasources.py`, 145 LOC)

**구현된 것 — 보안 설계는 이미 수준급이다.**

```
validate_read_only_sql()
  ├─ 길이 1..50,000자
  ├─ 주석(--, /* */)·널바이트 금지
  ├─ 세미콜론 1개 이하 → 단일 문장 강제
  ├─ ^(select|with) 만 허용
  ├─ 금지 키워드 정규식 (insert/update/.../set/reset/listen/notify/load)
  ├─ 위험 함수 차단 (pg_read_file, dblink, lo_export, current_setting ...)
  └─ 시스템 스키마 차단 (pg_catalog, information_schema, pg_toast)

query()
  ├─ 스키마 allowlist 검증 (FROM/JOIN 뒤 스키마 한정자 추출)
  ├─ SELECT * FROM (원쿼리) LIMIT max_rows+1  ← 강제 행수 제한
  ├─ SET TRANSACTION READ ONLY
  ├─ SET LOCAL statement_timeout
  └─ SET LOCAL search_path = allowlist
```

`ToolDefinition.data_source_scoped=True`인 도구는 입력 스키마에 `source_id`가 **required**여야 하며(`domain.py:393`), 엔진이 실행 직전 워크스페이스 allowlist를 검사한다(`engine.py:415-425`).

**문제점 — 제품화 관점 8가지**

| # | 문제 | 근거 | 영향 |
|---|---|---|---|
| D-1 | **PostgreSQL 전용** | `DataSourceDefinition.driver: Literal["postgresql"]`, `_engine()`이 `postgresql+asyncpg://`가 아니면 `ValueError` | MSSQL/Oracle 요구를 코드 수정 없이 못 받음. 국내 중소 제조·물류 현장은 **MSSQL이 다수** |
| D-2 | **SQL 가드가 PostgreSQL 문법 전제** | `_FORBIDDEN`·`_SYSTEM_SCHEMA` 정규식이 PG 카탈로그명 기준. T-SQL `sp_`/`xp_`, Oracle `DBMS_`/`UTL_FILE`은 무방비 | 다른 DB를 붙이는 순간 보안 가드가 **뚫림** |
| D-3 | **정규식 denylist 방식의 한계** | 키워드 블랙리스트는 우회 가능성이 상존. 파서 기반 검증 아님 | 고객사 감사에서 지적 대상 |
| D-4 | **스키마 카탈로그 없음** | 어디에도 테이블/컬럼 메타데이터를 수집·저장하는 코드가 없음. `system_inventory.py`는 **소스코드 AST 파싱**이지 라이브 DB 메타데이터가 아님 | LLM이 SQL을 쓰려면 스키마를 알아야 하는데 알 방법이 없음. Text-to-SQL이 사실상 불가능 |
| D-5 | **접속정보 관리가 `.env` 환경변수뿐** | `url_env`로 이름만 지정, 값은 프로세스 환경변수 | 고객사별/워크스페이스별 다중 DB 관리 불가. 자격증명 회전·암호화·감사 없음 |
| D-6 | **커넥션 풀이 소스당 2** | `pool_size=2, max_overflow=0` | 동시 Job 다수 실행 시 즉시 병목 |
| D-7 | **API 직접 호출 경로에 권한 검사가 없음** | `POST /data-sources/query`는 `authorize`(API 키)만 통과하면 **모든 소스에 임의 SELECT 가능**. 워크스페이스 검사는 엔진 경로에만 존재 | 심각한 권한 우회 경로. 제품화 전 반드시 차단 |
| D-8 | **질의 감사 로그 없음** | `llm_calls` 테이블은 있으나 `db.query` 실행 기록 테이블이 없음 | "누가 언제 어떤 사내 데이터를 조회했나"에 답할 수 없음 = 기업 판매 불가 |

### 2.2 파일 업로드 / 문서 분석 (`app/knowledge.py`, 280 LOC)

**구현된 것**

- `POST /knowledge/documents` (텍스트), `PUT /knowledge/documents/{id}/content` (바이너리 스트리밍, 기본 상한 20MB)
- `extract_text()` 지원 포맷: `text/plain`, `text/markdown`, `text/csv`, `application/json`, `text/html`, `docx`(zip→`word/document.xml` 직접 파싱), `application/pdf`(pypdf)
- 문단 경계 인식 청킹 (`chunk_size=1200`, `overlap=150`), 긴 문단은 슬라이딩 윈도우로 분할하며 꼬리 유실 방지
- 임베딩: Ollama `/api/embed` (기본 `nomic-embed-text`, 768차원), 16개씩 배치, 차원 불일치 시 즉시 실패
- 검색: pgvector HNSW 코사인 kNN, 모든 검색은 `retrieval_events`에 기록되고 `retrieval_id`가 발급됨

> **인용 무결성 설계는 훌륭하다.** `collaboration.py`가 "실제 retrieval ID가 있는 근거만 인용 가능"을 강제하고 FACT/INFERENCE/RECOMMENDATION/UNKNOWN 주장 계약을 둔 것은 기업용 제품에서 가장 어려운 부분을 이미 푼 것이다.

**문제점 — 9가지**

| # | 문제 | 근거 | 영향 |
|---|---|---|---|
| K-1 | **엑셀(xlsx/xls) 미지원** | `extract_text` 분기에 없음 → `unsupported document type` | 국내 기업 데이터의 절대다수가 엑셀. 최우선 결손 |
| K-2 | **HWP/HWPX 미지원** | 동일 | 한국형 플랫폼 표방 시 **치명적**. 공공·제조 문서 상당수가 HWP |
| K-3 | **CSV를 표가 아니라 글로 취급** | `text/csv`를 그대로 decode해서 청킹 | 100만 행 CSV를 임베딩하는 무의미한 동작. 집계·필터 질의 불가 |
| K-4 | **스캔 PDF 대응 없음** | pypdf `extract_text()`는 이미지 PDF에서 빈 문자열 반환. 실패조차 안 나고 **조용히 빈 문서 생성** | 도면·거래명세서 스캔본이 흔한 제조·물류 현장에서 무증상 실패 |
| K-5 | **인제스트가 동기 요청 내 처리** | `upload_document_content`가 요청 안에서 추출→청킹→임베딩→저장 전부 수행 | 대용량 문서 업로드가 API 워커를 점유. 진행률·재시도·실패 복구 없음 |
| K-6 | **중복 제거 미동작** | `content_hash`를 저장은 하지만 인제스트 시 조회·스킵하지 않음 | 같은 문서 재업로드 시 청크 중복 → 검색 결과 오염 |
| K-7 | **임베딩 모델이 전역 단일·차원 하드코딩** | `migrations/004`에 `embedding vector(768)`, 설정도 전역 1개 | 모델 교체 = 전량 재색인 + DDL 변경. 한국어 특화 임베딩 도입 시 큰 마이그레이션 |
| K-8 | **순수 벡터 검색만 존재 (하이브리드·리랭커 없음)** | `search_knowledge(collection, vector, top_k, workspace_id)` 단일 경로 | **한국어에서 실질 품질 리스크.** 품번·거래처코드·규격("SUS304 t2.0")·조사 변형은 dense 임베딩이 잘 못 잡는다. BM25 병행이 필수 |
| K-9 | **문서 단위 접근권한이 없음** | `knowledge_chunks`는 `workspace_id`+`collection`만 보유 | 워크스페이스 접근 = 그 안 모든 문서 열람. 인사·재무 문서 분리 불가 |

### 2.3 폴더 단위 문서 검색 (`app/external.py` `FileReadService`)

**구현된 것**

- `APP_FILE_READ_ROOTS` 화이트리스트 루트 내부만 접근, 경로 이탈(`..`) 차단 (`_resolve`가 `root in target.parents` 검사)
- `file.read` 도구(L0), `/reference-directories`로 폴더 트리 노출, 파일당 5MB 상한
- 반환 페이로드에 `injection_notice`를 붙여 **읽은 내용은 명령이 아니라 데이터**임을 프롬프트 계층에 명시 — 프롬프트 인젝션 방어로 올바른 접근
- `template_parser.role_globs()`가 사용자가 고른 단일 작업폴더를 역할별 하위폴더(`template/`, `references/`, `specs/`, `tables/`, `ui/`)로 매핑

**문제점**

| # | 문제 | 영향 |
|---|---|---|
| F-1 | **"폴더 읽기"와 "폴더 검색"이 서로 다른 세계** | `file.read`는 인덱스를 만들지 않고, `knowledge.search`는 폴더를 모른다. 사용자가 기대하는 "이 폴더에서 찾아줘"가 성립하지 않음 |
| F-2 | **증분 동기화·감시 없음** | `rglob` 전수 스캔. 파일 변경 감지, 삭제 반영, 스케줄 동기화 전무 |
| F-3 | **500개 파일 하드 캡** | `list_files`가 `sorted(found)[:500]`. 실무 폴더는 수만 개 |
| F-4 | **파일시스템 ACL 무시** | 프로세스 권한으로 전부 읽음. 윈도우 공유폴더 권한 체계와 무관하게 동작 |
| F-5 | **컨테이너 마운트 의존** | Docker 배포 시 호스트 폴더를 볼륨으로 넣어야 함. 고객사 파일서버(SMB/NAS) 연결 경로가 설계에 없음 |

### 2.4 API 연결

현재 존재하는 것은 두 가지뿐이다.

- `web.fetch` — `APP_WEB_FETCH_DOMAINS` 도메인 허용목록 기반 HTTPS 페이지 가져오기 (2MB 상한)
- `web.search` — SearXNG 등 JSON 검색 엔드포인트

**즉, 사내 시스템 API 연결 기능은 0이다.** 없는 것:

- 범용 REST 커넥터 (OpenAPI/Swagger 스펙 임포트)
- 인증 방식 처리 (API Key, Bearer, OAuth2 Client Credentials, 사내 SSO)
- 페이지네이션·레이트리밋·재시도·백오프
- 응답 스키마 매핑 및 캐싱
- 국내 업무 시스템 커넥터 (더존, 영림원, SAP B1, 그룹웨어, 카카오워크/네이버웍스, 세금계산서, 화물/택배 추적)

### 2.5 접근 권한

**현재 권한 모델의 전체 그림**

```
X-API-Key (단일 문자열, secrets.compare_digest 상수시간 비교)
   └─ 통과하면 모든 API 접근 가능
        └─ Workspace (논리 경계)
             ├─ model_policy: local_only | hybrid | cloud_allowed
             └─ allowed_data_sources: ["*"] 또는 [source_id...]
                  └─ 엔진의 data_source_scoped 도구 실행 시에만 검사
```

CLAUDE.md도 이를 명시적으로 인정한다: *"Workspace is a data boundary under a single API key, not full multi-tenant isolation."*

**결손 목록**

| # | 없는 것 | 기업 판매 시 요구 수준 |
|---|---|---|
| P-1 | 사용자(User) 개념 | 로그인, 세션, 개인 식별 |
| P-2 | 조직/부서, 역할(Role), 권한(Permission) | RBAC 최소, 가능하면 ABAC |
| P-3 | 데이터 소스별 사용자 권한 | 사용자 A는 생산 DB만, B는 회계 DB만 |
| P-4 | 테이블/컬럼 단위 통제 | 급여 테이블 차단, 주민번호 컬럼 마스킹 |
| P-5 | 행 단위 보안(RLS) | 자기 사업장 데이터만 |
| P-6 | 개인정보 마스킹/비식별 | 개인정보보호법 대응 |
| P-7 | 접근 감사 로그 | 누가·언제·무엇을·어떤 결과 (조회 이력 보존) |
| P-8 | 승인 기반 데이터 접근 | 민감 소스는 결재 후 조회 |
| P-9 | SSO 연동 | 사내 AD/LDAP, 네이버웍스, 카카오워크 |

---

## 3. 아키텍처 관점 종합 진단

### 3.1 강점 (그대로 살릴 자산)

1. **YAML 정의 + 버전 규율 + 설정 동결** — 재현성·감사성 측면에서 이미 기업용 수준. 커넥터도 이 틀에 태우면 그대로 이득을 본다.
2. **부작용 등급(L0~L3) + 도구 레지스트리** — 커넥터를 도구로 편입하는 자연스러운 확장 지점이 이미 존재.
3. **인용 무결성·주장 계약** — RAG 제품의 최대 난제인 환각 통제가 설계에 들어가 있음.
4. **결정적 구조 파싱** — 양식/시방서를 LLM 없이 파싱하는 접근은 한국 기업 문서(표준 양식이 강한 문화)에 특히 잘 맞는다.
5. **로컬/프런티어 모델 분리** — 폐쇄망 요구가 강한 국내 제조업에 그대로 맞는 구조.
6. **인메모리 리포지토리 병행** — DB 없이 213개 테스트가 도는 구조는 커넥터 추가 시 테스트 비용을 크게 낮춘다.

### 3.2 약점 (제품화 전 반드시 해소)

| 등급 | 항목 | 사유 |
|---|---|---|
| **Blocker** | 인증·인가 부재 (단일 API 키) | 이것 없이는 어떤 기업에도 못 판다 |
| **Blocker** | `POST /data-sources/query` 권한 우회 | 워크스페이스 검사가 API 경로에 없음 |
| **Blocker** | 데이터 접근 감사 로그 부재 | 내부통제·개인정보보호법 대응 불가 |
| **Critical** | 커넥터 프레임워크 부재 | 소스 하나 추가할 때마다 Python 수정 → 확장 불가능한 구조 |
| **Critical** | MSSQL/Oracle 미지원 | 타깃 시장(제조·물류)의 실제 DB 분포와 불일치 |
| **Critical** | 엑셀·HWP 미지원 | 한국형을 표방하는 데 근본적 결손 |
| **Critical** | 비동기 인제스트 파이프라인 부재 | 실사용 규모에서 즉시 붕괴 |
| **High** | 하이브리드 검색·리랭커 부재 | 한국어 검색 품질 리스크 |
| **High** | 스키마 카탈로그 부재 | Text-to-SQL이 성립하지 않음 |
| **High** | 프런트엔드 단일 파일 1,300 LOC | 데이터 소스 관리 화면 추가 시 유지보수 붕괴 |
| **Medium** | 실 LLM 품질 미검증 (CLAUDE.md 자인) | "213 passed"는 로직 통과일 뿐 |
| **Medium** | 감사 하네스(변경이력) 설계만 존재 | CLAUDE.md 로드맵 2번 항목, 미구현 |

### 3.3 구조적 관찰 — 가장 중요한 한 가지

현재 시스템에서 데이터는 **세 갈래로 따로 흐른다.**

```
[DB]      → db.query        → 즉석 SQL 결과 (인덱스 없음, 스키마 정보 없음)
[문서]     → knowledge.*     → 벡터 인덱스 (파일 원본과 연결 없음)
[폴더]     → file.read       → 원시 텍스트 (인덱스 없음)
```

세 경로가 서로를 모르고, 공통 메타데이터·공통 권한·공통 감사 지점이 없다.
**고도화의 본질은 "커넥터를 더 만드는 것"이 아니라 이 세 갈래를 하나의 데이터 연결 계층(Data Connectivity Layer)으로 통합하는 것이다.** 그 위에서만 "데이터 소스별 접근 권한"이 일관되게 성립한다.

---

## 4. 정량 현황

| 지표 | 값 |
|---|---|
| 버전 | 0.8.4.1 |
| 백엔드 코드 | 11,010 LOC (Python 29파일) |
| API 라우트 | 74개 |
| 등록 도구 | 17개 (`core.echo`, `db.query`, `knowledge.search`, `file.read`, `file.write`, `web.fetch`, `web.search`, `code.read/save/exec`, `document.render/bundle`, `template.parse`, `spec.parse`, `reference.collect/require`, `video.montage`) |
| 데이터 소스 드라이버 | **1종 (PostgreSQL)** |
| 지원 문서 포맷 | 7종 (txt, md, csv, json, html, docx, pdf) |
| DB 마이그레이션 | 003~009 (7개) |
| 예제 정의 YAML | 에이전트 25, 워크플로 11, 팀 5, 잡템플릿 13, 프리셋UI 4 |
| 테스트 | 213 passed (인메모리) |
| 프런트엔드 | `App.tsx` 단일 1,300 LOC |

---

## 5. 결론

현행 시스템은 **오케스트레이션 엔진으로서는 이미 완성도가 높고, 데이터 플랫폼으로서는 아직 시작 지점에 있다.**

- 엔진·정의 체계·보안 등급·인용 무결성은 기업용 제품의 어려운 부분을 이미 해결해 두었다.
- 반면 데이터 연결 계층은 "PostgreSQL 1종 + 문서 7종 + 폴더 읽기"에 머물러 있고, 이 셋이 서로 통합되어 있지 않으며, 접근 권한과 감사가 사실상 없다.
- 따라서 고도화는 **기능 추가가 아니라 계층 신설**로 접근해야 한다. → `02_PRODUCT_PLAN.md`, `03_CONNECTOR_DETAIL_DESIGN.md`

---

### 부록 A. 분석 근거 파일

| 주제 | 파일 |
|---|---|
| DB 연결·SQL 가드 | `app/datasources.py`, `config/data_sources.yaml`, `app/domain.py:405-422` |
| 권한 검사 | `app/engine.py:412-425`, `app/main.py:218-220`, `app/domain.py:619-631` |
| 문서 인제스트·검색 | `app/knowledge.py`, `app/main.py:641-731`, `migrations/004` |
| 폴더 접근 | `app/external.py:56-120`, `app/config.py`, `app/main.py:503-522` |
| 도구 등록 | `app/tools.py:342-830`, `app/domain.py:381-401` |
| 워크스페이스 모델 | `migrations/007`, `app/repository.py:490-500, 1370-1380` |
| 설정 | `app/config.py`, `.env.example` |
| 로드맵·자체 진단 | `CLAUDE.md:133-165`, `ARCHITECTURE_V072.md`, `docs/ui/02_API_CONTRACT_AND_GAPS.md` |
