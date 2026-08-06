"""universal_ai_agent_orchestrator REST API 클라이언트.

Phase B(docs/06-ai-agent-integration.md) 범위: Job 생성/시작/상태 조회까지만.
승인(human 노드)은 아직 오케스트레이터 자체 UI에서 하고, git 반영도 아직 없다.
"""
from typing import Any

import httpx

from app.core.config import settings


class OrchestratorError(RuntimeError):
    """오케스트레이터 API 호출이 실패했을 때(연결 실패 포함)."""


class OrchestratorClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        resolved_base_url = base_url if base_url is not None else settings.orchestrator_base_url
        self._base_url = resolved_base_url.rstrip("/")
        self._api_key = api_key if api_key is not None else settings.orchestrator_api_key
        self._timeout = timeout

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"X-API-Key": self._api_key}
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise OrchestratorError(f"orchestrator unreachable ({method} {path}): {exc}") from exc
        if response.status_code >= 400:
            raise OrchestratorError(
                f"orchestrator {method} {path} returned {response.status_code}: "
                f"{response.text[:500]}"
            )
        return response.json()

    async def create_job(
        self, *, workspace_id: str, template_id: str, title: str, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/jobs",
            json={
                "workspace_id": workspace_id,
                "template_id": template_id,
                "title": title,
                "inputs": inputs,
            },
        )

    async def start_job(self, job_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/jobs/{job_id}/start")

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/jobs/{job_id}")


orchestrator_client = OrchestratorClient()
