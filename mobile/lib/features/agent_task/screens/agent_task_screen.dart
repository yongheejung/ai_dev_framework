import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../providers/agent_task_provider.dart';

class AgentTaskScreen extends ConsumerStatefulWidget {
  const AgentTaskScreen({super.key});

  @override
  ConsumerState<AgentTaskScreen> createState() => _AgentTaskScreenState();
}

class _AgentTaskScreenState extends ConsumerState<AgentTaskScreen> {
  final _agentNameController = TextEditingController();
  final _instructionController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _agentNameController.dispose();
    _instructionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_agentNameController.text.isEmpty || _instructionController.text.isEmpty) {
      return;
    }
    setState(() => _submitting = true);
    try {
      await ref.read(agentTaskListProvider.notifier).create(
            agentName: _agentNameController.text,
            instruction: _instructionController.text,
          );
      _agentNameController.clear();
      _instructionController.clear();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tasksAsync = ref.watch(agentTaskListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('에이전트 작업 관리')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                TextField(
                  controller: _agentNameController,
                  decoration: const InputDecoration(labelText: '에이전트 이름 (예: feature-developer)'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _instructionController,
                  decoration: const InputDecoration(labelText: '지시 내용'),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _submitting ? null : _submit,
                    child: Text(_submitting ? '등록 중...' : '작업 등록'),
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: tasksAsync.when(
              data: (tasks) {
                if (tasks.isEmpty) {
                  return const Center(child: Text('아직 등록된 작업이 없습니다.'));
                }
                return ListView.separated(
                  itemCount: tasks.length,
                  separatorBuilder: (context, index) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final task = tasks[index];
                    return ListTile(
                      title: Text(task.agentName),
                      subtitle: Text(task.instruction),
                      trailing: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(task.status),
                          Text(
                            DateFormat('yyyy.MM.dd HH:mm').format(task.createdAt),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stackTrace) => Center(child: Text('$error')),
            ),
          ),
        ],
      ),
    );
  }
}
