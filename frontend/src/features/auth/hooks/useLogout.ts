import { useQueryClient } from "@tanstack/react-query";

import { clearToken } from "@/shared/auth/token-store";

import { useAuthContext } from "../AuthContext";
import { ME_QUERY_KEY } from "./useMe";

export function useLogout() {
  const { setHasToken } = useAuthContext();
  const queryClient = useQueryClient();

  return () => {
    clearToken();
    setHasToken(false);
    // setQueryData(key, undefined)는 TanStack Query가 "갱신 없음"으로 무시해버려서
    // 로그아웃해도 캐시된 사용자 정보가 안 지워지는 실제 버그가 있었다 — removeQueries로 고침.
    queryClient.removeQueries({ queryKey: ME_QUERY_KEY });
  };
}
