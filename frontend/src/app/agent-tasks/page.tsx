"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AgentTaskForm } from "@/features/agent-task/components/AgentTaskForm";
import { AgentTaskTable } from "@/features/agent-task/components/AgentTaskTable";
import { useAgentTasks } from "@/features/agent-task/hooks/useAgentTasks";

export default function AgentTasksPage() {
  const { data, isLoading, error } = useAgentTasks();

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>새 에이전트 작업 등록</CardTitle>
        </CardHeader>
        <CardContent>
          <AgentTaskForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>에이전트 작업 목록</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-sm text-muted-foreground">불러오는 중...</p>}
          {error && <p className="text-sm text-destructive">{error.message}</p>}
          {data && <AgentTaskTable tasks={data} />}
        </CardContent>
      </Card>
    </div>
  );
}
