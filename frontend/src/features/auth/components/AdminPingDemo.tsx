"use client";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/shared/api/client";

import { useAdminPing } from "../hooks/useAdminPing";
import { useMe } from "../hooks/useMe";

/** RBAC 데모: ROLE_ADMIN이 있는 계정으로 로그인해야 성공한다 (기본: admin/admin1234). */
export function AdminPingDemo() {
  const { data: me } = useMe();
  const adminPing = useAdminPing();

  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="outline"
        onClick={() => adminPing.mutate()}
        disabled={adminPing.isPending || !me}
      >
        {adminPing.isPending ? "호출 중..." : "관리자 핑 (/api/v1/admin/ping)"}
      </Button>
      {!me && <p className="text-sm text-muted-foreground">로그인 후 이용할 수 있습니다.</p>}
      {adminPing.data && <p className="text-sm text-foreground">성공: {adminPing.data}</p>}
      {adminPing.error && (
        <p className="text-sm text-destructive">
          {adminPing.error instanceof ApiError
            ? `${adminPing.error.code}: ${adminPing.error.message}`
            : adminPing.error.message}
        </p>
      )}
    </div>
  );
}
