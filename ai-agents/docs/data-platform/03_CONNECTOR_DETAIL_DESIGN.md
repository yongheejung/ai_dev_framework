# 03. 데이터 연결 계층 상세설계서

- 대상: Universal AI Agent Orchestrator v0.8.4.1 → v1.0
- 작성일: 2026-08-04
- 선행 문서: `01_AS_IS_ANALYSIS.md`, `02_PRODUCT_PLAN.md`
- 범위: 요구 6개 항목 **전부 설계**, 구현은 Phase 1/2/3 분할

---

## 0. 설계 요약 (1페이지)

**신설하는 것 — 4개 컴포넌트**

| 컴포넌트 | 파일 | 역할 |
|---|---|---|
| `ConnectorRegistry` | `app/connectors/registry.py` | 커넥터 정의(YAML) 로딩 + 드라이버 플러그인 해석 |
| `DataAccessGateway` | `app/access/gateway.py` | **모든** 데이터 접근의 유일한 관문 (권한·마스킹·감사) |
| `PolicyEngine` | `app/access/policy.py` | 주체×객체×행위 정책 평가 |
| `CatalogService` | `app/catalog/service.py` | 스키마·문서·필드 메타데이터 단일 원장 |

**변경 최소화 원칙**

- 기존 도구 ID(`db.query`, `knowledge.search`, `file.read`)는 **유지**한다. 내부 구현만 Gateway 경유로 교체.
- 기존 워크플로 YAML 11개, 에이전트 25개, 잡템플릿 13개는 **수정하지 않는다.**
- `DataSourceDefinition`은 deprecated 후 `ConnectorDefinition`으로 흡수. 기존 `config/data_sources.yaml`은 자동 변환 로더로 계속 동작.

---

## 1. 커넥터 프레임워크

### 1.1 계층 구조

```
app/connectors/
├── __init__.py
├── base.py           # Connector ABC, ConnectorCapability, ConnectorResult
├── registry.py       # 정의 로딩 + 드라이버 해석 + 인스턴스 캐시
├── credentials.py    # 자격증명 봉투 암호화 저장/조회
├── health.py         # 연결 상태 점검, 회로차단기
└── drivers/
    ├── db_postgresql.py
    ├── db_mssql.py
    ├── db_oracle.py
    ├── file_upload.py
    ├── folder.py
    └── rest_api.py
```

### 1.2 공통 인터페이스 (`base.py`)

```python
class ConnectorCapability(StrEnum):
    QUERY      = "query"       # SQL/구조화 질의
    LIST       = "list"        # 목록 조회
    READ       = "read"        # 단건 원문 읽기
    SEARCH     = "search"      # 전문/의미 검색
    INTROSPECT = "introspect"  # 스키마/메타데이터 수집
    WATCH      = "watch"       # 변경 감지 (증분 동기화)


class Connector(ABC):
    """모든 커넥터의 계약. 인스턴스는 ConnectorRegistry만 생성한다."""

    capabilities: frozenset[ConnectorCapability]

    @abstractmethod
    async def health(self) -> HealthResult: ...

    @abstractmethod
    async def introspect(self) -> CatalogSnapshot:
        """스키마/문서 목록 등 메타데이터. Catalog에 적재된다."""

    @abstractmethod
    async def execute(self, request: AccessRequest) -> ConnectorResult:
        """실제 데이터 접근. Gateway 외에서 직접 호출 금지."""

    async def close(self) -> None: ...
```

> **강제 규칙:** `Connector.execute()`는 `DataAccessGateway` 이외에서 호출하면 안 된다.
> 이를 테스트로 강제한다 — `tests/test_access_boundary.py`가 `app/` 전체를 AST 파싱해
> Gateway 외 모듈에서 `.execute(` 호출이 있으면 실패시킨다. (기존 `system_inventory.py`의
> AST 파싱 기법을 그대로 재사용)

### 1.3 커넥터 정의 (YAML) — O-1 원칙 구현

기존 `DataSourceDefinition`을 일반화한다. 위치: `examples/connectors/*.yaml`
(기존 정의 체계와 동일하게 `version` 승급 규율·`configuration_definitions` 저장 대상)

```yaml
id: prod-erp-mssql
version: 1
name: 생산 ERP (MSSQL)
kind: database                      # database | file | folder | api
driver: mssql                       # 드라이버 레지스트리 키
enabled: true
description: 생산관리 ERP 읽기전용 복제본

credential_ref: cred-prod-erp       # 자격증명 저장소 참조 (값 직접 기재 금지)

connection:
  host_env: null                    # 하위호환: 환경변수 주입도 허용
  read_only_replica: true
  pool_size: 5
  pool_max_overflow: 5
  connect_timeout_ms: 5000

limits:
  max_rows: 500
  statement_timeout_ms: 20000
  max_concurrent_queries: 3
  daily_query_quota: 2000

scope:                              # 노출 범위 (allowlist)
  allowed_schemas: [dbo, mes]
  allowed_tables:                   # 비우면 스키마 내 전체
    - dbo.work_order
    - dbo.defect_log
    - mes.*
  denied_tables:
    - dbo.employee_salary

catalog:
  introspect_on_startup: true
  refresh_cron: "0 3 * * *"
  sample_rows: 3                    # 카탈로그용 샘플값 (마스킹 후 저장)

classification:                     # 데이터 등급 — 정책 평가 입력
  default: internal                 # public | internal | confidential | restricted
  column_overrides:
    dbo.customer.resident_no: restricted
    dbo.customer.phone: confidential
```

### 1.4 드라이버 등록 (플러그인)

```python
# app/connectors/registry.py
DRIVERS: dict[str, type[Connector]] = {}

def register_driver(key: str):
    def deco(cls: type[Connector]) -> type[Connector]:
        if key in DRIVERS:
            raise ValueError(f"driver already registered: {key}")
        DRIVERS[key] = cls
        return cls
    return deco
```

새 데이터 소스 추가 절차 = **드라이버 1개 파일 + 정의 YAML 1개.** 코어 수정 없음.

### 1.5 자격증명 저장소 (`credentials.py`)

As-Is의 `url_env` 환경변수 방식을 대체한다.

- 저장: `connector_credentials` 테이블에 **봉투 암호화**(envelope encryption)로 저장
  - DEK(데이터 키)로 자격증명 암호화 → DEK를 KEK(마스터 키)로 암호화하여 함께 저장
  - KEK는 `APP_CREDENTIAL_MASTER_KEY` 환경변수 또는 OS 키스토어 (온프레미스), 향후 KMS 대체 가능
