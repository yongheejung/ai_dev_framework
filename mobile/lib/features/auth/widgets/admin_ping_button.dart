import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../data/auth_repository.dart';
import '../providers/auth_provider.dart';

/// RBAC 데모 위젯. ROLE_ADMIN이 없는 계정으로 로그인하면 core-service가 403을 준다.
class AdminPingButton extends ConsumerStatefulWidget {
  const AdminPingButton({super.key});

  @override
  ConsumerState<AdminPingButton> createState() => _AdminPingButtonState();
}

class _AdminPingButtonState extends ConsumerState<AdminPingButton> {
  bool _loading = false;
  String? _result;
  String? _error;

  Future<void> _ping() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await authRepository.adminPing();
      setState(() => _result = result);
    } on ApiException catch (error) {
      setState(() => _error = '${error.code}: ${error.message}');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final me = ref.watch(authProvider).valueOrNull;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        OutlinedButton(
          onPressed: (me == null || _loading) ? null : _ping,
          child: Text(_loading ? '호출 중...' : '관리자 핑 (/api/v1/admin/ping)'),
        ),
        if (me == null)
          const Padding(
            padding: EdgeInsets.only(top: 4),
            child: Text('로그인 후 이용할 수 있습니다.'),
          ),
        if (_result != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('성공: $_result'),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
      ],
    );
  }
}
