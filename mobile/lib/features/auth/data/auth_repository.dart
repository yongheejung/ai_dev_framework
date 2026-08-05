import '../../../core/api_client.dart';
import '../models/auth_models.dart';

class AuthRepository {
  Future<TokenResponse> login({required String username, required String password}) => coreClient.post(
        '/auth/login',
        {'username': username, 'password': password},
        (json) => TokenResponse.fromJson(json as Map<String, dynamic>),
      );

  Future<String> register({required String username, required String password}) => coreClient.post(
        '/auth/register',
        {'username': username, 'password': password},
        (json) => json as String,
      );

  Future<MeResponse> me() =>
      coreClient.get('/me', (json) => MeResponse.fromJson(json as Map<String, dynamic>));

  /// RBAC 데모: ROLE_ADMIN이 없으면 core-service가 403을 준다.
  Future<String> adminPing() => coreClient.get('/admin/ping', (json) => json as String);
}

final authRepository = AuthRepository();
