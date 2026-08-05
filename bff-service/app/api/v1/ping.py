from fastapi import APIRouter, Header

from app.core.responses import ApiResponse

router = APIRouter()


@router.get("/ping", response_model=ApiResponse[str])
async def ping(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")) -> ApiResponse[str]:
    message = "pong" if x_tenant_id is None else f"pong (tenant={x_tenant_id})"
    return ApiResponse.ok(message)
