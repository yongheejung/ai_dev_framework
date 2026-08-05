# ---- deps ----
FROM node:24-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- build ----
FROM node:24-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# 백엔드 주소(BFF_INTERNAL_URL/CORE_SERVICE_INTERNAL_URL)는 빌드 시점에 필요 없다 —
# app/api/bff, app/api/core의 Route Handler가 요청마다 런타임 환경변수를 읽어 프록시하므로
# dev/staging/prod마다 이미지를 다시 빌드하지 않고 환경변수만 바꿔서 배포한다.
RUN npm run build

# ---- runtime ----
FROM node:24-slim AS runtime
WORKDIR /app
RUN useradd -r -m appuser
ENV NODE_ENV=production
COPY --from=build --chown=appuser:appuser /app/public ./public
COPY --from=build --chown=appuser:appuser /app/.next/standalone ./
COPY --from=build --chown=appuser:appuser /app/.next/static ./.next/static
USER appuser
EXPOSE 3000
ENV PORT=3000
# Docker/Kubernetes가 컨테이너 환경변수 HOSTNAME을 파드/컨테이너 이름으로 자동 채워 넣는데,
# Next.js standalone 서버가 이 값을 바인드 주소로 써버려서 0.0.0.0이 아니라 그 이름(파드 IP)에만
# 리슨하게 된다 — 그 결과 kubectl port-forward나 localhost 접속이 ECONNREFUSED로 실패한다
# (Service/Ingress/Docker 포트 매핑을 통한 실제 트래픽은 파드 IP로 바로 붙어서 문제없이 통과했음,
# kind로 실제 재현/확인함). HOSTNAME을 0.0.0.0으로 명시해서 그 자동 주입을 덮어쓴다.
CMD ["sh", "-c", "HOSTNAME=0.0.0.0 node server.js"]
