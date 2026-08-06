# 프론트엔드 코드 리뷰 — Orbit Console

- 대상: `frontend/` (App.tsx 1,300 LOC, api.ts 216 LOC, React 19 + Vite 6 + nginx)
- 리뷰일: 2026-08-04
- 방법: 전체 정독 + 백엔드 API 74개 라우트·워크플로 정의와 교차 검증

---

## 총평

**만듦새는 개인 프로젝트 수준을 넘습니다.** 구조가 일관되고, 상태 관리가 단순 명료하고,
API 계약을 정확히 따르고 있으며, 보안 설계(아래)는 상용 제품에서도 자주 틀리는 부분을
제대로 했습니다.

**그런데 실사용에는 두 개의 Blocker가 있습니다.** 둘 다 "기능이 없다"가 아니라
"첫 사용자가 반드시 부딪히는데 안내가 없다"는 종류입니다. 데모로는 훌륭하고
실사용에는 이 둘을 고쳐야 합니다.

| 판정 | |
|---|---|
| 작동하는가 | 🟢 **작동합니다.** API 계약 일치, 배포 구성 정상 |
| 쓸만한가 | 🟢 **Blocker 2건 수정 완료 (2026-08-04)** — 아래 "수정 내역" 참고 |
| 버릴 것인가 | 🟢 **아닙니다.** 고쳐 쓰는 게 맞습니다 |

