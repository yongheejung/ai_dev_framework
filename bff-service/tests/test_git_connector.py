import httpx
import pytest

from app.agents import git_connector
from app.agents.orchestrator_client import orchestrator_client
from app.core.config import settings


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    monkeypatch.setattr(settings, "git_connector_enabled", False)
    monkeypatch.setattr(settings, "github_token", "")
    monkeypatch.setattr(settings, "github_owner_repo", "acme/widgets")
    monkeypatch.setattr(settings, "git_connector_base_branch", "main")
    monkeypatch.setattr(settings, "git_connector_path_prefix", "bff-service/")


async def test_disabled_by_default_raises_git_connector_disabled():
    with pytest.raises(git_connector.GitConnectorDisabled):
        await git_connector.apply_job_to_repo(
            task_id="task-1", job_id="job-1", agent_name="a", instruction="i"
        )


def test_safe_join_rejects_path_traversal():
    with pytest.raises(git_connector.GitConnectorError):
        git_connector._safe_join("bff-service/", "../../etc/passwd")


def test_safe_join_rejects_absolute_path():
    with pytest.raises(git_connector.GitConnectorError):
        git_connector._safe_join("bff-service/", "/etc/passwd")


def test_safe_join_prefixes_relative_path():
    assert git_connector._safe_join("bff-service/", "app/foo.py") == "bff-service/app/foo.py"


async def test_apply_job_to_repo_end_to_end(monkeypatch):
    monkeypatch.setattr(settings, "git_connector_enabled", True)
    monkeypatch.setattr(settings, "github_token", "gh-secret-token")

    async def fake_get_job(job_id):
        assert job_id == "job-1"
        return {"id": "job-1", "run_id": "run-1", "status": "SUCCEEDED"}

    async def fake_get_run(run_id):
        assert run_id == "run-1"
        return {
            "nodes": [
                {
                    "node_id": "save_files",
                    "status": "SUCCEEDED",
                    "output": {
                        "files": [
                            {"path": "app/foo.py", "artifact_id": "art-1"},
                            {"path": "tests/test_foo.py", "artifact_id": "art-2"},
                        ]
                    },
                }
            ]
        }

    async def fake_get_artifact(artifact_id):
        contents = {
            "art-1": "def foo(): return 1\n",
            "art-2": "def test_foo(): assert True\n",
        }
        return {"encoding": "text", "content": contents[artifact_id], "content_omitted": False}

    monkeypatch.setattr(orchestrator_client, "get_job", fake_get_job)
    monkeypatch.setattr(orchestrator_client, "get_run", fake_get_run)
    monkeypatch.setattr(orchestrator_client, "get_artifact", fake_get_artifact)

    calls: list[tuple[str, str]] = []
    created_blobs: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        # 토큰이 절대 요청 바디/쿼리에 실리지 않고 헤더에만 있는지 확인
        assert request.headers.get("authorization") == "Bearer gh-secret-token"

        if request.url.path == "/repos/acme/widgets/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": "base-sha"}})
        if request.url.path == "/repos/acme/widgets/git/commits/base-sha":
            return httpx.Response(200, json={"tree": {"sha": "base-tree-sha"}})
        if request.url.path == "/repos/acme/widgets/git/blobs":
            blob_sha = f"blob-sha-{len(created_blobs)}"
            created_blobs.append(blob_sha)
            return httpx.Response(201, json={"sha": blob_sha})
        if request.url.path == "/repos/acme/widgets/git/trees":
            return httpx.Response(201, json={"sha": "new-tree-sha"})
        if request.url.path == "/repos/acme/widgets/git/commits":
            return httpx.Response(201, json={"sha": "new-commit-sha"})
        if request.url.path == "/repos/acme/widgets/git/refs":
            return httpx.Response(201, json={})
        if request.url.path == "/repos/acme/widgets/pulls":
            return httpx.Response(201, json={"html_url": "https://github.com/acme/widgets/pull/42"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_async_client)

    pr_url = await git_connector.apply_job_to_repo(
        task_id="12345678-abcd", job_id="job-1", agent_name="Feature Developer", instruction="do X"
    )

    assert pr_url == "https://github.com/acme/widgets/pull/42"
    assert ("POST", "/repos/acme/widgets/git/refs") in calls
    assert ("POST", "/repos/acme/widgets/pulls") in calls
    assert created_blobs == ["blob-sha-0", "blob-sha-1"]


async def test_error_message_never_contains_token(monkeypatch):
    monkeypatch.setattr(settings, "git_connector_enabled", True)
    monkeypatch.setattr(settings, "github_token", "gh-secret-token")

    async def fake_get_job(job_id):
        return {"id": "job-1", "run_id": "run-1", "status": "SUCCEEDED"}

    async def fake_get_run(run_id):
        return {
            "nodes": [
                {
                    "node_id": "save_files",
                    "status": "SUCCEEDED",
                    "output": {"files": [{"path": "app/foo.py", "artifact_id": "art-1"}]},
                }
            ]
        }

    monkeypatch.setattr(orchestrator_client, "get_job", fake_get_job)
    monkeypatch.setattr(orchestrator_client, "get_run", fake_get_run)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Branch not found")

    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_async_client)

    with pytest.raises(git_connector.GitConnectorError) as exc_info:
        await git_connector.apply_job_to_repo(
            task_id="task-1", job_id="job-1", agent_name="a", instruction="i"
        )

    assert "gh-secret-token" not in str(exc_info.value)