- 조회: 평문은 **메모리에만** 존재. API 응답·로그·감사기록에 절대 미노출 (`***` 마스킹)
- 회전: `credential_version` 증가 방식, 이전 버전은 `revoked_at` 표시 후 보존
- 하위호환: `credential_ref`가 없고 `url_env`만 있으면 기존 환경변수 경로로 폴백

---

## 2. DataAccessGateway — 모든 데이터 접근의 유일한 관문

### 2.1 처리 흐름

```
AccessRequest
   │
   ├─ 1. 주체 확인 (Principal)
   │     user_id / role[] / workspace_id / project_id / run_id / job_id
   │     (에이전트 실행 시에도 "누구를 대신해 실행 중인가"가 반드시 실림)
   │
   ├─ 2. 정책 평가 (PolicyEngine.evaluate)
   │     → ALLOW / DENY / ALLOW_WITH_MASKING / REQUIRE_APPROVAL
   │
   ├─ 3. 사전 변환 (Request Rewriting)
   │     · 테이블 allowlist 검증
   │     · 금지 컬럼 SELECT 제거 or 거부
   │     · 행 수준 필터 주입 (RLS predicate)
   │     · 행수/타임아웃 상한 적용
   │
   ├─ 4. 실행 (Connector.execute)
   │     · 회로차단기, 재시도, 동시성 쿼터
   │
   ├─ 5. 사후 변환 (Response Masking)
   │     · 컬럼 마스킹 규칙 적용
   │     · 결과 크기 제한, 잘림 표시
   │     · injection_notice 부착 (O-4)
   │
   └─ 6. 감사 기록 (반드시. 실패해도 기록)
         data_access_events INSERT
```

### 2.2 인터페이스

```python
@dataclass(frozen=True)
class Principal:
    user_id: str | None            # None = 서비스 계정(기존 API 키 호환)
    roles: tuple[str, ...]
    workspace_id: str
    project_id: str | None = None
    run_id: str | None = None
    node_id: str | None = None
    job_id: str | None = None
    on_behalf_of: str | None = None   # 에이전트 실행의 실제 요청자


@dataclass(frozen=True)
class AccessRequest:
    connector_id: str
    action: Literal["query", "list", "read", "search", "introspect"]
    payload: dict[str, Any]        # 예: {"sql": "...", "parameters": {...}}
    principal: Principal


class DataAccessGateway:
    async def access(self, request: AccessRequest) -> ConnectorResult:
        decision = await self.policy.evaluate(request)
        if decision.effect is Effect.DENY:
            await self.audit.record(request, decision, status="DENIED")
            raise DataAccessDenied(decision.reason)
        if decision.effect is Effect.REQUIRE_APPROVAL:
            raise DataAccessApprovalRequired(decision)   # → human 노드로 승격
        rewritten = self.rewriter.apply(request, decision)
        try:
            result = await self.connectors.get(request.connector_id).execute(rewritten)
        except Exception as exc:
            await self.audit.record(request, decision, status="ERROR", error=str(exc))
            raise
        masked = self.masker.apply(result, decision)
        await self.audit.record(request, decision, status="OK", result_meta=masked.meta)
        return masked
```

### 2.3 기존 도구와의 접속 (호환성 핵심)

```python
# app/tools.py — 변경 후
async def db_query(args, execution_context):
    return await gateway.access(AccessRequest(
        connector_id=args["source_id"],          # 기존 파라미터명 유지
        action="query",
        payload={"sql": args["sql"], "parameters": args.get("parameters")},
        principal=_principal_from(execution_context),
    ))
```

- 도구 ID·입력 스키마·출력 스키마 **전부 그대로**. 기존 워크플로 YAML 무수정.
- `engine.py:412-425`의 워크스페이스 allowlist 검사는 **그대로 둔다** (2차 방어선). 단, 권위 있는 판정은 PolicyEngine이 한다.
- `execution_context`에 `user_id`/`on_behalf_of`를 추가로 실어야 한다 → `engine.py`의 `execution_context` dict에 2개 필드 추가 (기존 4개 필드 유지, 하위호환).

### 2.4 As-Is Blocker 차단

`POST /data-sources/query`는 다음과 같이 바뀐다.

```python
@app.post("/connectors/{connector_id}/query", dependencies=[Depends(require_auth)])
async def query_connector(connector_id: str, req: QueryRequest, principal: Principal = Depends(current_principal)):
    return await gateway.access(AccessRequest(
        connector_id=connector_id, action="query",
        payload=req.model_dump(), principal=principal,
    ))
```

기존 `POST /data-sources/query`는 **동일 Gateway 경유로 리다이렉트**하고 `Deprecation` 헤더를 반환한다. 권한 우회 경로가 사라진다.

---

## 3. 권한 모델 (요구항목 6)

### 3.1 데이터 모델 (ERD)

```
users ──< user_roles >── roles ──< role_permissions >── permissions
  │                                        │
  │                                        └─ 대상: connector / schema / table / column / collection
  │
  └──< user_workspaces >── workspaces (기존)
                              │
                              └──< connector_bindings >── connectors
```

```
┌────────────────┐      ┌──────────────────┐      ┌────────────────────┐
│ users          │      │ roles            │      │ access_policies    │
│ id (PK)        │      │ id (PK)          │      │ id (PK)            │
│ login_id       │──┐   │ workspace_id     │  ┌──▶│ workspace_id       │
│ display_name   │  │   │ name             │  │   │ subject_type       │  user|role
│ email          │  │   │ description      │  │   │ subject_id         │
│ status         │  │   └──────────────────┘  │   │ connector_id       │
│ auth_provider  │  │            ▲            │   │ object_type        │  connector|schema
│ created_at     │  │            │            │   │                    │  |table|column|collection
└────────────────┘  │   ┌────────┴─────────┐  │   │ object_pattern     │  'dbo.*', 'dbo.emp.salary'
                    └──▶│ user_roles       │──┘   │ actions            │  jsonb ["query","read"]
                        │ user_id (FK)     │      │ effect             │  ALLOW|DENY|MASK|APPROVAL
                        │ role_id (FK)     │      │ mask_rule          │  null|full|partial|hash
                        │ granted_at       │      │ row_filter         │  'plant_cd = :user.plant'
                        │ granted_by       │      │ priority           │  int, 낮을수록 우선
                        └──────────────────┘      │ valid_from/until   │
                                                  │ created_by         │
                                                  └────────────────────┘
```

### 3.2 정책 평가 규칙

