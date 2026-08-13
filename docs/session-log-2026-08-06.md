# 세션 작업 로그 — 2026-08-06 (AI_Dev_FrameWork ↔ universal_ai_agent_orchestrator 연동)

> 각 항목의 제목(질문 요약)을 클릭하면 처리한 내용과 답변이 펼쳐집니다. smartcore-wms 작업 로그는
> `smartcore-wms/docs/session-log-2026-08-06.md`에 별도로 있습니다 — 이 문서는 그 이전에 진행한
> AI_Dev_FrameWork 자체 점검 + universal_ai_agent_orchestrator 연동 작업을 다룹니다.

---

<details>
<summary><b>1. 전체적으로 테스트 점검 및 분석</b> — docker-compose, Helm, MSSQL/Oracle DB 프로파일까지 실제로 붙여서 검증</summary>

**처리한 내용**
- `GlobalExceptionHandler`에 `NoResourceFoundException`/`NoHandlerFoundException` 핸들러 추가(404가 500으로 새던 버그 수정)
- `MeController`가 Spring Security 내부용 `FACTOR_BEARER` 같은 비-`ROLE_` 권한까지 `/me` 응답에 노출하던 것 필터링
- `core-service/Dockerfile`에 `chown appuser:appuser /app` 추가(SQLite 프로파일이 non-root 컨테이너에서 `SQLITE_CANTOPEN`으로 죽던 버그)
- MSSQL/Oracle을 실제 `db-mssql`/`db-oracle` 컨테이너에 붙여서 Flyway 마이그레이션 + 회원가입/로그인/`/me`/RBAC(200/403)/404까지 전부 통과 확인
- `docker compose --profile <x> down`이 지정한 프로파일뿐 아니라 기본 프로파일 서비스까지 전부 내려버리는 것을 실제로 겪고 문서화

**답변 요지**: Postgres는 프레임워크 자체가 계속 써서 이미 검증됨, MSSQL/Oracle은 core-service 기준 실제 검증 완료, bff-service는 아직 미검증(드라이버 미설치)이라고 `docs/03-database.md`에 정리.
</details>

<details>
<summary><b>2. 실제 프레임워크 사용방법 가이드 문서를 주제별로 상세하게 작성</b></summary>

**처리한 내용**
- `docs/01-getting-started.md` ~ `docs/05-deployment.md` 신규 작성: 클론/이름변경, 인증/RBAC, DB 프로파일/마이그레이션, 기능 추가 실습 예제("note" 도메인), docker-compose/Helm 배포
- `docs/README.md`로 목차 정리
</details>

<details>
<summary><b>3. Mobile CI 실행 결과 확인</b></summary>

**답변 요지**: `dart format` 불일치, Flutter 스캐폴딩 한계(`android/`/`ios/` 미커밋, CI가 그때그때 `flutter create`로 스캐폴딩) 등을 확인하고 수정.
</details>

<details>
<summary><b>4. universal_ai_agent_orchestrator 멀티 AI 에이전트 시스템과 이번 프레임워크가 어떻게 협업하면 좋을지</b> — 아이디어 요청 → 비전 문서 반영 → 설계 문서로 정리 → AGENTS.md 작성</summary>

**처리한 내용**
- 사용자가 제공한 "2단계 AI 에이전트 연계.docx"(Feature Developer + Maintenance 에이전트 파이프라인 비전) 반영
- `docs/06-ai-agent-integration.md` 신규 — 통합 설계/진행상황 문서(이후 Phase가 진행될 때마다 계속 갱신)
- 루트 `AGENTS.md` 작성 — AI 코딩 에이전트용 규칙(0. 공통, 1~4 서비스별, 5. 체크리스트, 6. docs 포인터), 루트 `CLAUDE.md`가 `@AGENTS.md`로 임포트

**답변 요지**: 오케스트레이터의 실제 REST API/Docker 실행모델(`app/sandbox.py`, `app/tools.py`)을 직접 읽고, code-build-v1 워크플로우(context→write→verify→review→approve→save_files) 구조를 확인한 뒤 설계에 반영.
</details>

<details>
<summary><b>5. Phase A (수동 파이프라인 검증)</b></summary>

**처리한 내용**: 사용자가 "orchestrator 저장소에서 별도 Claude CLI 세션으로 진행하자"고 정정 — 이 세션이 아니라 `universal_ai_agent_orchestrator` 저장소에서 별도로 진행됨.

**답변 요지**: GPU가 없어 로컬 Ollama(qwen3:8b) 검증만 보류, 나머지는 전부 통과했다고 사용자가 전달 — 집 PC(GPU)에서 추후 재검증 예정으로 확인만 하고 넘어감.
</details>

<details>
<summary><b>6. Phase B(REST 위임) / Phase C(git 커넥터) 검토·확인</b></summary>

**처리한 내용**: 다른 세션에서 완료된 작업을 리뷰 — Phase B는 agent-tasks를 실제 오케스트레이터에 연결, Phase C는 승인된 코드를 실제 GitHub PR로 저장하는 git 커넥터(GitHub REST Git Data API 사용, 로컬 `git push` 서브프로세스 대신 — 토큰이 프로세스 인자/에러메시지로 새는 것을 막기 위해). `docs/06` 갱신 내용 확인.

