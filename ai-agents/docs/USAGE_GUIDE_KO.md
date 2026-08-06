# 실사용 가이드 (문서작성팀) — 첫 문서까지 30분

> **팀별 가이드:** 문서작성팀(이 문서) · [개발팀](./GUIDE_DEV_TEAM_KO.md) ·
> [퀀트 자문팀](./GUIDE_QUANT_TEAM_KO.md) · [동영상 제작팀](./GUIDE_VIDEO_TEAM_KO.md)


**엄두가 안 나는 이유는 시스템이 어려워서가 아니라, 시작점이 여러 개라서다.**
Docker·Postgres·워크스페이스·프리셋·MCP… 전부 필요해 보이지만 첫 문서를 만드는 데는
**하나도 필요 없다.** 이 가이드는 필요한 것만 순서대로 놓는다.

---

## 0. 큰 그림 — 3단계

| 단계 | 필요한 것 | 얻는 것 | 소요 |
|---|---|---|---|
| **1단계. 명령어** | Ollama만 | 실제 업무 문서 1건 | 30분 |
| 2단계. 반복 사용 | 위와 동일 | 업무 루틴에 편입 | — |
| 3단계. 웹 UI | 집PC + Docker | 화면에서 클릭으로 | 반나절 |

**1단계부터 하세요.** 3단계를 먼저 하려다 막히는 게 지금 상황입니다.

---

# 1단계 — 명령어로 첫 문서 (Docker 불필요)

## 1-1. 준비 확인 (5분)

```powershell
cd C:\workspace\universal_ai_agent_orchestrator

# Ollama 가 떠 있고 모델이 있는가
ollama list          # qwen3:8b 가 보여야 함

# 의존성 (최초 1회)
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 한글 깨짐 방지 — 매 세션마다
$env:PYTHONUTF8=1
```

## 1-2. 작업 폴더 만들기 (2분)

이미 폴더를 만들어 두셨다면 **구조만 맞추면 됩니다.** 규약은 단순합니다.

```
<참조 루트>/
  <작업 이름>/
    references/     ← 근거 자료 (필수)
    template/       ← 회사 양식 (선택)
    output/         ← 결과물
```

자동 생성:

```powershell
.\.venv\Scripts\python.exe -m cli.init_workspace `
    --root "C:\work\ai-docs" --work "wms-proposal"
```

> **`--root` 와 `--work` 를 나눈 이유:** 여러 작업이 한 루트를 공유해도 `work` 가 다르면
> 근거와 양식이 섞이지 않습니다. 작업이 늘어날 때 폴더를 새로 파지 않아도 됩니다.

## 1-3. 근거 자료 넣기 (10분) — **여기가 품질의 90%**

`references/` 에 자료를 넣습니다. 인식 확장자: `.md` `.txt` `.pdf` `.docx` `.csv` `.json`

**꼭 이해하고 넘어갈 것:** 이 시스템은 **references/ 에 없는 내용을 인용하지 못하도록**
구조적으로 막혀 있습니다(인용 무결성 계약). 그래서:

- 자료가 부실하면 → 확정 사실(FACT)이 적고 "확인 필요"(unknowns)가 많은 문서가 나옵니다.
  **이건 고장이 아니라 정상 동작입니다.** 다른 AI 도구였다면 그 빈칸을 그럴듯하게
  지어냈을 겁니다.
- 미확정 사항도 적어 두세요. "2호점 신설은 4분기 결정 예정, 현재 미확정" 같은 문장을
  넣으면 AI가 그걸 `unknowns` 로 분리해 줍니다.

좋은 근거 파일 예시:

```markdown
# 창고 현황 조사 (2026-07)

- 입출고를 수기 엑셀로 관리하며, 재고 실사 오차율이 월평균 7%다.
- 주문 1건당 평균 피킹 시간이 4.2분이다.
- 성수기 오출고 건수가 월 30건에 달해 반품 비용이 증가하고 있다.
- 물류센터 2호점 신설 여부는 2026년 4분기 결정 예정으로 현재 미확정이다.
```

## 1-4. 양식 넣기 (선택)

`template/` 에 회사 양식을 넣으면 **그 목차를 그대로 따릅니다.**
LLM이 아니라 코드가 결정적으로 파싱하므로 목차가 임의로 바뀌지 않습니다.

```markdown
# 제안서 양식
## 1. 현황 및 문제점
## 2. 개선 방향
## 3. 기대 효과
```

비워 두면 AI가 자유롭게 구성합니다.

## 1-5. 실행 (5분 + 대기)

```powershell
.\.venv\Scripts\python.exe -m cli.write_doc `
    --root "C:\work\ai-docs" `
    --work "wms-proposal" `
    --goal "현행 입고 프로세스를 진단하고 개선안을 제안" `
    --doc-type "WMS AS-IS/TO-BE 제안서" `
    --audience "고객사 물류팀장"
```