1. **DENY 우선** — 매칭되는 DENY가 하나라도 있으면 즉시 거부.
2. **명시적 ALLOW 필요** — 매칭 ALLOW가 없으면 기본 거부(deny-by-default).
3. **우선순위** — `priority` 오름차순, 동률이면 더 구체적인 `object_pattern`(와일드카드 적은 쪽)이 우선.
4. **분류 등급 기본값** — `classification: restricted`인 객체는 명시적 ALLOW가 있어도 `REQUIRE_APPROVAL`로 승격 (기본 정책, 워크스페이스 설정으로 완화 가능).
5. **행 필터 병합** — 매칭된 ALLOW들의 `row_filter`는 **AND**로 결합.
6. **서비스 계정 하위호환** — `user_id=None`이면 기존 `workspace.allowed_data_sources`를 정책으로 환산해 평가. 기존 배포가 그대로 동작한다.

### 3.3 마스킹 규칙

| rule | 동작 | 예 |
|---|---|---|
| `full` | 전체 치환 | `***` |
| `partial` | 앞/뒤 일부 유지 | `홍*동`, `010-****-1234` |
| `hash` | SHA-256 앞 8자 (조인 가능, 값 미노출) | `a1b2c3d4` |
| `nullify` | NULL 반환 | `null` |
| `drop` | 컬럼 자체 제거 | 결과에서 사라짐 |

**개인정보 자동 탐지 (기본 안전)**
카탈로그 수집 시 컬럼명·샘플값 패턴으로 개인정보 후보를 자동 태깅하고, 후보는 **기본 `restricted`로 분류**한다. 관리자가 명시적으로 완화하기 전까지는 노출되지 않는다.

```
주민번호   : 컬럼명 (resident|jumin|ssn|rrn) OR 값 \d{6}-?[1-4]\d{6}
휴대폰     : (phone|mobile|hp|tel)          OR 값 01[016-9]-?\d{3,4}-?\d{4}
계좌       : (account|acct|bank)            OR 값 \d{2,6}-?\d{2,6}-?\d{2,7}
사업자번호 : (biz_no|bizno|company_no)      OR 값 \d{3}-?\d{2}-?\d{5}
이메일     : (email|mail)                   OR 값 RFC5322 근사
주소/성명  : (addr|address|name|nm) → 후보 태깅 후 관리자 확인 요청
```

### 3.4 감사 로그

```sql
data_access_events (
  id, occurred_at, workspace_id, project_id,
  principal_user_id, principal_roles, on_behalf_of,
  run_id, node_id, job_id,
  connector_id, connector_kind, action,
  object_refs      jsonb,   -- 실제 접근한 테이블/문서/파일 목록
  request_digest   text,    -- SQL 정규화 후 해시 (원문은 아래 정책에 따름)
  request_preview  text,    -- 선택적 원문 (설정으로 저장 여부 제어)
  policy_decision  varchar, -- ALLOW / DENY / MASK / APPROVAL
  matched_policies jsonb,
  masked_columns   jsonb,
  status           varchar, -- OK / DENIED / ERROR / TIMEOUT
  row_count, bytes_returned, latency_ms, error
)
```

**불변성** — 이 테이블은 append-only. 애플리케이션 롤은 INSERT/SELECT만 갖고 UPDATE/DELETE 권한을 부여하지 않는다(DB 롤 레벨 강제). CLAUDE.md 로드맵의 "감사 이벤트 로그는 절대 수정하지 않는다" 원칙과 일치.

**보존** — 기본 3년, 파티셔닝(월 단위) 후 아카이빙.

---

## 4. DB 커넥터 (요구항목 1)

### 4.1 드라이버 매트릭스

| 드라이버 | 라이브러리 | DSN | 읽기전용 강제 | 행수 제한 | 타임아웃 |
|---|---|---|---|---|---|
| `postgresql` | asyncpg (기존) | `postgresql+asyncpg://` | `SET TRANSACTION READ ONLY` | `SELECT * FROM (q) LIMIT n` | `SET LOCAL statement_timeout` |
| `mssql` | aioodbc + ODBC Driver 18 | `mssql+aioodbc://` | `SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED` + **읽기전용 계정 필수** | `SELECT TOP (n) * FROM (q) AS _q` | `Connection.timeout` + `SET LOCK_TIMEOUT` |
| `oracle` | python-oracledb (async) | `oracle+oracledb://` | 읽기전용 계정 + `SET TRANSACTION READ ONLY` | `SELECT * FROM (q) WHERE ROWNUM <= n` | `call_timeout` |

> **MSSQL·Oracle은 세션 레벨 읽기전용 강제가 PostgreSQL만큼 강하지 않다.**
> 따라서 **SELECT 전용 DB 계정 사용을 필수 요건으로 문서화**하고, 커넥터 정의에
> `connection.read_only_account_confirmed: true`를 명시하지 않으면 `enabled: true`를
> 거부한다 (pydantic `model_validator`). 마지막 방어선은 코드가 아니라 계정 권한이다.

### 4.2 SQL 가드 재설계

As-Is의 정규식 denylist는 PostgreSQL 전용이고 우회 위험이 있다. **파서 기반 + 방언별 denylist 2중 구조**로 교체한다.

```
app/connectors/sql_guard/
├── base.py         # SqlGuard ABC, GuardResult
├── parser.py       # sqlglot 기반 AST 파싱 (read=dialect)
├── postgres.py     # 기존 규칙 승계 + AST 검증
├── tsql.py         # sp_/xp_ 확장 프로시저, OPENROWSET, xp_cmdshell, BULK
└── plsql.py        # DBMS_*, UTL_FILE, UTL_HTTP, DBMS_SCHEDULER, ALTER SESSION
```

**공통 검증 (AST 기반)**

1. 단일 문장인가 (파싱 결과 statement 1개)
2. 최상위 노드가 `SELECT` 또는 `WITH`인가
3. AST를 순회하며 DML/DDL/DCL 노드가 하나도 없는가
4. 참조된 모든 테이블이 `scope.allowed_tables`에 매칭되고 `denied_tables`에 없는가
5. 참조된 모든 컬럼이 정책상 허용되는가 (`SELECT *`는 카탈로그로 확장 후 검증)
6. 시스템 카탈로그 접근 차단 (방언별 목록)
7. 서브쿼리·CTE·UNION 내부까지 동일 규칙 재귀 적용

**핵심 개선:** AST에서 테이블·컬럼을 **정확히 추출**할 수 있으므로 정규식 시절 불가능했던
"테이블/컬럼 단위 권한"이 비로소 성립한다. 요구항목 6이 요구항목 1과 여기서 만난다.

**폴백** — sqlglot 파싱 실패 시 **거부**한다(fail-closed). 파싱 못 하는 SQL은 검증도 못 한다.

