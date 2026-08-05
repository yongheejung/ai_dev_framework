from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorPayload(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    """core-service(Spring Boot)의 ApiResponse와 동일한 포맷.

    두 서비스의 응답 형태를 맞춰둬야 프론트엔드/AI 에이전트가
    어느 백엔드를 호출하든 같은 방식으로 처리할 수 있다.
    """

    success: bool
    data: T | None = None
    error: ErrorPayload | None = None

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: str, message: str) -> "ApiResponse[T]":
        return cls(success=False, data=None, error=ErrorPayload(code=code, message=message))
