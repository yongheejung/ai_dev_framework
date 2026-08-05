import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'features/agent_task/screens/agent_task_screen.dart';
import 'features/auth/providers/auth_provider.dart';
import 'features/auth/screens/login_screen.dart';
import 'features/auth/widgets/admin_ping_button.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Dev Framework'),
        actions: [
          authState.when(
            data: (me) => me == null
                ? TextButton(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (context) => const LoginScreen()),
                    ),
                    child: const Text('로그인'),
                  )
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        child: Text('${me.username} (${me.roles.join(", ")})'),
                      ),
                      TextButton(
                        onPressed: () => ref.read(authProvider.notifier).logout(),
                        child: const Text('로그아웃'),
                      ),
                    ],
                  ),
            loading: () => const SizedBox.shrink(),
            error: (error, stackTrace) => const SizedBox.shrink(),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              title: const Text('에이전트 작업 관리'),
              subtitle: const Text('bff-service의 agent-tasks API와 연동된 예시 화면입니다.'),
              trailing: const Icon(Icons.arrow_forward),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (context) => const AgentTaskScreen()),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('core-service 인증 / RBAC 데모', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(
                    'core-service의 JWT 로그인과 역할 기반 인가(RBAC)가 실제로 연동되어 있습니다.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 12),
                  const AdminPingButton(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
