"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { useCreateAgentTask } from "../hooks/useAgentTasks";

export function AgentTaskForm() {
  const [agentName, setAgentName] = useState("");
  const [instruction, setInstruction] = useState("");
  const { mutate, isPending, error } = useCreateAgentTask();

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!agentName || !instruction) return;

    mutate(
      { agent_name: agentName, instruction },
      {
        onSuccess: () => {
          setAgentName("");
          setInstruction("");
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          placeholder="에이전트 이름 (예: feature-developer)"
          value={agentName}
          onChange={(event) => setAgentName(event.target.value)}
        />
        <Input
          placeholder="지시 내용"
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
        />
        <Button type="submit" disabled={isPending}>
          {isPending ? "등록 중..." : "작업 등록"}
        </Button>
      </div>
      {error && <p className="text-sm text-destructive">{error.message}</p>}
    </form>
  );
}
