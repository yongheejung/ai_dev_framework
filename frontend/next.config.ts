import type { NextConfig } from "next";

// 백엔드 프록시는 next.config.ts의 rewrites()가 아니라 app/api/bff, app/api/core의
// Route Handler로 구현했다 — rewrites()는 next build 시점에 한 번 평가되어 라우트
// 매니페스트에 박히므로 컨테이너 런타임에 BFF_INTERNAL_URL 등을 바꿔도 반영되지 않는다
// (직접 겪은 문제). Route Handler는 요청마다 실행되므로 process.env를 그때그때 읽는다.
const nextConfig: NextConfig = {
  // Docker 이미지를 최소 크기로 만들기 위해 standalone 서버 번들을 생성한다.
  output: "standalone",
};

export default nextConfig;