실행하면 먼저 **사전 점검**이 나옵니다. 여기서 막히면 실행 자체를 안 합니다.

```
  참조 루트   : C:\work\ai-docs
  작업 폴더   : C:\work\ai-docs\wms-proposal
  근거 자료   : 4건
  양식 파일   : 1건
  결과 폴더   : C:\work\ai-docs\wms-proposal\output
```

> ⏱ **로컬 8B 기준 첫 초안까지 수 분에서 십수 분** 걸립니다. 단일 노드 실측이 약 190초였고,
> 여기는 작성자 1명 + 리뷰어 3명이 최대 3라운드 도니까 그 몇 배입니다.
> **멈춘 게 아닙니다.** 처음엔 `--doc-type` 을 짧은 문서로 잡고 감을 잡으세요.

## 1-6. 검토·반려 — 이게 이 시스템의 핵심 기능

초안이 나오면 화면에 Markdown이 그대로 뜨고 멈춥니다.

```
  [Enter] 승인    |    고칠 점을 적고 [Enter] → 반려 후 재작성
  > 톤을 더 공식적으로. 기대 효과를 정량 수치로 바꿔주세요.
```

반려하면 **그 코멘트를 최우선으로 반영해 다시 씁니다.** 최대 4회.
`--auto-approve` 로 검토를 건너뛸 수 있지만, 첫 몇 번은 직접 보세요.

## 1-7. 결과

```
output/
  wms-proposal_20260804_1430.md          ← 이걸 읽으면 됩니다
  wms-proposal_20260804_1430_detail.json ← 근거·리뷰 이력 (감사용)
  _work/                                  ← 내부 파일 (신경 안 써도 됨)
```

실행할 때마다 타임스탬프로 쌓입니다. **덮어쓰지 않습니다.**

---

## 1-8. 첫 실행 후 반드시 할 것

산출물을 **납품 가능한 수준으로 고치는 데 걸린 시간을 재세요.**

```
RTR = 재작업 시간 ÷ 처음부터 직접 쓰는 시간
```

`verification/REWORK_PROTOCOL.md` 에 측정 절차와 기록 양식이 있습니다.
**이 숫자 하나가 "이걸 계속 쓸 가치가 있는가"에 답합니다.** 목표선은 0.4입니다.

---

# 2단계 — 업무 루틴에 편입

## 자주 쓰는 조합을 배치 파일로

`C:\work\ai-docs\제안서작성.bat`:

```bat
@echo off
chcp 65001 > nul
set PYTHONUTF8=1
cd /d C:\workspace\universal_ai_agent_orchestrator
.\.venv\Scripts\python.exe -m cli.write_doc ^
    --root "C:\work\ai-docs" ^
    --work "%1" ^
    --goal "%2" ^
    --doc-type "제안서" ^
    --audience "고객사 담당자"
pause
```

```powershell
.\제안서작성.bat wms-proposal "현행 입고 프로세스 진단 및 개선안"
```

## 문서 종류를 바꾸는 법

**같은 워크플로에 입력만 바꿉니다.** 새 코드가 필요 없습니다.

| 문서 | `--doc-type` | `--instructions` |
|---|---|---|
| 사업계획서 | `사업계획서(PSST)` | `Problem-Solution-Scale up-Team 순서로` |
| 분석 보고서 | `분석 보고서` | `결론을 먼저, 근거를 뒤에` |
| 마케팅 홍보문 | `마케팅 홍보문` | `기술용어 최소화, 3문단 이내` |
| 업무 매뉴얼 | `업무 매뉴얼` | `번호 매긴 절차 중심, 스크린샷 위치 표시` |
| 회의록 정리 | `회의록` | `결정사항·보류사항·담당자를 분리` |

## 품질이 안 나올 때 점검 순서

| 증상 | 원인 | 조치 |
|---|---|---|
| FACT가 거의 없고 unknowns만 많음 | 근거 부족 | `references/` 보강. **정상 동작입니다** |
| 목차가 회사 양식과 다름 | 양식 미인식 | `template/` 위치·확장자 확인 |
| 너무 일반론적 | goal이 추상적 | goal을 구체적으로. "개선안 제안" → "입고 검수 단계의 중복 확인 작업 제거 방안" |
| 해석 없이 사실만 나열 | 8B 모델의 알려진 약점 | `--hybrid` 로 비교. 차이가 크면 판단 역할만 Claude로 |
| 톤이 안 맞음 | | `--instructions` 에 명시. 반려 코멘트로도 교정됨 |