### 4.3 스키마 카탈로그 (As-Is 최대 결손 D-4 해소)

```
catalog_datasets        -- 논리 데이터셋 (테이블/뷰/시트/API 응답 공통)
  id, connector_id, kind(table|view|sheet|endpoint|collection),
  physical_name, logical_name_ko, description,
  row_count_estimate, classification, tags jsonb,
  last_introspected_at, is_active

catalog_fields
  id, dataset_id, ordinal, physical_name, logical_name_ko,
  data_type, nullable, is_primary_key, is_foreign_key,
  fk_dataset_id, fk_field_id,
  description, sample_values jsonb,     -- 마스킹 후 저장
  classification, pii_candidate boolean, distinct_count_estimate

catalog_relations
  id, from_dataset_id, from_field_id, to_dataset_id, to_field_id,
  relation_type(fk|inferred|manual), confidence
```

**수집 소스**

| DB | 메타데이터 소스 | 한글 논리명 |
|---|---|---|
| PostgreSQL | `information_schema` + `pg_description` | 컬럼 COMMENT |
| MSSQL | `sys.tables/columns` + `sys.extended_properties` | `MS_Description` |
| Oracle | `ALL_TAB_COLUMNS` + `ALL_COL_COMMENTS` | COMMENT |

**한글 논리명 보완** — 사내 DB는 컬럼 코멘트가 비어 있는 경우가 많다. 3단계 폴백:
1. DB 코멘트
2. 관리자가 UI에서 직접 입력 (`logical_name_ko`)
3. **기존 `system_inventory.py`/`service_table_linker.py` 재사용** — 고객사 소스코드를 AST 파싱해 테이블·컬럼 사용처와 화면 라벨을 역추적. 이미 구현되어 있는 자산이다.

**Text-to-SQL 프롬프트 주입** — 에이전트가 SQL을 쓸 때 카탈로그에서 **정책상 접근 가능한 데이터셋만** 골라 압축된 스키마 설명을 프롬프트에 주입한다. 접근 불가 테이블은 존재 자체를 알려주지 않는다(정보 유출 방지).

---

## 5. 파일 업로드 — 엑셀·CSV (요구항목 2)

### 5.1 핵심 설계 결정: 표는 글이 아니다

As-Is는 CSV를 텍스트로 임베딩한다(K-3). 이를 **이중 경로**로 바꾼다.

```
업로드 파일
   │
   ├─ 표 형식(xlsx/xls/csv/tsv) ──▶ TabularIngestor
   │      · 시트별 분리
   │      · 헤더 행 자동 탐지 (병합셀·타이틀 행 스킵)
   │      · 컬럼 타입 추론 (int/float/date/text/code)
   │      · 정규화 후 내부 DuckDB/PostgreSQL 테이블로 적재
   │      · catalog_datasets/fields 등록
   │      → 결과: db.query로 SQL 질의 가능한 데이터셋
   │
   └─ 문서 형식 ──────────────────▶ DocumentIngestor (RAG)
          → 결과: knowledge.search로 의미 검색 가능
```

**표 파일도 요약 텍스트는 RAG에 함께 넣는다** — 컬럼 목록·행 수·주요 값 분포를 담은
"데이터셋 카드"를 생성해 색인. 사용자가 "불량률 엑셀 어디 있지?"라고 물으면 찾을 수 있어야 하고,
"불량률 계산해줘"라고 물으면 SQL로 가야 한다. **라우팅은 카탈로그가 결정한다.**

### 5.2 표 인제스트 상세

```python
class TabularIngestor:
    async def ingest(self, file: UploadedFile) -> list[DatasetRef]:
        # 1. 시트 열거 (xlsx: openpyxl read_only + values_only 스트리밍)
        # 2. 헤더 탐지: 상위 20행 중 (비어있지 않은 셀 비율 + 문자열 비율 + 중복 없음) 최대 행
        # 3. 타입 추론: 컬럼별 상위 1000행 샘플 → int > float > date > bool > text
        #    한국 관행 처리: '1,234' 천단위, '2026.08.04'/'26/08/04' 날짜, '10%' 비율,
        #                    '₩1,000' 통화, 앞자리 0 유지 코드값(품번·우편번호) → text 고정
        # 4. 컬럼명 정규화: 공백·특수문자 → snake_case, 한글명은 logical_name_ko에 보존
        # 5. 병합셀: 좌상단 값으로 forward-fill
        # 6. 대상 테이블 생성: ws_{workspace}_ds_{dataset_id} (별도 스키마 uploaded_data)
        # 7. COPY/executemany 배치 적재
        # 8. catalog 등록 + 데이터셋 카드 RAG 색인
```

**제한 및 안전장치**

| 항목 | 기본값 |
|---|---|
| 최대 파일 크기 | 200MB (기존 20MB에서 상향, 설정 가능) |
| 최대 행 수 | 500만 행/파일 |
| 최대 컬럼 수 | 1,024 |
| 수식 | 계산된 값만 읽음 (`data_only=True`), 수식 문자열 미저장 |
| 매크로(xlsm) | 거부 |
| 외부 링크·DDE | 무시 및 경고 |
| 중복 업로드 | `content_hash` 동일 시 새 버전으로 등록(덮어쓰기 아님) + 사용자 확인 |

### 5.3 API

```http
POST   /connectors/{id}/datasets/upload      # multipart, 비동기 → ingestion_job_id 반환
GET    /ingestion-jobs/{id}                  # 진행률/단계/에러
GET    /datasets?workspace_id=&connector_id= # 목록
GET    /datasets/{id}                        # 스키마 + 샘플 (정책 마스킹 적용)
PATCH  /datasets/{id}/fields/{field_id}      # 한글 논리명·분류등급 수정
DELETE /datasets/{id}                        # 아카이브 (물리 삭제 아님)
```

---

## 6. 문서 분석 — PDF·Word·HWP (요구항목 3)

### 6.1 파서 매트릭스

| 포맷 | 라이브러리 | 추출 대상 | 비고 |
|---|---|---|---|
| PDF (텍스트) | pypdf → **pdfplumber**로 교체 | 텍스트 + **표** + 좌표 | 표 추출이 pypdf 대비 결정적 개선 |
| PDF (스캔) | Tesseract OCR (kor+eng) | 텍스트 | 텍스트 레이어 부재 감지 시 자동 전환 |
| DOCX | python-docx (기존 직접 XML 파싱 대체) | 본문 + 표 + 헤더/푸터 + 각주 | 표 손실 해소 |
| **HWP (5.0 바이너리)** | pyhwp / hwp5 | 본문 + 표 | 구형 포맷, 실패율 측정 필요 |
| **HWPX (OWPML)** | 자체 파서 (zip + XML) | 본문 + 표 + 스타일 | ZIP+XML이라 안정적. **HWPX 우선 권장** |
| PPTX | python-pptx | 슬라이드 텍스트 + 표 + 노트 | |
| 이미지 | Tesseract | 텍스트 | 도면·사진 내 문자 |
| 기존 7종 | 유지 | | |

