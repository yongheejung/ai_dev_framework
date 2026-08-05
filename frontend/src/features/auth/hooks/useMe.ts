import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { coreClient } from "@/shared/api/client";
import { clearToken } from "@/shared/auth/token-store";

import { useAuthContext } from "../AuthContext";
import type { MeResponse } from "../types";

export const ME_QUERY_KEY = ["auth", "me"];

export function useMe() {
  const { hasToken, setHasToken } = useAuthContext();

  const query = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: () => coreClient.get<MeResponse>("/me"),
    enabled: hasToken,
    retry: false,
  });

  // 토큰이 만료/무효화됐으면 /me가 401을 준다 — 저장된 토큰을 정리하고 로그아웃 상태로 되돌린다.
  useEffect(() => {
    if (query.isError && hasToken) {
      clearToken();
      setHasToken(false);
    }
  }, [query.isError, hasToken, setHasToken]);

  return query;
}