**답변 요지**: `GIT_CONNECTOR_ENABLED`는 아직 `false`, `GITHUB_TOKEN` 미설정 — 실제 GitHub 라이브 테스트는 아직 안 함(세분화된 PAT 발급이 선행 조건으로 남음).
</details>

<details>
<summary><b>7. Phase D (샌드박스에 Java/Gradle 지원 추가) — 이 세션에서 직접 진행</b></summary>

**처리한 내용** — 순차적으로 4개 버그를 발견하고 수정, 매번 실제 프로덕션 코드 경로(`build_code_executor(...).run(...)`)로 재검증:

1. **`gradlew: not found`(exit 127)** — `verify` 노드가 `write.files`만 스테이징하고 기존 프로젝트(gradlew 등)는 안 올림 → `code.exec`에 옵트인 플래그 `seed_from_read_roots` 신규 추가(`app/sandbox.py`의 `CodeExecService._seed_from_read_roots`), 기본값 false로 유지해 기존 bff-service job은 영향 없음
2. **`Permission denied`(exit 126)** — 시딩한 파일이 `write_bytes`로 실행권한(+x)을 잃음 → `target.chmod(source.stat().st_mode)`로 원본 권한 보존
3. **Gradle lock 파일 생성 실패** — `--read-only` 루트라 `/root/.gradle`에 못 씀 → 이미지에는 `/opt/gradle-cache-seed`(읽기전용 시드)만 굽고, 컨테이너 시작 시 wrapper 스크립트가 쓰기 가능한 `/work/.gradle-home`으로 복사
4. **`UnsatisfiedLinkError`(sqlite-jdbc 네이티브 라이브러리)** — 기본 `java.io.tmpdir`(`/tmp`)도 읽기전용 → `JAVA_TOOL_OPTIONS=-Djava.io.tmpdir=/work/.jtmp` + 런타임에 `mkdir -p /work/.jtmp`

- 함께 변경: `docker/code-sandbox.Dockerfile`(JDK 21 멀티스테이지 추가), `app/config.py`(`code_exec_memory` 1g→2g, `code_exec_tmpfs_size` 신규 1536m), `examples/workflows/code_build.yaml`(v4→v5, `seed_from_read_roots` 입력 추가), `examples/job_templates/code-build-core-job.yaml`(신규), 테스트 4건 추가 + 기존 테스트 2건의 fake executor 시그니처 수정 — **234/234 테스트 통과**
- 최종 검증: `./gradlew test` → `BUILD SUCCESSFUL in 1m 3s` (실제 컨테이너 안에서 프로덕션 코드 경로로 실행)
- `docs/06-ai-agent-integration.md`에 4개 버그를 발견 순서대로 상세 기록, 커밋 `386e110` 참조

**답변 요지**: 사용자가 "네트워크 차단을 풀면 더 간단하지 않냐"고 제안했을 때, 보안 근거(샌드박스에서 검증 안 된 AI 생성 코드가 돈다는 위협 모델)를 설명했고 사용자가 동의 — 네트워크 차단 유지, SQLite 프로파일 고정으로 해결.
</details>

<details>
<summary><b>8. 객관적 평가 — 다른 프레임워크와 비교했을 때 AI_Dev_FrameWork + 오케스트레이터 연동이 어떤지 솔직하게</b></summary>

**답변 요지**: 강점/약점을 가감없이 정리 — 사용자가 이후 "이 프레임워크와 오케스트레이터를 실전에서 더 적극적으로 쓰면서 나오는 버그나 안정화를 계속 신경써서 고도화하겠다"는 방향에 동의. "나만의 무기(빠르고 정확하고 보안점검·거버넌스까지 되는 개인 개발 시스템)를 만들고 싶었다"는 동기를 공유.
</details>

<details>
<summary><b>9. 오케스트레이터 저장소 푸시</b></summary>

**처리한 내용**: 로컬에 쌓여있던 커밋 3개(설계 문서 반영, 샌드박스 Java 확장, Phase D 버그 수정 4건)를 사용자 확인 후 `git push origin main` — `19ae66d..386e110`.
</details>

<details>
<summary><b>10. smartcore-wms 신규 프로젝트 착수</b></summary>

**처리한 내용**: 이 지점부터는 완전히 새로운 프로젝트(WMS)로 전환 — 별도 저장소 `C:\workspace\smartcore-wms`에서 진행. 상세 내용은 `smartcore-wms/docs/session-log-2026-08-06.md` 참고.
</details>

---

## 참고 문서
- `docs/06-ai-agent-integration.md` — 오케스트레이터 연동 설계/진행상황 (Phase A~D 상세 기록의 원본)
- `AGENTS.md` — AI 코딩 에이전트 규칙 (이 저장소 + universal_ai_agent_orchestrator 공통 참조)
- `docs/03-database.md` — MSSQL/Oracle 검증 방법과 결과
