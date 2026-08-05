export interface AgentTask {
  id: string;
  agent_name: string;
  instruction: string;
  status: string;
  created_at: string;
}

export interface CreateAgentTaskInput {
  agent_name: string;
  instruction: string;
}
