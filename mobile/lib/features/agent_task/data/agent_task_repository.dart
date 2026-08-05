import '../../../core/api_client.dart';
import '../models/agent_task.dart';

class AgentTaskRepository {
  Future<List<AgentTask>> list() => bffClient.get(
        '/agent-tasks',
        (json) => (json as List)
            .map((item) => AgentTask.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  Future<AgentTask> create({required String agentName, required String instruction}) => bffClient.post(
        '/agent-tasks',
        {'agent_name': agentName, 'instruction': instruction},
        (json) => AgentTask.fromJson(json as Map<String, dynamic>),
      );
}

final agentTaskRepository = AgentTaskRepository();
