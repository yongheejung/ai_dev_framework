"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";

import { useLogout } from "../hooks/useLogout";
import { useMe } from "../hooks/useMe";

export function AuthNav() {
  const { data: me, isLoading } = useMe();
  const logout = useLogout();

  if (isLoading) {
    return null;
  }

  if (!me) {
    return (
      <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground">
        로그인
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-muted-foreground">
        {me.username} ({me.roles.join(", ")})
      </span>
      <Button variant="ghost" size="sm" onClick={() => logout()}>
        로그아웃
      </Button>
    </div>
  );
}
