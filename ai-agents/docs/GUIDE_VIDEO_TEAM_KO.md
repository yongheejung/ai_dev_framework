# 동영상 제작팀 사용 가이드

- 대상 팀: `video-team` (기획자 · 품질검토 · 논리비평)
- 형제 문서: [`USAGE_GUIDE_KO.md`](./USAGE_GUIDE_KO.md), [`GUIDE_DEV_TEAM_KO.md`](./GUIDE_DEV_TEAM_KO.md), [`GUIDE_QUANT_TEAM_KO.md`](./GUIDE_QUANT_TEAM_KO.md)

---

## 0. 이 팀이 만드는 것 — 기대치를 먼저 맞추세요

**만드는 것:** 보유한 이미지들을 순서·자막·노출초를 설계해 이어 붙인 **슬라이드쇼 MP4**
(선택적으로 켄번스 효과 + 배경 오디오)

**만들지 않는 것:**

- 영상 생성 AI가 아닙니다. **없는 장면을 만들어내지 않습니다**
- 컷 편집, 트랜지션 다양화, 모션그래픽, 나레이션 TTS 없음
- 자막을 영상에 굽지 않습니다 (`caption` 은 기획 산출물의 텍스트)

**즉 "이미지 + 순서 + 타이밍"을 AI가 기획하고 ffmpeg가 이어 붙이는 도구입니다.**
이걸 알고 쓰면 유용하고, 영상 생성 AI를 기대하면 실망합니다.

> 앞선 사업성 분석에서 **동영상팀은 사업화 기여가 가장 낮다**고 판정했습니다.
> 이 가이드는 "이미 만들어 뒀으니 제대로 쓰는 법"입니다. 여기에 추가 투자하기 전에
> [`EXTENSION_ANALYSIS.md`](./EXTENSION_ANALYSIS.md) 를 먼저 보세요.

---

## 1. 두 단계로 나뉩니다

| 단계 | 노드 | 요구 조건 | 작업PC에서 |
|---|---|---|---|
| **기획** | `plan`(협업) → `approve`(승인) | 없음 | 🟢 가능 |
| **렌더** | `render` (`video.montage`) | **ffmpeg + 미디어 루트** | 🔴 불가 |

**기획만 먼저 검증할 수 있습니다.** 그리고 기획이 이 팀의 실제 가치입니다 —
ffmpeg 이어붙이기는 누구나 합니다.

---

## 2. 사전 준비 (렌더까지 하려면)

### 2-1. ffmpeg + 한글 폰트

