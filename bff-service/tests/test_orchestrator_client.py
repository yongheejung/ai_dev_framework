import httpx
import pytest

from app.agents.orchestrator_client import OrchestratorClient, OrchestratorError


@pytest.fixture(autouse=True)
def _patch_async_client(monkeypatch):
    """OrchestratorClient._request가 만드는 httpx.AsyncClient에 MockTransport를 강제한다."""
    handler_holder: dict = {}

    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler_holder["handler"])
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_async_client)
    return handler_holder


async def test_create_job_sends_expected_payload_and_headers(_patch_async_client):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content
        return httpx.Response(200, json={"id": "job-1", "status": "READY", "run_id": None})

    _patch_async_client["handler"] = handler
    client = OrchestratorClient(base_url="http://orchestrator.test", api_key="secret-key")

    result = await client.create_job(
        workspace_id="default", template_id="code-build-job", title="t", inputs={"goal": "g"}
    )

    assert result == {"id": "job-1", "status": "READY", "run_id": None}
    assert captured["method"] == "POST"
    assert captured["url"] == "http://orchestrator.test/jobs"
    assert captured["headers"]["x-api-key"] == "secret-key"


async def test_start_job_returns_run_id(_patch_async_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job-1/start"
        return httpx.Response(200, json={"id": "job-1", "status": "QUEUED", "run_id": "run-1"})

    _patch_async_client["handler"] = handler
    client = OrchestratorClient(base_url="http://orchestrator.test", api_key="k")

    result = await client.start_job("job-1")

    assert result["run_id"] == "run-1"
    assert result["status"] == "QUEUED"


async def test_non_2xx_status_raises_orchestrator_error(_patch_async_client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, text="immutable definition conflict")

    _patch_async_client["handler"] = handler
    client = OrchestratorClient(base_url="http://orchestrator.test", api_key="k")

    with pytest.raises(OrchestratorError, match="409"):
        await client.create_job(workspace_id="default", template_id="x", title="t", inputs={})


async def test_connection_failure_raises_orchestrator_error(_patch_async_client):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _patch_async_client["handler"] = handler
    client = OrchestratorClient(base_url="http://orchestrator.test", api_key="k")

    with pytest.raises(OrchestratorError, match="unreachable"):
        await client.get_job("job-1")
