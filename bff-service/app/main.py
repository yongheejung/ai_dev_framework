from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import agent_tasks, ping
from app.core.config import settings
from app.core.responses import ApiResponse

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ping.router, prefix="/api/v1", tags=["ping"])
app.include_router(agent_tasks.router, prefix="/api/v1", tags=["agent-tasks"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ApiResponse.fail("VALIDATION_FAILED", str(exc.errors())).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # 표준 ApiResponse 포맷(AGENTS.md 0.1절)을 유지하기 위해 FastAPI 기본 {"detail": ...}
    # 응답 대신 이 핸들러를 거친다. 라우터에서 그냥 raise HTTPException(...)을 써도 된다.
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.fail(f"HTTP_{exc.status_code}", str(exc.detail)).model_dump(),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}
