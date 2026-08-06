from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.git_connector import GitConnectorDisabled, GitConnectorError, apply_job_to_repo
from app.agents.orchestrator_client import OrchestratorError, orchestrator_client
from app.core.config import settings
from app.core.db import get_db
from app.core.responses import ApiResponse
from app.models import AgentTaskLog

router = APIRouter()


class CreateAgentTaskRequest(BaseModel):
    agent_name: str
    instruction: str


class AgentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_name: str
    instruction: str
    status: str
    job_id: str | None = None
    run_id: str | None = None
    delegation_error: str | None = None
    pr_url: str | None = None
    git_connector_error: str | None = None
    created_at: datetime


@router.post("/agent-tasks", response_model=ApiResponse[AgentTaskResponse])
async def create_agent_task(
    request: CreateAgentTaskRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[AgentTaskResponse]:
    task = AgentTaskLog(agent_name=request.agent_name, instruction=request.instruction)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 로그 기록은 오케스트레이터 위임 성공 여부와 무관하게 항상 남는다 — 위임 실패는
    # status="DELEGATION_FAILED" + delegation_error로 드러난다(요청 자체를 실패시키지 않음).
    try:
        job = await orchestrator_client.create_job(
            workspace_id=settings.orchestrator_workspace_id,
            template_id=settings.orchestrator_job_template_id,
            title=f"[{request.agent_name}] {request.instruction[:80]}",
            inputs={"goal": request.instruction},
        )
        started = await orchestrator_client.start_job(job["id"])
        task.job_id = started["id"]
        task.run_id = started.get("run_id")
        task.status = started.get("status", "QUEUED")
    except OrchestratorError as exc:
        task.status = "DELEGATION_FAILED"
        task.delegation_error = str(exc)[:2000]

    await db.commit()
    await db.refresh(task)
    return ApiResponse.ok(AgentTaskResponse.model_validate(task))


@router.get("/agent-tasks", response_model=ApiResponse[list[AgentTaskResponse]])
async def list_agent_tasks(db: AsyncSession = Depends(get_db)) -> ApiResponse[list[AgentTaskResponse]]:
    result = await db.execute(select(AgentTaskLog).order_by(AgentTaskLog.created_at.desc()))
    tasks = result.scalars().all()
    return ApiResponse.ok([AgentTaskResponse.model_validate(t) for t in tasks])


@router.post("/agent-tasks/{task_id}/sync", response_model=ApiResponse[AgentTaskResponse])
async def sync_agent_task(
    task_id: str, db: AsyncSession = Depends(get_db)
) -> ApiResponse[AgentTaskResponse]:
    """오케스트레이터에서 최신 Job 상태를 가져와 로컬 status를 맞추고, SUCCEEDED로 막 전환됐으면
    git 커넥터(Phase C)를 트리거해 PR을 연다.

    승인(human 노드)은 아직 오케스트레이터 자체 UI에서 처리하므로, 승인 여부를 반영하려면
    사람이 그쪽에서 처리한 뒤 이 엔드포인트를 다시 호출해야 한다(웹훅이 없어 폴링 방식 —
    docs/06-ai-agent-integration.md 2.1.2절).
    """
    task = await db.get(AgentTaskLog, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="agent task not found")
    if task.job_id is None:
        raise HTTPException(
            status_code=409, detail="this task was never delegated to the orchestrator"
        )

    try:
        job = await orchestrator_client.get_job(task.job_id)
    except OrchestratorError as exc:
        task.delegation_error = str(exc)[:2000]
        await db.commit()
        await db.refresh(task)
        return ApiResponse.ok(AgentTaskResponse.model_validate(task))

    previous_status = task.status
    task.status = job.get("status", task.status)
    task.run_id = job.get("run_id", task.run_id)

    # pr_url이 이미 있으면 이 task는 이미 반영됐다 — 중복으로 다시 PR을 만들지 않는다(멱등성).
    just_succeeded = task.status == "SUCCEEDED" and previous_status != "SUCCEEDED"
    if just_succeeded and task.pr_url is None:
        try:
            task.pr_url = await apply_job_to_repo(
                task_id=task.id,
                job_id=task.job_id,
                agent_name=task.agent_name,
                instruction=task.instruction,
            )
            task.git_connector_error = None
        except GitConnectorDisabled:
            pass  # 기본 상태 — 명시적으로 켜기 전까지는 조용히 건너뛴다.
        except GitConnectorError as exc:
            task.git_connector_error = str(exc)[:2000]

    await db.commit()
    await db.refresh(task)
    return ApiResponse.ok(AgentTaskResponse.model_validate(task))
