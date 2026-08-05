import { useMutation } from "@tanstack/react-query";

import { coreClient } from "@/shared/api/client";

import type { RegisterInput } from "../types";

export function useRegister() {
  return useMutation({
    mutationFn: (input: RegisterInput) => coreClient.post<string>("/auth/register", input),
  });
}