## 로컬 vs 하이브리드

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."
.\.venv\Scripts\python.exe -m cli.write_doc ... --hybrid
```

같은 작업을 양쪽으로 돌려 비교하세요. **이 차이가 온프레미스 전략의 성립 여부를 결정합니다.**
차이가 작으면 로컬만으로 제품이 됩니다.

---

# 3단계 — 웹 UI (집PC, Docker)

명령어가 익숙해진 다음에 하세요. UI는 편의지 필수가 아닙니다.

## 3-1. `.env` 설정

```dotenv
APP_API_KEY=본인이-정한-키
APP_DATABASE_URL=postgresql+asyncpg://agent:agent@db:5432/agent_platform
OLLAMA_API_BASE=http://host.docker.internal:11434

# ★ 참조 폴더 — 컨테이너 안 경로로 적어야 함 (아래 3-2 와 짝)
APP_FILE_READ_ROOTS=["/workspace/docs"]
APP_HOST_SOURCE_ROOT=C:/work/ai-docs
```

## 3-2. ⚠ 볼륨 마운트 — 여기서 대부분 막힙니다

**기본 `docker-compose.yml` 은 당신의 작업 폴더를 컨테이너에 넣어주지 않습니다.**
`docker-compose.dev.yml` 이 `APP_HOST_SOURCE_ROOT` 를 `/workspace/source` 로 마운트하지만,
문서 참조용으로 쓰려면 경로를 맞춰야 합니다. 가장 단순한 방법은 `docker-compose.override.yml` 추가:

```yaml
services:
  api:
    volumes:
      - type: bind
        source: ${APP_HOST_SOURCE_ROOT}
        target: /workspace/docs
        read_only: true
```

`.env` 의 `APP_FILE_READ_ROOTS` 와 `target` 이 **같아야** 합니다. 다르면 `file.read` 가
"path is outside the allowed work folders" 를 냅니다.

## 3-3. 기동

```powershell
docker compose up --build
# UI  : http://localhost:3000
# API : http://localhost:8000/docs
```

`.\scripts\windows\deploy-local.ps1` 은 테스트→빌드→재시작→버전검증을 한 번에 합니다.

## 3-4. UI 사용 흐름

1. 워크스페이스 생성 (최초 1회) — 사내 자료면 `model_policy: local_only`
2. 프리셋 카드에서 **문서작성팀** 선택
3. 폼 작성 → Job 생성 → 시작
4. 승인함에서 초안 검토 → 승인 또는 반려
5. 산출물 다운로드

> 카드가 안 보이면 `job_templates` 와 `preset_ui` 가 서로를 id+version으로 참조하는지
> 확인하세요. 둘 다 있어야 렌더링됩니다.

## 3-5. 자주 나는 실패

| 증상 | 원인 |
|---|---|
| `409 Conflict` (기동 실패) | 정의 YAML 내용만 바꾸고 `version` 을 안 올림 |
| `path is outside the allowed work folders` | 3-2의 마운트 경로 불일치 |
| Ollama 연결 실패 | `OLLAMA_API_BASE` 가 `localhost` (컨테이너에선 `host.docker.internal`) |
| 프리셋 카드 안 보임 | job_template ↔ preset_ui 상호참조 불일치 |

---

# 부록. 명령어 요약

```powershell
# 작업 폴더 생성
python -m cli.init_workspace --root <루트> --work <이름>

# 문서 작성
python -m cli.write_doc --root <루트> --work <이름> --goal "..." --doc-type "..." [--hybrid] [--auto-approve]

# 소스 분석 (개발팀, Docker 불필요)
python -m cli.analyze_source --repo <저장소> --goal "..." --focus "..." [--include <glob>...]

# 품질 검증 (실사용 아님, 측정용)
python -m verification.harness --configs local --scenarios document-wms
python -m verification.report verification/runs
```

| 문서 | 용도 |
|---|---|
| 이 문서 | 문서작성팀 실사용 |
| `docs/GUIDE_DEV_TEAM_KO.md` | 개발팀 (소스분석 · 코드생성) |
| `docs/GUIDE_QUANT_TEAM_KO.md` | 퀀트 자문팀 |
| `docs/GUIDE_VIDEO_TEAM_KO.md` | 동영상 제작팀 |
| `verification/README.md` | 품질 측정 하니스 |
| `verification/REWORK_PROTOCOL.md` | 합격 판정 기준 (RTR) |
| `DOCUMENT_TEAM_GUIDE.md` | 문서팀 API 레벨 상세 |
| `docs/EXTENSION_ANALYSIS.md` | 기능 확장 타당성 |
| `docs/FRONTEND_REVIEW.md` | 웹 UI 코드 리뷰 |
