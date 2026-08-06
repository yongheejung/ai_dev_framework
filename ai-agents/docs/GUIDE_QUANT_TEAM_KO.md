# 퀀트 자문팀 사용 가이드

- 대상 팀: `quant-advisory` (성과분석 · 청산위험검토 · ML무결성검토 · 논리비평 · 자문작성)
- **설정·활성화는 [`QUANT_ADVISORY_SETUP.md`](../QUANT_ADVISORY_SETUP.md) 를 먼저 읽으세요.** 이 문서는 *사용*을 다룹니다.
- 형제 문서: [`USAGE_GUIDE_KO.md`](./USAGE_GUIDE_KO.md), [`GUIDE_DEV_TEAM_KO.md`](./GUIDE_DEV_TEAM_KO.md)

---

## 0. 이 팀은 다른 팀과 근본적으로 다릅니다

| | 문서·개발팀 | **퀀트 자문팀** |
|---|---|---|
| 근거 | 문서 / 코드 (텍스트) | **SQL 집계 결과 (숫자)** |
| LLM의 역할 | 생성 | **해석만** |
| 실행 요건 | 파일 폴더 | **PostgreSQL 라이브 연결** |
| Docker 없이 | 🟢 가능 | 🔴 불가 (DB 필요) |

### 설계 원칙 — 반드시 이해하고 쓰세요

> **계산은 전부 SQL이 한다. LLM은 이미 계산된 표를 해석만 한다.**
> **SQL은 워크플로에 고정한다. LLM이 SQL을 생성하지 않는다.**

`examples/workflows/quant_advisory.yaml` 상단 주석에 그대로 적혀 있습니다. 이유는 단순합니다 —
**조인 하나가 틀리면 수치가 조용히 틀리고**, 지표 정의가 흔들리면 회차 간 비교가 무의미해집니다.

그래서 이 팀에서 LLM이 틀릴 수 있는 범위는 **"맞는 숫자를 잘못 해석하는 것"** 뿐입니다.
숫자 자체를 지어낼 수는 없습니다. 이게 이 팀의 안전장치이자 한계입니다.

### 🔴 절대 하지 않는 것

- **주문 실행 도구를 등록하지 않습니다.** AI가 매매하지 않습니다.
- **전략 자동 수정 노드를 두지 않습니다.** 최종 판단은 사람이 합니다.
- 산출물은 **사람이 읽는 리포트뿐**입니다.

이건 설계 결정이지 미구현이 아닙니다. `ARCHITECTURE_V072.md` 에도 명시돼 있습니다.
**확장할 때도 이 경계를 넘지 마세요.**

---

## 1. 실행 전 확인 (매번)

```powershell
# 데이터소스가 켜져 있고 접속정보가 있는가
curl -s -H "X-API-Key: $env:APP_API_KEY" http://localhost:8000/data-sources | ConvertFrom-Json
```

```
enabled: true              ← config/data_sources.yaml 의 quant-db
credentials_configured: true ← .env 의 APP_QUANT_DB_URL
```

둘 중 하나라도 false면 실행이 실패합니다. 활성화 절차는 `QUANT_ADVISORY_SETUP.md` 2~4절.

> **SELECT 전용 롤을 쓰세요.** `db.query` 가 읽기 트랜잭션을 강제하지만,
> **계정 권한 최소화가 마지막 방어선**입니다. 이건 타협 대상이 아닙니다.

---

## 2. 실행

```powershell
$K = $env:APP_API_KEY
$body = @{
  use_case_id = "quant-advisory"
  inputs = @{
    username        = "내계정"
    period_days     = 90
    signal_user_id  = "default"
    focus           = "최근 손실이 특정 전략에 몰렸는지"
  }
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8000/runs `
  -Headers @{ "X-API-Key" = $K; "Content-Type" = "application/json" } -Body $body
