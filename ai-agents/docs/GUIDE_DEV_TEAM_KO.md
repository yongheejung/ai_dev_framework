# 개발팀 사용 가이드

- 대상 팀: `dev-team` (분석가 · 설계자 · 코더 · 코드리뷰어 · 보안검토 · 논리비평 · 품질평가)
- 형제 문서: [`USAGE_GUIDE_KO.md`](./USAGE_GUIDE_KO.md) (문서작성팀)

---

## 0. 두 가지 모드 — 요구 조건이 다릅니다

개발팀에는 성격이 아주 다른 두 작업이 있습니다. **이 차이를 먼저 이해해야 합니다.**

| | **소스 분석** | **코드 생성** |
|---|---|---|
| Job Template | `source-analysis-job` | `code-build-job` |
| Workflow | `source-analysis-v1` | `code-build-v1` |
| 하는 일 | 코드를 **읽고** 구조·위험·테스트 공백·변경 후보 도출 | 코드를 **쓰고** 샌드박스에서 테스트·리뷰 |
| 부작용 등급 | L1 (산출물만) | **L2 (샌드박스 실행)** |
| 실행 모드 | balanced | **quality** (L2는 quality에서만 허용) |
| Docker | **불필요** | **필수** |
| 작업PC에서 | 🟢 **오늘 바로 가능** | 🔴 불가 |

> **먼저 소스 분석부터 하세요.** 코드를 바꾸지 않으니 안전하고, 오늘 바로 돌아가고,
> 결과물(변경 후보·테스트 공백)이 코드 생성의 입력이 됩니다. 순서가 설계에 반영돼 있습니다 —
> 분석 결과에 `development_handoff.suggested_template_id: code-build-job` 이 들어 있습니다.

---

# 1부. 소스 분석 (Docker 불필요)

## 1-1. 실행

```powershell
cd C:\workspace\universal_ai_agent_orchestrator
$env:PYTHONUTF8=1

python -m cli.analyze_source `
    --repo "C:\workspace\my-project" `
    --goal "결제 모듈의 예외 처리와 회귀 위험을 분석" `
    --focus "보안, 트랜잭션 경계, 테스트 공백" `
    --include "app/payment/**/*.py" "app/models/*.py"
```

사전 점검이 먼저 나옵니다.

```
  저장소     : C:\workspace\my-project
  파일 패턴  : app/payment/**/*.py, app/models/*.py
  매칭 파일  : 23개 (상위 20개까지 읽음)
  결과 폴더  : ...\analysis-output
```

## 1-2. ⚠ `--max-files` 를 줄이지 마세요 — 실측으로 확인된 함정

`code.read` 는 **저장소 이해에 중요한 파일을 우선순위로 먼저 넣습니다.**

```python
# app/external.py:41
_SOURCE_PRIORITY_NAMES = {
    "readme.md", "pyproject.toml", "requirements.txt", "package.json",
    "dockerfile", "docker-compose.yml", "pom.xml", "build.gradle", "go.mod", ...
}
```

이 파일들은 `--include` 패턴과 **무관하게** 슬롯을 먼저 차지합니다. 실측 결과:

| `--max-files` | 결과 |
|---|---|
| 5 | 읽은 5개가 전부 우선순위 파일. **요청한 파일이 하나도 안 읽힘** ✗ |
| 20 (기본) | 16개 읽음, 요청 파일 포함 ✓ |

**즉 `--max-files 5` 같이 줄이면 정작 분석하려던 코드는 안 읽고 Dockerfile만 분석합니다.**
기본값 20을 유지하세요. 큰 저장소는 오히려 **늘리세요**(최대 100).

## 1-3. 근거는 코드 자체입니다

```yaml
# source_analysis.yaml
evidence_path: source_snapshot.evidence
require_evidence: true
```

문서작성팀과 달리 **참고 자료를 따로 넣지 않아도 됩니다.** 읽어들인 코드 발췌가 곧 근거이며,
인용 ID는 `source:0`, `source:1` … 형태입니다. 분석가는 **읽지 않은 파일을 근거로 주장할 수 없습니다.**

설계서·DB 문서를 추가로 근거에 넣고 싶으면:

```powershell
--reference-globs "docs/**/*.md" "docs/erd/*.pdf"
```

## 1-4. 비밀값은 자동으로 가려집니다

```python
# app/external.py — 민감 파일은 아예 제외, 코드 안 비밀값은 <redacted>
_SENSITIVE_NAMES / _SENSITIVE_SUFFIXES  → redacted_files 로 별도 보고
_SECRET_ASSIGNMENT                       → api_key = "..." → api_key = "<redacted>"
```

결과 JSON의 `redacted_files` 에 제외된 파일 목록이 남습니다. **고객사 저장소를 분석할 때
이 목록을 먼저 확인**하세요.

## 1-5. 검토·반려

분석서가 나오면 멈춥니다. 최대 3회까지 반려하며 다시 분석시킬 수 있습니다.

```
  [Enter] 승인    |    보완할 점을 적고 [Enter] → 반려 후 재분석
  > 트랜잭션 롤백 경로를 더 구체적으로. 테스트 공백은 파일별로 나눠주세요.
```

## 1-6. 결과물

```
analysis-output/
  my-project_분석_20260804_1430.md            ← 사람이 읽는 분석서
  my-project_개발인계_20260804_1430.json      ← ★ 코드 생성의 입력
  my-project_분석_20260804_1430_detail.json
```