### 6.2 HWP 처리 전략 (한국형의 핵심)

```
HWP/HWPX 입력
   │
   ├─ HWPX (.hwpx) ──▶ 자체 OWPML 파서 (권장 경로, 안정적)
   │
   └─ HWP (.hwp) ───┬─▶ pyhwp 파싱 시도
                    │
                    ├─ 성공 → 본문/표 추출
                    │
                    └─ 실패 → ① 한/글 설치 환경이면 CLI 변환 (hwp→hwpx)
                              ② 그래도 실패 → **명시적 실패 처리**
                                 (status=FAILED, 사유 기록, 관리자 알림)
```

> **원칙: 조용한 실패 금지.** As-Is의 K-4(스캔 PDF가 빈 문서로 조용히 등록되는 문제)를
> 구조적으로 차단한다. 추출 텍스트가 `min_extracted_chars`(기본 50자) 미만이면
> 인제스트를 `FAILED` 또는 `NEEDS_OCR`로 표시하고 색인하지 않는다.

### 6.3 문서 구조 보존

기존 `template_parser.py`의 "구조는 계약" 철학을 인제스트에 확장한다. 청크에 구조 메타데이터를 부착한다.

```python
KnowledgeChunkRecord.metadata = {
    "title": ...,
    "section_path": ["3. 품질관리", "3.2 불량 판정기준"],  # 헤딩 계층
    "page": 12,
    "block_type": "paragraph" | "table" | "list" | "caption",
    "table_ref": "T-3",         # 표는 별도 구조 보존
    "source_file_hash": ...,
    "classification": "internal",
    "acl_tags": ["dept:quality"],   # 문서 단위 권한 (K-9 해소)
}
```

**표 청킹** — 표는 문단처럼 자르면 의미가 파괴된다. 표는 **행 단위 청크 + 헤더 반복 부착** 방식으로 처리하고, 원본 표 전체는 `catalog_datasets`에도 등록해 SQL 질의 가능하게 한다.

---

## 7. 폴더 단위 문서 검색 (요구항목 4)

### 7.1 As-Is 문제의 근본 해결 (F-1)

"폴더 읽기"와 "폴더 검색"을 통합한다. 폴더를 **커넥터**로 승격시킨다.

```yaml
# examples/connectors/quality-docs-folder.yaml
id: quality-docs
version: 1
name: 품질관리 공유폴더
kind: folder
driver: folder
enabled: true
credential_ref: cred-nas-quality      # SMB 자격증명

connection:
  root_path: "//nas01/quality"        # SMB/UNC, 로컬 경로, 마운트 볼륨 모두 지원
  follow_symlinks: false

scope:
  include_globs: ["**/*.pdf", "**/*.hwp", "**/*.hwpx", "**/*.xlsx", "**/*.docx"]
  exclude_globs: ["**/~$*", "**/임시/**", "**/.git/**", "**/백업/**"]
  max_file_size_mb: 100
  max_files: 200000                   # As-Is 500개 캡 해소

sync:
  mode: incremental                   # full | incremental
  cron: "0 2 * * *"
  detect_by: [mtime, size, content_hash]
  delete_policy: soft                 # 원본 삭제 시 색인은 archived 처리
  respect_os_acl: true                # 파일시스템 ACL 반영 (F-4)

classification:
  default: internal
  path_overrides:
    "**/인사/**": restricted
```

### 7.2 증분 동기화 알고리즘

```
1. 스캔      : os.scandir 재귀 (rglob 대비 대폭 빠름), include/exclude 적용
2. 비교      : folder_index 테이블의 (path, mtime, size)와 대조
                 · 신규       → INGEST
                 · mtime/size 변경 → content_hash 확인 → 다르면 REINGEST
                 · 사라짐     → ARCHIVE (soft delete)
                 · 동일       → SKIP
3. 큐 적재   : 변경분만 ingestion_jobs에 투입
4. 처리      : 워커가 병렬 처리 (동시성 제한), 진행률 갱신
5. 정리      : 고아 청크 제거, 카탈로그 갱신
```

`folder_index` 테이블:
```sql
folder_index (
  id, connector_id, relative_path, absolute_path_hash,
  size_bytes, mtime, content_hash,
  document_id,                    -- knowledge_documents FK
  os_acl_snapshot jsonb,          -- 파일시스템 권한 (respect_os_acl 시)
  status,                         -- INDEXED | PENDING | FAILED | ARCHIVED | SKIPPED
  fail_reason, last_synced_at,
  UNIQUE (connector_id, relative_path)
)
```

### 7.3 OS ACL 반영 (F-4)

`respect_os_acl: true`이면 동기화 시 파일의 접근 제어 목록을 읽어 `os_acl_snapshot`에 저장하고,
사용자 계정을 SID/UID로 매핑해 검색 결과 필터에 반영한다.

- Windows/SMB: `win32security.GetFileSecurity` (또는 SMB 서버 조회)
- Linux: POSIX 권한 + ACL

매핑이 불가능한 사용자에 대해서는 **기본 차단**한다(fail-closed).

---

## 8. API 연결 (요구항목 5)

### 8.1 범용 REST 커넥터

```yaml
# examples/connectors/wms-api.yaml
id: wms-api
version: 1
name: 물류 WMS API
kind: api
driver: rest_api
enabled: true
credential_ref: cred-wms

connection:
  base_url: "https://wms.internal.corp/api/v2"
  openapi_spec: "file:///specs/wms-openapi.json"   # 있으면 엔드포인트 자동 등록
  auth:
    type: oauth2_client_credentials     # none|api_key|bearer|basic|oauth2_client_credentials
    token_url: "https://wms.internal.corp/oauth/token"
    scope: "read:inventory read:shipment"
    token_cache_ttl_sec: 3000
  verify_tls: true
  timeout_sec: 20

limits:
  rate_limit_per_min: 60
  max_response_bytes: 10485760
  retry:
    max_attempts: 3
    backoff: exponential
    retry_on: [429, 500, 502, 503, 504]
  circuit_breaker:
    failure_threshold: 5
    open_duration_sec: 60

endpoints:                              # openapi_spec이 없을 때 수동 정의
  - id: inventory.list
    method: GET
    path: /inventory
    description: 재고 목록 조회
    side_effect_level: L0               # 기존 등급 체계 재사용
    query_params:
      warehouse_cd: {type: string, required: true}
      as_of: {type: string, format: date}
    pagination:
      type: cursor                      # page | offset | cursor | link_header
      cursor_param: next_token
      cursor_path: $.meta.next_token
      items_path: $.data
      max_pages: 20
    response_schema_ref: "#/components/schemas/InventoryList"
```

