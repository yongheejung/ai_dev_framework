"""승인된 오케스트레이터 Job 결과를 실제 GitHub 저장소에 반영한다 (Phase C).

이 프레임워크에서 유일하게 실제 저장소에 "쓰는" 지점이다. 기본은 비활성
(GIT_CONNECTOR_ENABLED=true로 명시적으로 켜야 함, app/core/config.py 참고).

로컬 git checkout이나 `git push`를 쓰지 않고 GitHub REST Git Data API(blob→tree→commit→ref)만
쓴다 — 커밋 하나로 여러 파일을 원자적으로 반영할 수 있고, 무엇보다 GITHUB_TOKEN을 서브프로세스
인자나 원격 URL에 실어 보낼 필요가 없어(그 경우 에러 메시지·프로세스 목록으로 새어나갈 수 있다)
토큰이 항상 Authorization 헤더 안에만 머무른다.
"""
import re
from typing import Any

import httpx

from app.agents.orchestrator_client import orchestrator_client
from app.core.config import settings


class GitConnectorError(RuntimeError):
    """git 커넥터 실행 실패 (설정 오류, 오케스트레이터 조회 실패, GitHub API 실패 등)."""


class GitConnectorDisabled(GitConnectorError):
    """GIT_CONNECTOR_ENABLED가 꺼져 있을 때."""


def _safe_join(prefix: str, relative_path: str) -> str:
    """job이 낸 상대경로를 검증 후 대상 저장소 경로에 붙인다.

    오케스트레이터 자체의 code.save 경로 검증(app/tools.py의 _safe_relative_path)과 같은 원칙 —
    절대경로/상위 디렉터리 탈출은 조용히 고치지 않고 거부한다(모델 오류를 드러내기 위함).
    """
    cleaned = str(relative_path).strip().replace("\\", "/")
    if not cleaned or cleaned.startswith("/") or re.match(r"^[A-Za-z]:/", cleaned):
        raise GitConnectorError(f"unsafe file path from job output: {relative_path!r}")
    if any(part in ("", "..") for part in cleaned.split("/")):
        raise GitConnectorError(f"unsafe file path from job output: {relative_path!r}")
    return f"{prefix.rstrip('/')}/{cleaned}"


async def _fetch_saved_files(job_id: str) -> list[dict[str, Any]]:
    """save_files 노드의 출력(경로 + artifact_id 목록)을 오케스트레이터에서 가져온다."""
    job = await orchestrator_client.get_job(job_id)
    run_id = job.get("run_id")
    if not run_id:
        raise GitConnectorError(f"job {job_id} has no run_id yet")
    run = await orchestrator_client.get_run(run_id)
    for node in run.get("nodes", []):
        if node.get("node_id") == "save_files" and node.get("status") == "SUCCEEDED":
            output = node.get("output") or {}
            files = output.get("files", [])
            if files:
                return files
    raise GitConnectorError(
        f"run {run_id} has no save_files output — job may not be approved/succeeded yet"
    )


async def _fetch_artifact_text(artifact_id: str) -> str:
    artifact = await orchestrator_client.get_artifact(artifact_id)
    if artifact.get("content_omitted"):
        raise GitConnectorError(f"artifact {artifact_id} is too large to inline")
    if artifact.get("encoding") == "base64":
        raise GitConnectorError(
            f"artifact {artifact_id} is binary; git connector only handles text files"
        )
    return artifact.get("content", "")


class _GitHubClient:
    def __init__(self) -> None:
        if not settings.github_token:
            raise GitConnectorError("GITHUB_TOKEN is not configured")
        self._owner_repo = settings.github_owner_repo
        self._headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url="https://api.github.com", timeout=20.0) as client:
            response = await client.request(
                method, f"/repos/{self._owner_repo}{path}", headers=self._headers, **kwargs
            )
        if response.status_code >= 400:
            # response.text에는 GitHub 에러 본문만 담기고 요청 헤더(토큰)는 안 실린다.
            raise GitConnectorError(
                f"GitHub {method} {path} returned {response.status_code}: {response.text[:500]}"
            )
        return response.json() if response.content else {}

    async def get_branch_head_sha(self, branch: str) -> str:
        ref = await self._request("GET", f"/git/ref/heads/{branch}")
        return ref["object"]["sha"]

    async def get_commit_tree_sha(self, commit_sha: str) -> str:
        commit = await self._request("GET", f"/git/commits/{commit_sha}")
        return commit["tree"]["sha"]

    async def create_blob(self, content: str) -> str:
        blob = await self._request(
            "POST", "/git/blobs", json={"content": content, "encoding": "utf-8"}
        )
        return blob["sha"]

    async def create_tree(self, base_tree_sha: str, entries: list[dict[str, Any]]) -> str:
        tree = await self._request(
            "POST", "/git/trees", json={"base_tree": base_tree_sha, "tree": entries}
        )
        return tree["sha"]

    async def create_commit(self, message: str, tree_sha: str, parent_sha: str) -> str:
        commit = await self._request(
            "POST",
            "/git/commits",
            json={"message": message, "tree": tree_sha, "parents": [parent_sha]},
        )
        return commit["sha"]

    async def create_or_update_branch_ref(self, branch: str, commit_sha: str) -> None:
        try:
            await self._request(
                "POST", "/git/refs", json={"ref": f"refs/heads/{branch}", "sha": commit_sha}
            )
        except GitConnectorError:
            # 브랜치가 이미 있으면(재시도 등) fast-forward로 갱신
            await self._request(
                "PATCH", f"/git/refs/heads/{branch}", json={"sha": commit_sha, "force": False}
            )

    async def create_pull_request(self, *, branch: str, base: str, title: str, body: str) -> str:
        pr = await self._request(
            "POST", "/pulls", json={"title": title, "head": branch, "base": base, "body": body}
        )
        return pr["html_url"]


async def apply_job_to_repo(*, task_id: str, job_id: str, agent_name: str, instruction: str) -> str:
    """승인된 Job의 결과 파일을 GitHub에 커밋 하나로 반영하고 PR을 연다. PR URL을 반환한다."""
    if not settings.git_connector_enabled:
        raise GitConnectorDisabled("GIT_CONNECTOR_ENABLED is not set to true")

    files = await _fetch_saved_files(job_id)
    github = _GitHubClient()
    base = settings.git_connector_base_branch

    base_sha = await github.get_branch_head_sha(base)
    base_tree_sha = await github.get_commit_tree_sha(base_sha)

    entries = []
    for f in files:
        github_path = _safe_join(settings.git_connector_path_prefix, f["path"])
        content = await _fetch_artifact_text(f["artifact_id"])
        blob_sha = await github.create_blob(content)
        entries.append({"path": github_path, "mode": "100644", "type": "blob", "sha": blob_sha})

    new_tree_sha = await github.create_tree(base_tree_sha, entries)
    commit_message = f"agent({agent_name}): {instruction[:72]}"
    commit_sha = await github.create_commit(commit_message, new_tree_sha, base_sha)

    branch = f"agent/task-{task_id[:8]}"
    await github.create_or_update_branch_ref(branch, commit_sha)

    pr_body = (
        f"자동 생성된 PR입니다 (AI Dev Framework agent-task `{task_id}` → "
        f"오케스트레이터 job `{job_id}`).\n\n**지시**: {instruction}\n\n"
        "사람이 리뷰 후 직접 merge하세요 — 자동 merge는 하지 않습니다."
    )
    return await github.create_pull_request(
        branch=branch, base=base, title=commit_message, body=pr_body
    )
