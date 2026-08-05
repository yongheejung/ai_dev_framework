import { useMutation } from "@tanstack/react-query";

import { coreClient } from "@/shared/api/client";

/** RBAC 데모: ROLE_ADMIN이 없으면 core-service가 403을 준다. */
export function useAdminPing() {
  return useMutation({
    mutationFn: () => coreClient.get<string>("/admin/ping"),
  });
}