### 8.2 안전 규칙

1. **L0(읽기) 엔드포인트만 기본 등록.** POST/PUT/DELETE는 `side_effect_level: L3`로만 정의 가능하며, 기존 원칙대로 **기본 미등록**이고 워크플로에서 명시적 허용 + 인간 승인 노드가 있어야 실행된다.
2. **SSRF 방어** — `base_url`은 커넥터 정의에 고정. 에이전트는 `endpoint_id`와 파라미터만 지정하며 임의 URL을 넣을 수 없다. 사설 IP 대역은 명시적 허용 목록에서만.
3. **응답은 증거** — `injection_notice` 부착 (O-4).
4. **자격증명 미노출** — 토큰은 커넥터 내부에만. 로그·감사·에이전트 프롬프트에 절대 노출 금지.

### 8.3 도구 노출

```python
ToolDefinition(
    id="api.call",
    name="External API Call",
    side_effect_level=SideEffectLevel.L0_READ,
    data_source_scoped=True,              # 기존 메커니즘 재사용 → 워크스페이스 검사 자동 적용
    input_schema={
        "type": "object",
        "properties": {
            "source_id": {"type": "string"},      # = connector_id
            "endpoint_id": {"type": "string"},
            "parameters": {"type": "object"},
            "max_pages": {"type": "integer"},
        },
        "required": ["source_id", "endpoint_id"],
    },
)
```

---

## 9. 인제스트 파이프라인 (K-5 해소)

### 9.1 구조

```
   업로드/동기화
        │
        ▼
  ingestion_jobs  ──(SKIP if content_hash 동일)──▶ 완료
        │
   [워커 풀] ─ 기존 app/worker.py 확장 (리스·하트비트 메커니즘 재사용)
        │
        ├─ 1. EXTRACT   원문 추출 (포맷별 파서)      ─┐
        ├─ 2. VALIDATE  최소 길이·인코딩·손상 검사     │ 각 단계 진행률/
        ├─ 3. STRUCTURE 섹션·표·메타 추출             │ 재시도 독립
        ├─ 4. CHUNK     구조 인식 청킹                │
        ├─ 5. EMBED     배치 임베딩                   │
        ├─ 6. INDEX     벡터 + BM25 동시 색인         │
        └─ 7. CATALOG   데이터셋/필드 등록            ─┘
```

```sql
ingestion_jobs (
  id, workspace_id, connector_id, source_ref,
  kind,            -- upload | folder_sync | api_snapshot
  status,          -- QUEUED | RUNNING | SUCCEEDED | FAILED | SKIPPED | CANCELLED
  stage,           -- EXTRACT | VALIDATE | STRUCTURE | CHUNK | EMBED | INDEX | CATALOG
  progress_pct, total_units, processed_units,
  content_hash, document_id, dataset_id,
  attempt, max_attempts, error, error_code,
  lease_owner, lease_expires_at,    -- 기존 worker.py 리스 방식 재사용
  created_at, started_at, finished_at
)
```

**기존 자산 재사용:** `app/worker.py`의 리스·하트비트·graceful shutdown, `app/scheduling.py`의 cron 트리거를 그대로 쓴다. 새 스케줄러를 만들지 않는다.

---

## 10. 검색 계층 재설계 (K-8 해소)

### 10.1 하이브리드 검색

```
질의
 │
 ├─ 벡터 경로 : 임베딩 → pgvector HNSW cosine → top 50
 │
 ├─ 키워드 경로: 한국어 형태소 분석 → PostgreSQL tsvector/GIN → top 50
 │               (mecab-ko / kiwi 기반 커스텀 텍스트 검색 설정)
 │
 ├─ 융합      : RRF (Reciprocal Rank Fusion), k=60
 │              score = Σ 1/(k + rank_i)
 │
 ├─ 권한 필터 : PolicyEngine으로 접근 불가 청크 제거 ★반드시 융합 후
 │
 ├─ 리랭킹    : cross-encoder 리랭커 (bge-reranker-v2-m3 등) → top_k
 │
 └─ 결과      : retrieval_events 기록 → retrieval_id 발급 (기존 인용 계약 유지)
```

**한국어 대응 세부**

| 문제 | 대응 |
|---|---|
| 조사·어미 변형 ("불량률이/불량률의") | 형태소 분석기 기반 tsvector |
| 품번·규격 ("SUS304 t2.0", "A-1023-B") | BM25 경로가 처리. dense 단독으로는 실패 |
| 사내 약어·동의어 | `search_synonyms` 사전 테이블 + 질의 확장 |
| 한/영 혼용 | 양쪽 인덱싱 |
| 띄어쓰기 오류 | n-gram 보조 인덱스 (선택) |

### 10.2 임베딩 모델 유연화 (K-7 해소)

```sql
-- 차원 하드코딩(vector(768)) 탈피
knowledge_collections (
  id, workspace_id, name,
  embedding_model, embedding_dimension,
  index_type, created_at
)
-- 청크 테이블을 차원별로 분리하거나, pgvector 최신 버전의 가변 차원 사용
knowledge_chunks_768  / knowledge_chunks_1024  ...
-- 또는 재색인 시 blue-green 컬렉션 전환
```

**모델 교체 절차** — 새 컬렉션 생성 → 백그라운드 재색인 → 검증 → 별칭 전환 → 구 컬렉션 폐기.
운영 중단 없이 한국어 특화 임베딩으로 이관 가능해야 한다.

---

## 11. 데이터베이스 마이그레이션

기존 `003~009`에 이어 `010~015`를 추가한다. 기존 원칙(가산적·멱등)을 유지한다.

| 번호 | 파일 | 내용 |
|---|---|---|
| 010 | `010_identity_and_access.sql` | `users`, `roles`, `user_roles`, `access_policies`, `api_clients` |
| 011 | `011_data_access_audit.sql` | `data_access_events` (월 파티션), 불변성 롤 설정 |
| 012 | `012_connectors.sql` | `connectors`, `connector_credentials`, `connector_health` |
| 013 | `013_catalog.sql` | `catalog_datasets`, `catalog_fields`, `catalog_relations` |
| 014 | `014_ingestion_and_folder.sql` | `ingestion_jobs`, `folder_index` |
| 015 | `015_hybrid_search.sql` | `knowledge_collections`, tsvector 컬럼 + GIN 인덱스, `search_synonyms`, 청크 메타 확장 |

