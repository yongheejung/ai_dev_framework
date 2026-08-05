import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/agent_task_repository.dart';
import '../models/agent_task.dart';

/// TanStack Query의 useAgentTasks/useCreateAgentTask(웹)에 대응하는 서버 상태 관리.
/// 화면은 이 provider를 통해서만 목록을 읽고 작업을 등록한다.
class AgentTaskListNotifier extends AsyncNotifier<List<AgentTask>> {
  @override
  Future<List<AgentTask>> build() => agentTaskRepository.list();

  Future<void> create({required String agentName, required String instruction}) async {
    await agentTaskRepository.create(agentName: agentName, instruction: instruction);
    ref.invalidateSelf();
    await future;
  }
}

final agentTaskListProvider =
    AsyncNotifierProvider<AgentTaskListNotifier, List<AgentTask>>(AgentTaskListNotifier.new);
