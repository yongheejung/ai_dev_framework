import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/token_store.dart';
import '../data/auth_repository.dart';
import '../models/auth_models.dart';

/// 로그인 상태(null이면 비로그인)를 앱 전역에서 관리한다. 웹의 AuthContext + useMe를 합친 역할.
class AuthNotifier extends AsyncNotifier<MeResponse?> {
  @override
  Future<MeResponse?> build() async {
    final token = await TokenStore.read();
    if (token == null) return null;

    try {
      return await authRepository.me();
    } catch (_) {
      // 토큰이 만료/무효화됐으면 /me가 401을 준다 — 저장된 토큰을 정리한다.
      await TokenStore.clear();
      return null;
    }
  }

  Future<void> login({required String username, required String password}) async {
    final token = await authRepository.login(username: username, password: password);
    await TokenStore.write(token.accessToken);
    ref.invalidateSelf();
    await future;
  }

  Future<void> logout() async {
    await TokenStore.clear();
    state = const AsyncData(null);
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, MeResponse?>(AuthNotifier.new);