### 11.1 하위호환 보장

```sql
-- 010: 기존 단일 API 키를 서비스 계정으로 승격
INSERT INTO api_clients (id, name, kind, workspace_id, created_at)
VALUES ('legacy-api-key', 'Legacy API Key', 'service', 'default', NOW())
ON CONFLICT (id) DO NOTHING;

-- 010: 기존 workspace.allowed_data_sources를 정책으로 환산
INSERT INTO access_policies (id, workspace_id, subject_type, subject_id,
                             connector_id, object_type, object_pattern,
                             actions, effect, priority)
SELECT gen_random_uuid(), w.id, 'service', 'legacy-api-key',
       src, 'connector', '*', '["query","read","search","list"]'::jsonb, 'ALLOW', 100
FROM workspaces w, jsonb_array_elements_text(w.allowed_data_sources::jsonb) AS src
ON CONFLICT DO NOTHING;

-- 012: config/data_sources.yaml의 기존 정의를 connectors로 이행
--      (애플리케이션 시작 시 자동 변환 로더가 수행, kind='database', driver='postgresql')
```

**호환성 계약**

1. 기존 74개 라우트는 **전부 동작을 유지**한다. 신규 라우트를 추가하고, 대체된 라우트에는 `Deprecation`·`Sunset` 헤더를 붙인다.
2. 기존 워크플로/에이전트/팀/잡템플릿 YAML은 **한 줄도 수정하지 않는다.**
3. `X-API-Key`만 보내는 기존 클라이언트는 `legacy-api-key` 서비스 계정으로 동작한다.
4. 인메모리 리포지토리도 신규 테이블을 동일하게 구현해 **213개 기존 테스트가 DB 없이 계속 통과**해야 한다.

---

## 12. API 명세 (신규)

### 12.1 커넥터

```http
GET    /connectors?workspace_id=&kind=&enabled=
POST   /connectors                          # ConnectorDefinition (version 규율 적용)
GET    /connectors/{id}
POST   /connectors/{id}/test-connection     # 자격증명 검증, 값 미반환
GET    /connectors/{id}/health
POST   /connectors/{id}/introspect          # 카탈로그 수집 (비동기)
POST   /connectors/{id}/query               # DB
POST   /connectors/{id}/search              # 문서/폴더
POST   /connectors/{id}/call                # API
```

### 12.2 자격증명

```http
POST   /credentials                         # {id, connector_kind, secret: {...}} → 값 즉시 암호화
PUT    /credentials/{id}                    # 회전 (version++)
DELETE /credentials/{id}
GET    /credentials                         # 메타데이터만. secret 절대 미반환
```

### 12.3 카탈로그

```http
GET    /catalog/datasets?connector_id=&q=
GET    /catalog/datasets/{id}
PATCH  /catalog/datasets/{id}               # 논리명, 설명, 분류등급
GET    /catalog/datasets/{id}/fields
PATCH  /catalog/fields/{id}
GET    /catalog/search?q=                   # 자연어로 데이터셋 찾기
```

### 12.4 권한·감사

```http
GET    /policies?workspace_id=&subject_id=&connector_id=
POST   /policies
DELETE /policies/{id}
POST   /policies/simulate                   # ★ 저장 전 시뮬레이션
       # {principal, connector_id, action, object} → {effect, matched, masked_columns}
GET    /audit/data-access?from=&to=&user_id=&connector_id=&status=&limit=&cursor=
GET    /audit/data-access/{id}
GET    /audit/data-access/export            # CSV/XLSX (내부감사 제출용)
```

`POST /policies/simulate`는 운영상 매우 중요하다. 정책은 잘못 설정하면 조용히 과다 노출되므로, **저장 전에 "이 사용자가 이 테이블을 볼 수 있는가"를 반드시 확인**할 수 있어야 한다.

### 12.5 오류 표현

`docs/ui/02_API_CONTRACT_AND_GAPS.md` 7절의 구조화 오류 봉투를 신규 API에 적용한다.

```json
{
  "error": {
    "code": "DATA_ACCESS_DENIED",
    "message": "해당 데이터 소스에 접근 권한이 없습니다.",
    "fields": [],
    "retryable": false,
    "details": {"connector_id": "prod-erp-mssql", "matched_policy": "pol-deny-hr"}
  }
}
```

---

## 13. 보안 설계 요약

| 위협 | 방어 |
|---|---|
| SQL 인젝션·권한 상승 | AST 파서 검증 + 방언별 denylist + 읽기전용 계정 + 스키마/테이블/컬럼 allowlist |
| 권한 우회 (As-Is Blocker) | 모든 접근 경로를 Gateway로 단일화 + AST 테스트로 우회 호출 금지 강제 |
| 프롬프트 인젝션 | 전 커넥터 `injection_notice` + 도구 출력 지시성 패턴 탐지 + L3 기본 미등록 |
| SSRF | base_url 고정, 엔드포인트 사전 정의, 사설망 명시 허용제 |
| 경로 이탈 | 기존 `_resolve` 방식 승계 + `os.path.realpath` 검증 + 심볼릭 링크 미추적 |
| 자격증명 유출 | 봉투 암호화, 평문 메모리 한정, 로그·API·프롬프트 마스킹, 회전 |
| 개인정보 노출 | 자동 PII 탐지 → 기본 restricted → 명시적 허용 필요 + 마스킹 기본값 |
| 감사 회피 | append-only 테이블, DB 롤에서 UPDATE/DELETE 미부여, 실패도 기록 |
| 기간계 부하 유발 | 읽기 복제본 권장, 커넥션 상한, 타임아웃, 동시성 쿼터, 일일 쿼터, 회로차단 |
| 대용량 응답으로 인한 OOM | 스트리밍 처리, 행수/바이트 상한, 잘림 명시 |

---

## 14. 테스트 전략

