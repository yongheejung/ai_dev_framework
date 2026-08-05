import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// JWT를 기기의 보안 저장소(Keychain/Keystore)에 보관한다. 웹의 shared/auth/token-store.ts와
/// 같은 역할이지만, 모바일에서는 localStorage 대신 flutter_secure_storage를 쓰는 게 표준이다.
class TokenStore {
  TokenStore._();

  static const _storage = FlutterSecureStorage();
  static const _key = 'aidevframework.accessToken';

  static Future<String?> read() => _storage.read(key: _key);

  static Future<void> write(String token) =>
      _storage.write(key: _key, value: token);

  static Future<void> clear() => _storage.delete(key: _key);
}
