import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { bffClient } from "@/shared/api/client";

import type { AgentTask, CreateAgentTaskInput } from "../types";

const AGENT_TASKS_KEY = ["agent-tasks"];

export function useAgentTasks() {
  return useQuery({
    queryKey: AGENT_TASKS_KEY,
    queryFn: () => bffClient.get<AgentTask[]>("/agent-tasks"),
  });
}

export function useCreateAgentTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateAgentTaskInput) => bffClient.post<AgentTask>("/agent-tasks", input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: AGENT_TASKS_KEY });
    },
  });
}
