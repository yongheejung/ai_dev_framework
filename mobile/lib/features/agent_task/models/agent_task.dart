class AgentTask {
  final String id;
  final String agentName;
  final String instruction;
  final String status;
  final DateTime createdAt;

  AgentTask({
    required this.id,
    required this.agentName,
    required this.instruction,
    required this.status,
    required this.createdAt,
  });

  factory AgentTask.fromJson(Map<String, dynamic> json) => AgentTask(
        id: json['id'] as String,
        agentName: json['agent_name'] as String,
        instruction: json['instruction'] as String,
        status: json['status'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}