| 계층 | 대상 | 방식 |
|---|---|---|
| 단위 | SQL 가드 3방언 | 우회 시도 케이스 100+ (주석, 인코딩, 유니코드 동형, 중첩 CTE, 세미콜론 변형) |
| 단위 | 정책 엔진 | DENY 우선, 우선순위, 와일드카드 구체성, 행필터 AND 결합 |
| 단위 | 표 인제스트 | 헤더 탐지·타입 추론·병합셀·한국 관행 포맷 |
| 단위 | 문서 파서 | 포맷별 골든 파일 (HWP/HWPX 실패율 측정 포함) |
| 통합 | Gateway | 6단계 파이프라인 전 경로, 감사 기록 누락 없음 검증 |
| 통합 | 증분 동기화 | 신규/수정/삭제/이름변경/권한변경 시나리오 |
| **구조** | 접근 경계 | **AST 검사 — Gateway 외 `Connector.execute` 호출 금지** |
| 회귀 | 하위호환 | 기존 213개 테스트 전부 통과 + 기존 API 응답 스키마 동일성 |
| 성능 | 인제스트 | 10만 문서 색인 처리량, 메모리 상한 |
| 성능 | 검색 | 하이브리드 검색 p95 지연 |
| 품질 | 한국어 검색 | 실데이터 기반 Recall@5 / MRR 벤치마크셋 구축 |
| 보안 | 권한 | 사용자별 접근 매트릭스 자동 검증 |

**기존 인프라 재사용:** `examples/regression_suites/`, `examples/rubrics/`, `app/evaluation.py`의 회귀·품질 평가 체계를 데이터 계층 검증에도 그대로 쓴다.

---

## 15. 구현 순서 (Phase 매핑)

### Phase 1 — 신뢰 기반

```
1.  migrations 010, 011, 012 작성 + 인메모리 리포지토리 동등 구현
2.  app/access/principal.py, policy.py  (정책 엔진 + 시뮬레이터)
3.  app/access/audit.py                 (감사 기록, append-only)
4.  app/access/masking.py               (마스킹 규칙)
5.  app/access/gateway.py               (6단계 파이프라인)
6.  app/connectors/base.py, registry.py, credentials.py
7.  drivers/db_postgresql.py            (기존 datasources.py 이식)
8.  app/tools.py                        (db.query / file.read / knowledge.search → Gateway 경유)
9.  app/main.py                         (인증 미들웨어, 신규 라우트, 기존 라우트 Deprecation)
10. tests/test_access_boundary.py       (AST 경계 검사)
11. 하위호환 회귀 (기존 213 테스트 + API 스키마 동일성)
```

**게이트:** 기존 테스트 전부 통과 + 권한 매트릭스 검증 통과 + 감사 커버리지 100%

### Phase 2 — 데이터 연결 확장

```
12. sql_guard/ (parser, postgres, tsql, plsql)
13. drivers/db_mssql.py, db_oracle.py
14. app/catalog/ (수집기 3방언, 서비스, API)
15. migrations 013, 014
16. app/ingestion/ (파이프라인, 워커 확장)
17. app/parsers/ (xlsx, csv, hwp, hwpx, pptx, pdfplumber, ocr)
18. app/ingestion/tabular.py (표 인제스트 → 데이터셋)
19. drivers/folder.py + 증분 동기화
20. migrations 015 + 하이브리드 검색 + 리랭커
21. 한국어 검색 벤치마크셋 구축 및 튜닝
```

**게이트:** 실 고객 데이터로 Recall@5 목표 달성 + 10만 문서 인제스트 안정성

### Phase 3 — 업무 시스템 통합

```
22. drivers/rest_api.py + OpenAPI 임포트
23. api.call 도구 + L3 승인 연동
24. 데이터 접근 결재 워크플로 (human 노드 재사용)
25. 감사 하네스 (산출물 레지스트리 + 이벤트 로그 + 드리프트 재검증)
26. 데이터 소스 상태 대시보드
27. 프런트엔드 재구조화 (App.tsx 분해 + 커넥터/권한/감사 화면)
```

---

## 16. 미결정 사항 (확정 필요)

| # | 항목 | 선택지 | 영향 |
|---|---|---|---|
| U-1 | 인증 방식 | 자체 계정 / AD·LDAP / 네이버웍스·카카오워크 SSO | Phase 1 착수 전 필수 |
| U-2 | 마스터 키 관리 | 환경변수 / OS 키스토어 / HSM | 자격증명 저장소 설계 |
| U-3 | 표 데이터 저장 위치 | 플랫폼 PostgreSQL 별도 스키마 / DuckDB 파일 | 용량·격리·성능 트레이드오프 |
| U-4 | 형태소 분석기 | mecab-ko / kiwi / PostgreSQL 확장 | 배포 복잡도 (온프레미스 설치 난이도) |
| U-5 | 리랭커 구동 위치 | 로컬 GPU / CPU / 외부 API | 폐쇄망 요건과 직결 |
| U-6 | HWP 파싱 라이선스 | pyhwp(GPL 계열 확인 필요) / 자체 구현 / 상용 | **법무 검토 필요** |
| U-7 | OCR 엔진 | Tesseract / PaddleOCR / 국산 상용 | 한글 인식률 vs 라이선스 |
| U-8 | 앵커 고객 DB 분포 | — | MSSQL/Oracle 우선순위 결정 |

---

### 부록. 신규 모듈 배치도

```
app/
├── access/                 ★신규
│   ├── principal.py        Principal, 인증 컨텍스트
│   ├── policy.py           PolicyEngine, 평가 규칙, 시뮬레이터
│   ├── masking.py          마스킹 규칙 적용
│   ├── rewriter.py         요청 재작성 (컬럼 제거, RLS 주입, 상한)
│   ├── audit.py            감사 기록 (append-only)
│   └── gateway.py          DataAccessGateway
├── connectors/             ★신규
│   ├── base.py registry.py credentials.py health.py
│   ├── sql_guard/          base.py parser.py postgres.py tsql.py plsql.py
│   └── drivers/            db_postgresql.py db_mssql.py db_oracle.py
│                           file_upload.py folder.py rest_api.py
├── catalog/                ★신규
│   ├── service.py
│   └── collectors/         postgres.py mssql.py oracle.py tabular.py document.py
├── ingestion/              ★신규
│   ├── pipeline.py queue.py tabular.py document.py
├── parsers/                ★신규
│   ├── xlsx.py csv.py hwp.py hwpx.py pptx.py pdf.py ocr.py
├── retrieval/              ★신규
│   ├── hybrid.py bm25.py rerank.py synonyms.py
│
├── datasources.py          → deprecated, drivers/db_postgresql.py로 이식
├── knowledge.py            → 청킹/임베딩만 남기고 인제스트는 ingestion/으로 이관
├── external.py             → FileReadService는 drivers/folder.py로 이관
├── tools.py                → Gateway 경유로 내부 구현만 교체 (도구 ID 불변)
├── engine.py               → execution_context에 user_id/on_behalf_of 추가 (2줄)
├── main.py                 → 인증 미들웨어 + 신규 라우트
└── (그 외 기존 모듈 변경 없음)
```
