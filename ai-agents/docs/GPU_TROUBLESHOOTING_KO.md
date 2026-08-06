# Ollama GPU 미사용 해결 (Windows)

**증상:** `verification.benchmark` 또는 하니스 사전 점검이 이렇게 나온다.

```
  생성 속도   : 6.1 tok/s
  모델 적재   : CPU 전용 (0% VRAM, 5.9GB 중 0.0GB)
```

**VRAM 0% = GPU를 아예 안 쓰고 CPU로만 추론 중.**
모델이 커서 넘친 게 아니므로 **양자화를 낮춰도 해결되지 않습니다.**

기준값: RTX 3060 Ti + qwen3:8b(Q4) 는 **40~60 tok/s**. CPU 전용이면 **3~8 tok/s**.
지금 6.1 tok/s 는 정확히 CPU 추론 구간입니다.

---

## 1단계. GPU가 존재하고 드라이버가 살아 있는가

```powershell
nvidia-smi
```

| 결과 | 의미 | 다음 |
|---|---|---|
| GPU 표와 드라이버 버전이 나옴 | 하드웨어·드라이버 정상 | 2단계로 |
| `nvidia-smi'은(는) 명령이 아닙니다` | 드라이버 미설치 또는 PATH 없음 | NVIDIA 드라이버 설치 후 재부팅 |
| GPU 없음 | 이 PC에 NVIDIA GPU가 없음 | **6단계로** |

`nvidia-smi` 가 나오면 상단 **CUDA Version** 을 적어두세요. 너무 낮으면(예: 11.x)
Ollama 최신 빌드와 안 맞을 수 있습니다.

---

## 2단계. 다른 프로그램이 VRAM을 먹고 있는가

`nvidia-smi` 하단 **Processes** 와 **Memory-Usage** 를 봅니다.

8GB 카드에서 qwen3:8b(약 5.9GB)를 올리려면 여유가 6GB 이상 필요합니다.
브라우저(하드웨어 가속), 게임 런처, Stable Diffusion, 다른 Ollama 인스턴스가
2~3GB를 잡고 있으면 Ollama가 **처음부터 GPU 적재를 포기하고 CPU로 갑니다.**

```powershell
# 무거운 것부터 닫고 재측정
nvidia-smi
python -m verification.benchmark
```

---

## 3단계. Ollama가 GPU를 발견했는가 — 로그 확인

이게 가장 확실한 단서입니다.

```powershell
# Ollama 서버 로그 (Windows 기본 위치)
Get-Content "$env:LOCALAPPDATA\Ollama\server.log" -Tail 80
```

찾을 문구:

| 로그 | 의미 |
|---|---|
| `no compatible GPUs were discovered` | Ollama가 GPU를 못 찾음 → 4단계 |
| `inference compute ... library=cuda` | CUDA 인식됨. 다른 원인 |
| `library=cpu` | CPU 빌드로 동작 중 → 4단계 |
| `insufficient VRAM` / `unable to load` | 용량 부족 → 2단계 |

로그가 없으면 트레이의 Ollama를 종료 후 콘솔에서 직접 띄워 보세요.

```powershell
ollama serve
```

기동 직후 출력에 GPU 탐지 결과가 그대로 찍힙니다.

---

## 4단계. Ollama 재설치 / 업데이트

CUDA 런타임은 Ollama에 내장돼 있어서, **버전이 낮으면 새 드라이버와 안 맞거나
그 반대인 경우**가 흔합니다. 재설치가 가장 빠른 해결책입니다.

```powershell
ollama --version
```

1. 트레이에서 Ollama 완전 종료
2. https://ollama.com/download 에서 최신 Windows 설치본 받아 설치
3. 재부팅
4. `ollama serve` 로그에서 GPU 탐지 확인
5. `python -m verification.benchmark` 재측정

> **Ollama를 Windows 서비스로 돌리고 있다면** 서비스 계정이 GPU에 접근하지 못하는 경우가
> 있습니다. 일단 사용자 세션에서 `ollama serve` 로 직접 띄워 비교해 보세요.

---

## 5단계. 환경변수가 GPU를 막고 있는가

```powershell
Get-ChildItem Env: | Where-Object { $_.Name -like "*OLLAMA*" -or $_.Name -like "*CUDA*" }
```

문제를 일으키는 값들:

| 변수 | 문제가 되는 값 | 조치 |
|---|---|---|
| `OLLAMA_LLM_LIBRARY` | `cpu`, `cpu_avx2` | 삭제 |
| `CUDA_VISIBLE_DEVICES` | `` (빈 값), `-1` | 삭제 |
| `OLLAMA_NUM_GPU` | `0` | 삭제 |

```powershell
Remove-Item Env:OLLAMA_LLM_LIBRARY -ErrorAction SilentlyContinue
# 영구 설정이면 시스템 환경변수에서도 지우고 재부팅
```

**노트북이라면** NVIDIA 제어판 → 3D 설정 관리 → `ollama.exe` 를 고성능 NVIDIA
프로세서로 지정하세요. 하이브리드 그래픽에서 내장 GPU가 잡히는 경우가 있습니다.

---

## 6단계. 이 PC에 쓸만한 GPU가 없다면

CPU 전용으로 이 워크플로를 완주하는 건 현실적이지 않습니다.
(6 tok/s 기준 호출 1회 5.4분 × 11회 ≈ **1시간**)

선택지 셋:

| 방법 | 명령 | 특징 |
|---|---|---|
| **더 작은 모델** | `ollama pull qwen3:4b` 후 `--model qwen3:4b` | CPU에서 2~3배 빠름. 품질은 떨어짐 |
| **하이브리드** | `--hybrid` (ANTHROPIC_API_KEY 필요) | 판단 역할만 Claude. 품질 상한 확인용으로 가장 유용 |
| **GPU 있는 집PC** | 그쪽에서 동일 명령 | 진짜 로컬 성능 확인 |

> 사업성 관점에서는 **하이브리드를 먼저 돌려보는 게 낫습니다.** "로컬 8B로 되는가"보다
> "이 파이프라인 설계가 애초에 쓸만한 결과를 내는가"가 먼저 답해야 할 질문이기 때문입니다.
> 설계가 좋으면 하드웨어는 나중에 붙이면 되지만, 설계가 나쁘면 GPU를 사도 소용없습니다.

---

## 확인 순서 요약

```
nvidia-smi                          → GPU·드라이버 있나?  없으면 6단계
  ↓ 있음
nvidia-smi 의 Memory-Usage          → 다른 게 VRAM 먹고 있나?  있으면 종료 후 재측정
  ↓ 여유 있음
ollama serve 로그                   → 'no compatible GPUs' 있나?
  ↓ 있음
Ollama 재설치 + 재부팅
  ↓ 그래도 안 되면
OLLAMA_LLM_LIBRARY / CUDA_VISIBLE_DEVICES 확인
  ↓ 그래도 안 되면
6단계 (작은 모델 / 하이브리드 / 다른 PC)
```

매 단계 후 재측정:

```powershell
python -m verification.benchmark
```

**목표: `적재 위치: GPU 전용 (100% VRAM)` 그리고 40 tok/s 이상.**
