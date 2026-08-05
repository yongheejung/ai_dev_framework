import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AgentTaskLog(Base):
    """AI 에이전트에게 위임한 작업의 실행 기록.

    core-service의 User 테이블과는 별개로 bff-service가 직접 소유하는 데이터다 —
    BFF 레이어도 자체 DB 처리가 가능함을 보여주는 예시이자, 향후 app/agents/에서
    실제 에이전트 시스템을 연동할 때 작업 이력을 남기는 용도로 확장할 자리다.
    """

    __tablename__ = "agent_task_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name: Mapped[str] = mapped_column(String(100))
    instruction: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
