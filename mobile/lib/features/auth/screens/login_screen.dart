import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../data/auth_repository.dart';
import '../providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _loginUsername = TextEditingController();
  final _loginPassword = TextEditingController();
  final _registerUsername = TextEditingController();
  final _registerPassword = TextEditingController();

  bool _loggingIn = false;
  bool _registering = false;
  String? _loginError;
  String? _registerError;
  String? _registerMessage;

  @override
  void dispose() {
    _loginUsername.dispose();
    _loginPassword.dispose();
    _registerUsername.dispose();
    _registerPassword.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    setState(() {
      _loggingIn = true;
      _loginError = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .login(username: _loginUsername.text, password: _loginPassword.text);
      if (mounted) Navigator.of(context).pop();
    } on ApiException catch (error) {
      setState(() => _loginError = error.message);
    } finally {
      if (mounted) setState(() => _loggingIn = false);
    }
  }

  Future<void> _register() async {
    setState(() {
      _registering = true;
      _registerError = null;
    });
    try {
      final username = await authRepository.register(
        username: _registerUsername.text,
        password: _registerPassword.text,
      );
      setState(() {
        _registerMessage = '$username 계정이 생성되었습니다. 로그인해 주세요.';
        _registerUsername.clear();
        _registerPassword.clear();
      });
    } on ApiException catch (error) {
      setState(() => _registerError = error.message);
    } finally {
      if (mounted) setState(() => _registering = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('로그인')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('로그인', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _loginUsername,
                    decoration: const InputDecoration(labelText: '아이디'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _loginPassword,
                    obscureText: true,
                    decoration: const InputDecoration(labelText: '비밀번호'),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _loggingIn ? null : _login,
                    child: Text(_loggingIn ? '로그인 중...' : '로그인'),
                  ),
                  if (_loginError != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _loginError!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Text(
                    '개발용 admin 계정: admin / admin1234',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('회원가입', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _registerUsername,
                    decoration: const InputDecoration(labelText: '아이디'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _registerPassword,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: '비밀번호 (8자 이상)',
                    ),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton(
                    onPressed: _registering ? null : _register,
                    child: Text(_registering ? '가입 중...' : '회원가입'),
                  ),
                  if (_registerError != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _registerError!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  if (_registerMessage != null) ...[
                    const SizedBox(height: 8),
                    Text(_registerMessage!),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