> **2026-08-04 업데이트:** B-1, B-2를 수정하고 `tsc -p tsconfig.app.json --noEmit` 타입 체크를
> 통과시켰습니다. 상세는 문서 끝의 [수정 내역](#수정-내역-2026-08-04).

---

## 잘한 것 — 유지해야 할 설계

### 1. API 키가 브라우저에 노출되지 않습니다 ⭐

```nginx
location /api/ {
    proxy_pass http://api:8000/;
    proxy_set_header X-API-Key "${APP_API_KEY}";
}
```

키를 **nginx가 서버 측에서 주입**합니다. 브라우저 번들에도, localStorage에도 키가 없습니다.
개인용 도구에서 여기까지 하는 경우는 드뭅니다. `docs/ui/02_API_CONTRACT_AND_GAPS.md` 의
"API Key는 세션 메모리에만, localStorage 영구 저장 비활성화" 원칙을 한 단계 더 강하게 구현했습니다.

### 2. 품질 게이트가 UI까지 관통합니다 ⭐

```tsx
const qualityFailed = task.message.includes("문서 품질 게이트: **FAIL**");
<button disabled={busy || qualityFailed} title="품질 게이트 통과 후 승인할 수 있습니다.">
```

게이트를 통과하지 못한 문서는 **승인 버튼 자체가 눌리지 않습니다.** 백엔드 설계 의도가
화면까지 이어진 좋은 사례입니다. (다만 구현 방식에 문제가 있습니다 — M-4 참고)

### 3. 반려에 코멘트를 강제합니다

```tsx
if (decision === "reject" && !comment.trim()) {
  setError("반려할 때는 수정 의견을 입력해 주세요.");
}
```

의견 없는 반려는 재작성 루프를 무의미하게 만듭니다. 정확한 판단입니다.

### 4. 구성 탐색기가 읽기 전용

Team/Agent/Workflow/Template을 볼 수는 있지만 고칠 수는 없습니다.
버전 승급 규율을 UI에서 우회할 수 없게 만든 올바른 선택입니다.

### 5. 그 외

- TypeScript `strict: true`
- 프리셋 카드가 `preset-ui` 응답이 없으면 "준비 중"으로 폴백 (`PRESET_FALLBACKS`)
- 모바일/태블릿 반응형 셸, `aria-label` 대체로 성실
- 실행 계약 고정(configuration snapshot) 안내를 UI에 노출

---

## 🔴 Blocker — 실사용 전 반드시 수정

### B-1. 기본 경로가 100% 실패로 끝납니다

**재현:** 새 사용자가 UI를 엽니다 → `문서작성팀` 카드 → `새 문서` → 작성 목표만 입력 →
`문서 작업 시작` → **실행이 실패합니다.**

**원인:** 폼의 기본값은 `collection = "default"` 인데, **UI에 Knowledge 업로드 화면이 없습니다.**

```bash
$ grep -c "knowledge" frontend/src/App.tsx frontend/src/api.ts
frontend/src/App.tsx:0
frontend/src/api.ts:0
```

그리고 워크플로는 근거가 0건이면 진행을 막습니다.

```yaml
# examples/workflows/document_build.yaml
- id: evidence_ready
  tool: reference.require
  args:
    evidence_count: $nodes.evidence.evidence_count
    minimum: 1          # ← 0건이면 ValueError
```

즉 사용자는 참고 폴더나 URL을 **반드시** 지정해야 하는데, 폼에서는 둘 다 선택 항목처럼 보입니다.
그래서 첫 실행이 실패하고, 실패 메시지는 Job 목록 안쪽에 있어서 원인을 찾기도 어렵습니다.

**수정안 (셋 중 하나, 위쪽이 저렴)**

1. **폼에서 사전 차단** — 참고 폴더·URL·웹검색이 모두 비었으면 제출 버튼을 막고
   "근거가 최소 하나 필요합니다" 안내. **가장 싸고 효과가 큽니다.**
2. 근거 요약 배지 — "선택된 근거: 폴더 1개(12개 파일)" 를 폼에 실시간 표시
3. Knowledge 업로드 화면 추가 (`POST /knowledge/documents`, `PUT .../content` 이미 있음)

### B-2. SSE가 끊기면 화면이 멈춥니다

```tsx
source.onerror = () => source.close();   // App.tsx:1033
```

**닫기만 하고 재연결도, 폴링 폴백도 없습니다.** 그리고 이 코드 외에 주기 갱신이 없습니다.

```bash
$ grep -n "setInterval\|EventSource\|onerror" frontend/src/App.tsx
1016:    const source = new EventSource(...)
1033:    source.onerror = () => source.close();
```

**왜 심각한가:** 로컬 8B로 문서 하나를 만드는 데 **수 분에서 십수 분**이 걸립니다
(작성자 1 + 리뷰어 3 × 최대 3라운드). 그동안 SSE 연결이 한 번이라도 끊기면 —
프록시 타임아웃, 절전, 네트워크 흔들림 — 화면은 **영원히 이전 상태로 멈춥니다.**
사용자는 실행이 죽은 줄 알고 다시 실행하게 됩니다.

백엔드는 이미 재연결을 지원합니다. `docs/ui/02_API_CONTRACT_AND_GAPS.md` 3.6절에
"단조 증가 `id`, `Last-Event-ID` 또는 `after` 지원, heartbeat" 가 **구현 완료**로 적혀 있습니다.
**클라이언트만 안 쓰고 있습니다.**

**수정안**

```tsx
source.onerror = () => {
  source.close();
  // 폴백: 실행이 끝날 때까지 주기 폴링
  const timer = window.setInterval(() => {
    void load();
  }, 5000);
  return () => window.clearInterval(timer);
};
```

최소한 폴링 폴백만 넣어도 "멈춘 것처럼 보이는" 문제는 사라집니다.
제대로 하려면 `Last-Event-ID` 기반 재연결까지.

---

## 🟡 Major — 기능이 죽어 있거나 취약

### M-1. 회사 양식(template) 기능이 UI에서 사용 불가

```bash
$ grep -c "work_dir\|template_globs" frontend/src/App.tsx
0
```

`document_build.yaml` 에는 `work_dir` 과 `template_globs` 입력이 있고, `template.parse` 노드가
**LLM 없이 결정적으로** 양식 목차를 파싱해 작성자에게 강제합니다. 이게 이 시스템의
차별점 중 하나("구조는 계약")인데 **UI에서 아예 보내지 않습니다.**

`examples/preset_ui/document-job.yaml` 의 `field_order` 에도 두 필드가 없어서, 프리셋 정의
차원에서도 빠져 있습니다.

**영향:** UI로는 회사 양식을 강제할 수 없습니다. CLI(`cli/write_doc.py`)로는 됩니다.
**같은 제품인데 경로에 따라 기능이 다릅니다.**

**수정안:** 폼에 "작업 폴더" 필드 하나를 추가하고 `work_dir` 로 보냅니다. 그러면
`references/` 와 `template/` 하위폴더 관례가 자동으로 동작합니다. `reference_globs` 를
손으로 조립하는 현재 코드(App.tsx:586-588)보다 오히려 단순해집니다.

### M-2. 한 곳이 느리면 대시보드 전체가 죽습니다

```tsx
const [healthData, workspaceData, presetData, ...] = await Promise.all([
  api.health(), api.workspaces(), api.presets(), api.approvals(),
  api.teams(), api.agents(), api.workflows(), api.templates(),
]);
// 실패하면 → setState("error") → 화면 전체가 "Core가 응답하지 않습니다"
```

8개 중 **하나만 실패해도** 전체가 연결 실패 화면으로 갑니다. 예를 들어 `preset-ui` 정의
하나가 잘못돼서 500이 나면, 작업 목록도 승인함도 못 봅니다.

`request()` 의 `AbortSignal.timeout(12000)` 도 여기에 물립니다. `/health/dependencies` 는
Ollama를 핑하는데(`check_ollama` 타임아웃 5초) 엔드포인트가 늘어나면 12초에 근접할 수 있습니다.

**수정안:** `Promise.allSettled` 로 바꾸고, 실패한 조각만 해당 패널에 표시합니다.
연결 실패 화면은 `api.workspaces()` 같은 **핵심 호출이 실패했을 때만** 띄웁니다.

### M-3. 페이지네이션이 구현되지 않았습니다

```tsx
jobs: (workspaceId) => request<ApiPage<Job>>(`/jobs/page?...&limit=100`),
runs: (workspaceId) => request<ApiPage<Run>>(`/runs?...&limit=100`),
```

타입에 `next_cursor: string | null` 이 있는데 **아무도 읽지 않습니다.**
작업이 100건을 넘으면 조용히 잘리고, 사용자는 알 수 없습니다.

부작용도 있습니다. `RunWorkspace` 는 `runs.find(item => item.id === job.run_id)` 로 Run을
찾는데, 오래된 Job의 Run이 100건 밖이면 못 찾습니다 → `runStatus` 가 `undefined` →
**SSE가 시작되지 않습니다**(App.tsx:1015 조건).

**수정안:** 최소한 "최근 100건만 표시 중" 배지. 제대로 하려면 무한 스크롤 또는 페이지 버튼.

### M-4. 품질 게이트 차단이 한글 문자열 매칭에 의존합니다

```tsx
const qualityFailed = task.message.includes("문서 품질 게이트: **FAIL**");
```

백엔드:
```python
# app/tools.py:308
quality_lines = [f"> 문서 품질 게이트: **{quality_status}**"]
```

**렌더러 문구를 한 글자만 바꾸면 승인 차단이 조용히 무력화됩니다.** 테스트도 이걸 못 잡습니다.
품질 통제 장치가 UI 문자열에 매달려 있는 건 위험합니다.

**수정안:** `HumanTaskRecord` 에 구조화 필드를 추가합니다. `docs/ui/02_API_CONTRACT_AND_GAPS.md`
4절이 이미 정확히 이걸 제안하고 있습니다 — `approval_kind`, `risk_level`, `subject_refs`.
거기에 `quality_status` 를 얹으면 됩니다.

---

## 🟢 Minor — 고치면 좋은 것

| # | 위치 | 문제 |
|---|---|---|
| m-1 | App.tsx:593 | `outputFormats` 가 비어도 오류 메시지는 "작성 목표를 3자 이상 입력해 주세요" — **틀린 안내** |
| m-2 | App.tsx:919 | `sort((a,b) => b.node_id.localeCompare(a.node_id))` — 사전순이라 반복 10회 이상이면 `i9 > i10`. 현재 `max_iterations: 4` 라 안전하지만 늘리면 깨짐 |
| m-3 | App.tsx:246 | `loadBase` 의존성에 `workspaceId` → 워크스페이스 전환 시 8개 API 전부 재호출 (3개면 충분) |
| m-4 | App.tsx:262 | `loadWorkspace` 가 `state` 에 의존 → 최초 로드 시 작업 데이터를 2번 가져옴 |
| m-5 | vite.config.ts:12 | 프록시 기본 타깃이 `http://localhost:3000` (nginx UI). README는 "API를 8000에 띄우고 `npm run dev`" 라고 안내 — **불일치**. `ORCH_API_URL` 을 안 정하면 `APP_API_KEY` 도 안 붙음(`directApi` 가 false) |
| m-6 | App.tsx 전반 | 모달에 Escape 핸들러·포커스 트랩 없음 |
| m-7 | api.ts:158 | GET 요청에도 `Content-Type: application/json` (무해하지만 불필요) |
| m-8 | package.json | `vite`, `@vitejs/plugin-react` 가 `dependencies` 에 (→ `devDependencies`) |
| m-9 | App.tsx | 에러 바운더리 없음 — 렌더 중 예외가 나면 흰 화면 |
| m-10 | App.tsx:948 | 자체 Markdown 렌더러가 표·코드블록·인라인 강조를 처리 못 함. 산출물에 표가 있으면 깨져 보임 |

> m-10은 생각보다 실사용에서 눈에 띌 수 있습니다. 문서 산출물에 표가 흔하기 때문입니다.

---

## 수정 우선순위

```
1일차  ┌─ B-1  근거 없음 사전 차단 + 안내            ← 첫 사용자 경험을 살림
       └─ B-2  SSE 폴링 폴백                         ← "멈춘 것 같음" 제거

2일차  ┌─ M-1  work_dir 필드 추가 (양식 기능 부활)
       ├─ M-2  Promise.allSettled
       └─ m-1  오류 메시지 수정

이후   ┌─ M-4  승인 문맥 구조화 (백엔드 같이 수정)
       ├─ M-3  페이지네이션
       ├─ m-10 Markdown 렌더러 교체 (표 지원)
       └─ m-5  dev 프록시/README 정합
```

**1일차 두 개만 고쳐도 "쓸만한가"가 🟡 → 🟢 로 바뀝니다.**

---

## 리팩터링에 대한 의견

`App.tsx` 가 1,300 LOC 단일 파일인 것은 앞선 As-Is 분석에서 "데이터 소스 관리 화면 추가 시
유지보수 붕괴" 위험으로 지적했습니다. 그 판단은 유지합니다.

**다만 지금 당장 쪼개지는 마세요.** 이유:

- 지금은 화면이 4개뿐이고, 파일 하나로 읽히는 이점이 아직 큽니다
- 위의 Blocker 수정이 먼저입니다. 리팩터링 중에 고치면 회귀 원인을 못 찾습니다
- 쪼개는 시점은 **화면이 6개를 넘거나, 커넥터/권한 화면을 추가할 때**입니다

쪼갤 때의 자연스러운 경계는 이미 코드에 있습니다:
`Dashboard` / `JobsView` + `RunWorkspace` / `ApprovalsView` / `ConfigurationView` / 모달 2개.

---

## 검증 한계

- 타입 체크는 통과했습니다(`tsc -p tsconfig.app.json --noEmit` → exit 0).
- **브라우저 실제 렌더링·반응형 동작은 미확인입니다.** `vite build` 와 실제 화면 확인은
  집PC에서 한 번 해주세요.

---

## 수정 내역 (2026-08-04)

### B-1 수정 — 근거 사전 점검

`POST /jobs` 를 보내기 전에 **실제로 근거가 있는지 확인**하고, 없으면 제출을 막습니다.

| 변경 | 내용 |
|---|---|
| `api.ts` | `knowledgeDocuments(collection, workspaceId)` 추가 — `GET /knowledge/documents` 호출 |
| `App.tsx` | Collection 입력을 400ms 디바운스로 조회해 실제 문서 수 확인 |
| `App.tsx` | 근거 4종(Knowledge / 폴더 / URL / 웹검색)을 집계해 폼에 실시간 표시 |
| `App.tsx` | 0건이면 제출 버튼 비활성 + 무엇을 지정해야 하는지 안내 |
| `App.tsx` | `outputFormats` 미선택 시 엉뚱한 오류 메시지가 뜨던 문제도 함께 수정 (m-1) |
| `styles.css` | `.evidence-check` / `.evidence-ok` / `.evidence-missing` |

웹 검색은 **제공자가 설정된 경우에만** 근거로 인정합니다. 체크만 하고 `web.search` 가
미등록이면 실제로는 근거가 0건이기 때문입니다.

### B-2 수정 — SSE 재연결 + 폴링 폴백

| 변경 | 내용 |
|---|---|
| 폴링 폴백 | 연결이 끊기면 **즉시** 5초 간격 폴링으로 전환. 화면이 멈추지 않음 |
| 지수 백오프 재연결 | 2s → 4s → 8s → 16s → 30s(상한)로 SSE 재시도. 성공하면 폴링 중단 |
| 이벤트 이어받기 | `event.lastEventId` 를 추적해 `?after=N` 으로 재연결 — 놓친 이벤트부터 수신 |
| 30분 상한 대응 | 서버는 30분 안전 상한에서도 `end` 를 보냄. 그때 status가 아직 실행 중이면 폴링 유지 |
| 상태 판정 개선 | `detail.run.status` 우선 사용. 기존엔 100건 제한인 `runs` 목록에 없으면 스트리밍이 **아예 시작조차 안 됐음** (M-3 부작용 해소) |
| 재연결 폭풍 방지 | `onRefresh` 를 `useRef` 로 고정. 부모 콜백 신원이 바뀔 때마다 SSE가 끊기던 문제 |
| 상태 표시 | 헤더에 `실시간` / `5초마다 확인 중` 배지 |
| `api.ts` | `runDetail` 타임아웃 12s → 30s (문서 실행은 노드 출력이 큼) |

### 검증

```
tsc -p tsconfig.app.json --noEmit   → exit 0
근거 게이트 7케이스                 → 전부 통과
end 이벤트 처리 4케이스             → 전부 통과 (30분 상한 시 폴링 유지 포함)
백오프 수열                         → 2000 → 4000 → 8000 → 16000 → 30000 → 30000
```

### 남은 것

M-1(work_dir/양식), M-2(Promise.allSettled), M-3(페이지네이션), M-4(승인 문맥 구조화)는
그대로입니다. 우선순위는 아래 표 유지.

### ⚠ 저장소 줄바꿈에 대한 주의 (이번 작업과 무관한 사전 문제)

이 저장소의 작업 트리는 **CRLF**, git 인덱스는 **LF** 이고 `core.autocrlf` 가 설정돼 있지
않습니다. 그래서 Linux 쪽에서 `git status` 를 보면 **건드리지 않은 214개 파일이 전부 수정된
것으로 표시됩니다.** 실제 내용 변경이 아니라 줄바꿈 차이입니다.

Windows에서 작업하실 때는 보이지 않겠지만, WSL/컨테이너에서 git을 쓰실 계획이면
한 번 정리하는 편이 좋습니다.

```powershell
git config core.autocrlf true      # Windows 쪽
# 또는 .gitattributes 에 * text=auto 를 두고 한 번 정규화 커밋
```

> 이번 수정 파일들의 줄바꿈은 저장소 관례(CRLF)에 맞춰 두었습니다.