**개발인계 JSON이 핵심입니다.**

```json
{
  "suggested_template_id": "code-build-job",
  "change_candidates": [{"path": "app/payment/service.py", "reason": "..."}],
  "test_gaps": ["환불 실패 경로 테스트 없음"],
  "unknowns": ["외부 PG사 타임아웃 정책 확인 필요"]
}
```

`unknowns` 를 먼저 보세요. **AI가 "모른다"고 표시한 것**이며, 여기를 사람이 채워야 다음 단계가 정확해집니다.

---

# 2부. 코드 생성 (Docker 필수)

## 2-1. ⚠ 사전 준비 — 안 하면 100% 실패

`LIVE_VERIFICATION_RUNBOOK.md` 5-0절에 적힌 그대로입니다. **가장 흔한 실패가 여기입니다.**

```powershell
# 1) 샌드박스 이미지 빌드 — 기본 python:3.12-slim 에는 pytest 가 없어 exit 127 이 납니다
docker build -f docker/code-sandbox.Dockerfile -t orchestrator-code-sandbox:latest .
```

```dotenv
# 2) .env
APP_CODE_EXEC_ENABLED=true
APP_CODE_EXEC_IMAGE=orchestrator-code-sandbox:latest
APP_CODE_READ_ROOTS=["/workspace/source"]
APP_HOST_SOURCE_ROOT=C:/workspace/my-project
```

```powershell
# 3) dev compose 로 기동 (호스트 저장소를 읽기 전용 마운트 + docker.sock)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## 2-2. 샌드박스 단독 확인 — 실패 확률이 가장 높은 지점부터

전체 사이클을 돌리기 전에 `code.exec` 만 태워 보세요.

- ✅ `exit_code: 0` + stdout 에 pytest 출력 → 준비 완료
- ❌ `exit_code: 127` → 이미지 미빌드/미지정. 2-1로 돌아가세요

## 2-3. 실행 (웹 UI)

```
대시보드 → 시스템 개발팀 → 개발 작업 → "코드 생성" 선택
```

실행 모드는 **자동으로 `quality`** 로 고정됩니다. `balanced` 로 바꾸면
`node verify requires L2` 오류가 납니다. L2는 quality 모드에서만 허용되기 때문입니다.

## 2-4. ⭐ 이 사이클이 돌면 개발팀이 "검증된 L2"입니다

`code-build-v1` 의 루프는 이렇게 돕니다.

```
context(기존 코드 주입) → write(코드 작성) → verify(샌드박스 테스트 실행)
                              ↑                      ↓
                              └──── test_result ─────┘   ← ★ 여기가 핵심
                          review(리뷰) → approve(사람 승인) → save_files
```

**검증 포인트: 일부러 실패하는 테스트를 유도하세요.** 아직 없는 함수를 호출하는 테스트를
포함한 goal 을 주고, **2회차 `write` 가 `test_result` 를 보고 실패를 고치는지** 확인합니다.
이게 되면 자율 수정 루프가 실제로 동작한다는 증거입니다. 안 되면 그냥 코드 생성기입니다.

## 2-5. 안전 경계

- 생성 파일은 **TAR 스트림**으로 일회용 컨테이너에 전달됩니다 (호스트 마운트 없음)
- 샌드박스는 네트워크 차단, 루트 파일시스템 읽기 전용, 비루트 사용자, CPU·메모리·PID 제한
- 허용 명령만 실행: `pytest`, `python`, `python -m pytest`, `ruff`, `mypy`
- **승인해도 원본 저장소는 바뀌지 않습니다.** 결과는 Artifact 저장소에 저장됩니다

---

## 3. 자주 나는 실패

| 증상 | 원인 | 조치 |
|---|---|---|
| 요청한 파일이 분석에 없음 | `--max-files` 가 작아 우선순위 파일이 슬롯 점유 | 20 이상 유지 (1-2절) |
| `code.read is not configured` | `APP_CODE_READ_ROOTS` 누락 | .env 확인 |
| `exit_code: 127` (pytest not found) | 샌드박스 이미지 미빌드 | 2-1 |
| `node verify requires L2` | 실행 모드를 balanced 로 지정 | quality 로 |
| 분석이 일반론적 | goal 이 추상적 | "코드 분석" → "환불 처리의 트랜잭션 롤백 경로에 누락이 있는지" |
| 인용 위반 경고 | 읽지 않은 파일을 근거로 주장 | 정상 동작 (막고 있는 것) |

---

## 4. 실사용 판정

첫 분석서를 받으면 **바로 쓰지 말고 재작업 시간을 재세요.**

```
RTR = 분석서를 쓸만하게 고치는 시간 ÷ 직접 코드 읽고 분석하는 시간
```

개발팀의 "완료" 기준은 **"지적된 위험이 실제 코드에 존재하고, 개선안이 바로 착수 가능한 수준"**
입니다. 실제로 없는 위험을 지적했다면(환각) 그건 인용 위반이므로 하니스가 잡아야 합니다.

측정 절차: [`verification/REWORK_PROTOCOL.md`](../verification/REWORK_PROTOCOL.md)

---

## 5. 명령어 요약

```powershell
# 소스 분석 (Docker 불필요)
python -m cli.analyze_source --repo <저장소> --goal "..." --focus "..." [--include <glob>...]
                             [--reference-globs <glob>...] [--max-files 20] [--hybrid] [--auto-approve]

# 품질 측정
python -m verification.harness --configs local --scenarios source-analysis code-build
```
