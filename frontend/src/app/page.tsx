import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AdminPingDemo } from "@/features/auth/components/AdminPingDemo";

export default function Home() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">AI Dev Framework</h1>
        <p className="mt-1 text-muted-foreground">
          core-service / bff-service 위에 얹히는 표준 프론트엔드 골격입니다.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>에이전트 작업 관리</CardTitle>
          <CardDescription>
            bff-service의 agent-tasks API와 실제로 연동된 예시 도메인입니다. features/agent-task 폴더
            구조를 참고해서 새 도메인을 추가하세요.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/agent-tasks">바로가기</Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>core-service 인증 / RBAC 데모</CardTitle>
          <CardDescription>
            core-service의 JWT 로그인과 역할 기반 인가(RBAC)가 실제로 연동되어 있습니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AdminPingDemo />
        </CardContent>
      </Card>
    </div>
  );
}
