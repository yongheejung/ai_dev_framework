from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    created_at: datetime


@router.post("/agent-tasks", response_model=ApiResponse[AgentTaskResponse])
async def create_agent_task(
    request: CreateAgentTaskRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[AgentTaskResponse]:
    task = AgentTaskLog(agent_name=request.agent_name, instruction=request.instruction)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return ApiResponse.ok(AgentTaskResponse.model_validate(task))


@router.get("/agent-tasks", response_model=ApiResponse[list[AgentTaskResponse]])
async def list_agent_tasks(db: AsyncSession = Depends(get_db)) -> ApiResponse[list[AgentTaskResponse]]:
    result = await db.execute(select(AgentTaskLog).order_by(AgentTaskLog.created_at.desc()))
    tasks = result.scalars().all()
    return ApiResponse.ok([AgentTaskResponse.model_validate(t) for t in tasks])
