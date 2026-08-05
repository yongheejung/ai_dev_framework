/**
 * core-service/bff-service의 표준 ApiResponse({ success, data, error }) 포맷에 맞춘
 * 공통 fetch 래퍼. 컴포넌트/훅에서 직접 fetch를 호출하지 말고 항상 bffClient/coreClient를 거친다.
 *
 * 브라우저는 항상 같은 출처(origin)의 상대 경로만 호출한다 — 실제 백엔드 주소는 Route Handler
 * (app/api/bff, app/api/core)가 서버 쪽에서(BFF_INTERNAL_URL / CORE_SERVICE_INTERNAL_URL
 * 환경변수로) 해석한다. 그래서 프론트는 core-service/bff-service의 실제 호스트를 몰라도 되고,
 * 배포 환경(dev/staging/prod)이 바뀌어도 이미지를 다시 빌드할 필요 없이 서버 환경변수만 바꾸면 된다.
 *
 * coreClient는 인터셉터처럼 모든 요청에 Authorization(JWT)과 X-Tenant-Id를 자동으로 붙인다 —
 * `shared/auth/token-store.ts`에 저장된 토큰을 읽는다. 토큰 재발급(refresh) 로직이 필요해지면
 * 여기 request() 안에서 401 응답을 가로채 처리하면 된다.
 */

import { getToken } from "@/shared/auth/token-store";

export interface ApiErrorPayload {
  code: string;
  message: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiErrorPayload | null;
}

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  tenantId?: string;
  body?: unknown;
}

interface ApiClientConfig {
  /** Authorization: Bearer <token> 헤더를 자동으로 붙인다 (토큰이 있을 때만). */
  auth?: boolean;
  /** X-Tenant-Id 헤더를 자동으로 붙인다. 호출 시 tenantId를 넘기면 그 값을, 안 넘기면 기본 테넌트를 쓴다. */
  tenant?: boolean;
}

// 실제 멀티테넌트 UI(테넌트 선택 화면)는 아직 없다 — 기본 테넌트 하나로 데모/개발한다.
const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "demo";

function createApiClient(basePath: string, config: ApiClientConfig = {}) {
  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { tenantId, headers, body, ...rest } = options;

    const finalHeaders = new Headers({ "Content-Type": "application/json" });
    if (config.tenant) {
      finalHeaders.set("X-Tenant-Id", tenantId ?? DEFAULT_TENANT_ID);
    } else if (tenantId) {
      finalHeaders.set("X-Tenant-Id", tenantId);
    }
    if (config.auth) {
      const token = getToken();
      if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
    }
    if (headers) {
      new Headers(headers).forEach((value, key) => finalHeaders.set(key, value));
    }

    const res = await fetch(`${basePath}${path}`, {
      ...rest,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    const payload = (await res.json()) as ApiResponse<T>;

    if (!res.ok || !payload.success) {
      throw new ApiError(
        payload.error?.code ?? "UNKNOWN",
        payload.error?.message ?? "요청 처리 중 오류가 발생했습니다.",
        res.status,
      );
    }

    return payload.data as T;
  }

  return {
    get: <T,>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "GET" }),
    post: <T,>(path: string, body?: unknown, options?: RequestOptions) =>
      request<T>(path, { ...options, method: "POST", body }),
  };
}

/** bff-service 호출용 (agent-tasks 등). /api/bff/v1/* → Route Handler → BFF_INTERNAL_URL */
export const bffClient = createApiClient("/api/bff/v1");

/** core-service 호출용 (auth/me/admin 등). JWT + 테넌트 헤더를 자동으로 붙인다. */
export const coreClient = createApiClient("/api/core/v1", { auth: true, tenant: true });
