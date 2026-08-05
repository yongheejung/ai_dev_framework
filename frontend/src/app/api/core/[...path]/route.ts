import { createBackendProxy } from "@/shared/api/proxy";

export const { GET, POST, PUT, PATCH, DELETE } = createBackendProxy(
  () => process.env.CORE_SERVICE_INTERNAL_URL ?? "http://localhost:8080",
);