```

또는 웹 UI의 **퀀트 자문팀** 카드에서 (프리셋 카드가 보이려면 job_template과 preset_ui가 짝을 이뤄야 합니다).

### 입력 파라미터

| 키 | 필수 | 기본 | 설명 |
|---|---|---|---|
| `username` | ✅ | — | 조회 대상 계정 |
| `period_days` | | 90 | 분석 기간 |
| `signal_user_id` | | `default` | **`signal_*` 테이블은 키가 `user_id`** (username이 아님) |
| `source_id` | | `quant-db` | 데이터소스. PAPER→LIVE 전환은 `.env` URL 교체 |
| `focus` | | "" | 이번에 특별히 보고 싶은 질문 |

> `focus` 를 잘 쓰세요. 11개 집계표는 항상 같지만, **어느 표에 무게를 둘지**가 바뀝니다.
> "최근 손실이 특정 전략에 몰렸나", "조기청산 때문에 알파를 잃고 있나" 같이 구체적으로.

---

## 3. 산출물을 읽는 법

### 3-1. 11개 집계표가 답하는 질문

| 노드 | 답하는 질문 | 주의해서 볼 것 |
|---|---|---|
| `bucket_perf` | 전략·버킷별 승률/평균 R | **표본 수(sample_count)**. 20건 미만이면 해석 금지 |
| `exit_quality` | 청산 사유별 이익 반납·손실 통제 | `STOP_LOSS` 평균이 계획 손절폭보다 크면 슬리피지 문제 |
| `entry_quality` | 국면·등급별 계획 RR 대비 실제 R | 계획-실제 괴리가 크면 진입 타이밍 문제 |
| `post_exit` | **판 뒤에 더 올랐나** (조기청산 알파 손실) | 여기가 크면 청산 규칙을 의심 |
| `candidate_outcome` | **안 산 후보가 더 나았나** (기회비용) | 필터가 과도한지 판단 |
| `shadow_eval` | 섀도우 전략 대비 실제 엣지 | 엣지가 0에 수렴하면 전략 수명 종료 신호 |
| `signal_power` | 시그널의 구간별 예측력 유지 | 최근 구간만 무너졌으면 국면 변화 |
| `ml_status` | 모델 auc/brier 추세 | 학습 기간과 실거래 기간이 겹치면 무의미 |
| `feature_ic` | 피처 IC 부호 반전·유의성 악화 | 부호 반전은 즉시 확인 대상 |
| `label_quality` | 텍스트 라벨 유효 비율·버전 혼재 | 버전 혼재면 위 해석 전부 흔들림 |
| `data_integrity` | **위 해석을 믿어도 되는 데이터인가** | ⭐ **이걸 제일 먼저 보세요** |

### 3-2. 읽는 순서 — 역순으로 읽으세요

```
1. data_integrity   ← 데이터를 믿을 수 있나?  아니면 나머지는 볼 필요 없음
2. label_quality    ← 라벨 버전이 섞였나?
3. bucket_perf      ← 표본이 충분한가?
4. 그 다음에 나머지 해석
```

**리포트의 결론부터 읽지 마세요.** 데이터 무결성이 깨진 상태에서 나온 결론은
그럴듯할수록 위험합니다.

### 3-3. 주장 유형을 구분해서 보세요

다른 팀과 동일하게 FACT / INFERENCE / RECOMMENDATION / UNKNOWN 계약이 적용됩니다.

- **FACT** — 집계표에 실제로 있는 숫자. 인용 ID가 붙습니다
- **INFERENCE** — 표에서 끌어낸 해석. **여기가 틀릴 수 있는 자리입니다**
- **RECOMMENDATION** — 제안. 사람이 판단할 대상
- **UNKNOWN** — 데이터로 답할 수 없는 것. **여기를 먼저 읽으세요**

---

## 4. 알려진 주의사항

`QUANT_ADVISORY_SETUP.md` 의 "알려진 확인 필요 사항"을 요약합니다. **첫 실행 때 반드시 확인:**

1. **날짜 컬럼이 TEXT입니다.** `public` 스키마의 `created_at`, `exit_time` 등이 TEXT라
   `substr(컬럼,1,10) >= ...` 로 비교합니다. 저장 포맷이 `YYYY-MM-DD` 로 시작한다는 전제입니다.
   **한 건 뽑아서 확인하세요.** 포맷이 다르면 기간 필터가 조용히 전부/전무가 됩니다.
2. **`require_evidence: true`** 라서 `bucket_perf` 가 비면 진단이 실패합니다.
   **의도된 동작입니다** — 근거 없이 자문하면 안 됩니다.
3. **`analytics` 뷰 이름이 `paper_*`** 입니다. LIVE 통합 후 이름이 바뀌면 쿼리를 맞춰야 합니다.
4. **`max_rows` 가 200** 이라 모든 쿼리는 집계를 반환하도록 짜여 있습니다. 원시 행을 뽑지 마세요.

### SQL을 수정할 때 — 가드레일

워크플로 YAML의 `sql:` 블록을 고칠 일이 생기면:

- `SELECT` 또는 `WITH` 로만 시작
- 단일 문장 (`;` 포함 시 거부)
- **SQL 주석 절대 금지** (`--`, `/* */`). YAML 안에 설명을 달고 싶어도 넣으면 실행이 막힙니다
- `pg_catalog`, `information_schema` 참조 금지
- **SQL 내용을 바꾸면 워크플로 `version` 을 올려야 합니다.** 안 그러면 `409 Conflict`

---

## 5. 자주 나는 실패

| 증상 | 원인 |
|---|---|
| `data source is disabled` | `config/data_sources.yaml` 의 `quant-db.enabled: false` |
| `data source environment variable is missing` | `.env` 의 `APP_QUANT_DB_URL` 없음 |
| `PostgreSQL data source URL must use postgresql...` | SQLite 경로를 넣음. **SQLite는 연결 불가** |
| `SQL comments ... are not allowed` | 쿼리에 `--` 주석 |
| 진단이 빈 결과로 실패 | `bucket_perf` 가 0행 (데이터 미적재 또는 날짜 필터 오작동 → 4-1 확인) |
| 기간 필터가 전부/전무 | 날짜 TEXT 포맷 불일치 (4-1) |
| `409 Conflict` | SQL 바꾸고 version 안 올림 |

---

## 6. 실사용 판정

퀀트팀의 "완료" 기준: **표에 있는 수치만 인용하고, 결론이 표와 모순되지 않을 것.**

이 팀은 RTR(재작업 시간)보다 **정확성 검증**이 우선입니다. 첫 몇 회는 이렇게 하세요.

1. 리포트의 FACT 주장 3개를 골라 **직접 SQL로 확인**
2. INFERENCE가 표와 논리적으로 이어지는지 확인
3. **표에 없는 숫자가 등장하면 즉시 보고**하세요. 인용 무결성이 뚫린 것입니다

셋 다 통과하면 그때부터 시간을 재도 됩니다.

> **투자 판단은 사람이 합니다.** 이 리포트는 정보이지 조언이 아닙니다. 저는 투자 자문가가 아니며,
> 이 시스템의 산출물도 마찬가지입니다. 실제 매매 결정 전에 본인이 근거를 검증하세요.

---

## 7. 하지 않은 것

- **DB 적재.** `db.query` 는 L0_READ라 쓰기가 불가능합니다. 결과는 `file.write` 로 아티팩트에만 저장됩니다.
  `vector_data.agent_reports` 로 넣으려면 별도 적재 경로가 필요합니다.
- **주문 실행·전략 자동 수정.** 0절 참고. 설계상 만들지 않습니다.