기본 `Dockerfile` 에는 ffmpeg가 **없습니다.** 추가하고 재빌드해야 합니다.

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg fonts-nanum && rm -rf /var/lib/apt/lists/*
```

### 2-2. 미디어 루트 지정

```dotenv
APP_MEDIA_INPUT_ROOTS=["/workspace/media"]
```

그리고 호스트 폴더를 그 경로로 마운트합니다 (`docker-compose.override.yml`).

> ⚠ **`video.montage` 도구는 `APP_MEDIA_INPUT_ROOTS` 를 설정해야 등록됩니다.**
> 설정 안 하면 도구 목록에 아예 나타나지 않고, 워크플로가 render 노드에서 실패합니다.
> `LIVE_VERIFICATION_RUNBOOK.md` 의 "가장 흔한 실패 4가지" 중 하나입니다.

### 2-3. 확인

```powershell
curl -s -H "X-API-Key: $env:APP_API_KEY" http://localhost:8000/tools | Select-String "video.montage"
```

나오지 않으면 2-2로 돌아가세요.

---

## 3. 실행

### 입력 파라미터

| 키 | 필수 | 설명 |
|---|---|---|
| `goal` | ✅ | 무엇을 알리는 영상인지 |
| `available_images` | ✅ | **미디어 루트 기준 파일명 목록.** 기획자는 이 안에서만 고릅니다 |
| `audience` | | 대상 시청자 |
| `audio` | | 배경 오디오 파일명 (미디어 루트 기준) |
| `reference_globs` / `reference_urls` | | 자막 근거 자료 |
| `output_path` | | 기본 `video/montage.mp4` |

```json
{
  "goal": "중소 물류창고 대표에게 WMS 도입 효과를 60초로 소개",
  "audience": "중소 물류창고 운영 대표",
  "available_images": [
    "warehouse_before.jpg", "barcode_scan.jpg",
    "dashboard.jpg", "picking_route.jpg"
  ],
  "audio": "bgm_calm.mp3",
  "output_path": "video/wms_intro.mp4"
}
```

---

## 4. 기획 산출물 읽는 법

```json
{
  "title": "WMS 도입 60초",
  "format": "16:9",
  "scenes": [
    {"image": "warehouse_before.jpg", "caption": "수기 엑셀 관리, 실사 오차율 월 7%", "seconds": 4},
    {"image": "barcode_scan.jpg",     "caption": "바코드 기반 실시간 반영",          "seconds": 3}
  ],
  "scene_images": ["warehouse_before.jpg", "barcode_scan.jpg"],
  "total_seconds": 7
}
```

### 승인 전에 확인할 3가지

1. **`scene_images` 가 `scenes` 와 정확히 일치하는가** — 같은 파일명, 같은 순서, 같은 개수.
   몽타주 도구는 `scene_images` 를 그대로 씁니다. 어긋나면 자막과 화면이 밀립니다.
2. **없는 이미지를 지어내지 않았는가** — 에이전트 프롬프트가 금지하고 있고 `video-quality-reviewer`
   가 검증하지만, **최종 확인은 사람**입니다. 없는 파일이 있으면 렌더가 실패합니다.
3. **자막이 근거에 있는 사실인가** — 과장·추정이 자막으로 들어가면 그대로 대외 노출됩니다.

> 다른 팀과 달리 이 워크플로는 `require_evidence: false` 입니다. 근거 없이도 기획이 나옵니다.
> **그래서 자막의 사실성은 사람이 더 꼼꼼히 봐야 합니다.**

---

## 5. 렌더 옵션

`app/media.py` 기본값:

| 옵션 | 기본 | 비고 |
|---|---|---|
| `width` × `height` | 1920×1080 | **쇼츠/릴스는 1080×1920** |
| `fps` | 30 | |
| `seconds_per_image` | 3.0 | 씬별 `seconds` 가 있으면 그쪽 우선 |
| `ken_burns` | **true** | 정지컷 pan/zoom. 끄면 단순 concat |
| `audio_fade_out_sec` | — | 배경음 페이드아웃 |

### ⚠ 켄번스가 실패하면

`zoompan` 필터 문자열은 **작업PC에서 실행 검증을 못 한 유일한 부분**입니다
(`LIVE_VERIFICATION_RUNBOOK.md` Phase 7).

```
ffmpeg 필터 에러 → options.ken_burns: false 로 먼저 단순 concat 확인
```

단순 concat이 되면 파이프라인은 정상이고 필터 문자열만 문제입니다. 원인 범위가 좁혀집니다.

---

## 6. 자주 나는 실패

| 증상 | 원인 |
|---|---|
| 도구 목록에 `video.montage` 없음 | `APP_MEDIA_INPUT_ROOTS` 미설정 (2-2) |
| `ffmpeg not found` | Dockerfile에 ffmpeg 미설치 (2-1) |
| 렌더 중 파일 없음 오류 | 기획이 실존하지 않는 파일명 사용 → 승인 전 확인 (4절) |
| 자막과 화면이 밀림 | `scene_images` ↔ `scenes` 불일치 (4절 1번) |
| zoompan 필터 에러 | `ken_burns: false` 로 원인 분리 (5절) |
| 한글 자막 깨짐 | 컨테이너에 한글 폰트 없음 (2-1의 `fonts-nanum`) |

---

## 7. 실사용 판정

동영상팀의 "완료" 기준: **실존하는 소재만 사용하고, 씬 구성이 그대로 렌더 가능할 것.**

이 팀은 RTR 측정 대상에서 빼도 됩니다 (사업화 우선순위 밖). 대신 **하니스 자동 지표만 확인**하세요.

```powershell
python -m verification.harness --configs local --scenarios video-montage
```

하니스는 기획 품질(환각 소재 사용 여부)까지만 검증합니다. 렌더는 ffmpeg가 있는 환경에서
직접 확인해야 합니다. 시나리오 정의에 `does_not_prove: "실제 렌더링 결과물의 품질"` 로
명시돼 있습니다.

---

## 8. 확장할 생각이라면

앞선 분석의 권고를 반복합니다. **동영상팀 확장은 지금 우선순위가 아닙니다.**

그래도 손을 댄다면 투자 대비 효과 순:

| 개선 | 효과 | 난이도 |
|---|---|---|
| 자막을 영상에 굽기 (`drawtext`) | 높음 — 지금은 자막이 텍스트로만 남음 | 낮음 |
| 세로형(1080×1920) 프리셋 | 높음 — 쇼츠/릴스 수요 | 낮음 |
| 트랜지션 종류 추가 (`xfade`) | 중간 | 중간 |
| TTS 나레이션 | 중간 | 높음 (외부 의존성) |
| 영상 클립 입력 지원 | 낮음 | 높음 |

**자막 굽기와 세로형 프리셋 둘 다 `app/media.py` 의 필터 문자열 수정 수준**입니다.
정말 쓸 일이 있다면 이 둘만 하세요.
