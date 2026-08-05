import { NextRequest, NextResponse } from "next/server";

/**
 * core-service/bff-service로 요청을 그대로 전달하는 서버 사이드 프록시.
 * next.config.ts의 rewrites()는 빌드 시점에 한 번 평가되어 라우트 매니페스트에 박히기 때문에
 * 컨테이너 런타임에 환경변수를 바꿔도 반영되지 않는다(직접 겪은 문제) — 그래서 요청마다
 * 실행되는 Route Handler로 프록시해서 process.env를 항상 그 요청 시점의 값으로 읽는다.
 */

const FORWARD_REQUEST_HEADERS = ["content-type", "authorization", "x-tenant-id", "accept"];

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  for (const name of FORWARD_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (!headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  return headers;
}

async function forward(
  request: NextRequest,
  path: string[],
  targetBaseUrl: string,
): Promise<NextResponse> {
  const url = `${targetBaseUrl}/api/${path.join("/")}${request.nextUrl.search}`;
  const hasBody = !["GET", "HEAD"].includes(request.method);

  const response = await fetch(url, {
    method: request.method,
    headers: buildForwardHeaders(request),
    body: hasBody ? await request.text() : undefined,
  });

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}

type RouteParams = { params: Promise<{ path: string[] }> };

/** getTargetBaseUrl은 요청이 올 때마다 호출된다 — process.env를 그 시점 값으로 읽기 위함. */
export function createBackendProxy(getTargetBaseUrl: () => string) {
  const handler = async (request: NextRequest, { params }: RouteParams) => {
    const { path } = await params;
    return forward(request, path, getTargetBaseUrl());
  };

  return { GET: handler, POST: handler, PUT: handler, PATCH: handler, DELETE: handler };
}
