import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/shared/utils/format";

import type { AgentTask } from "../types";

export function AgentTaskTable({ tasks }: { tasks: AgentTask[] }) {
  if (tasks.length === 0) {
    return <p className="text-sm text-muted-foreground">아직 등록된 작업이 없습니다.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>에이전트</TableHead>
          <TableHead>지시 내용</TableHead>
          <TableHead>상태</TableHead>
          <TableHead>생성 시각</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((task) => (
          <TableRow key={task.id}>
            <TableCell className="font-medium">{task.agent_name}</TableCell>
            <TableCell>{task.instruction}</TableCell>
            <TableCell>{task.status}</TableCell>
            <TableCell>{formatDateTime(task.created_at)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
