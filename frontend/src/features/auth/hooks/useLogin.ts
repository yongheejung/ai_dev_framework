import { useMutation, useQueryClient } from "@tanstack/react-query";

import { coreClient } from "@/shared/api/client";
import { setToken } from "@/shared/auth/token-store";

import { useAuthContext } from "../AuthContext";
import type { LoginInput, TokenResponse } from "../types";
import { ME_QUERY_KEY } from "./useMe";

export function useLogin() {
  const { setHasToken } = useAuthContext();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: LoginInput) => coreClient.post<TokenResponse>("/auth/login", input),
    onSuccess: (token) => {
      setToken(token.accessToken);
      setHasToken(true);
      queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
    },
  });
}
