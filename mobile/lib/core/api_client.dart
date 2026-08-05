import 'dart:convert';

import 'package:http/http.dart' as http;

import 'app_config.dart';
import 'token_store.dart';

class ApiException implements Exception {
  final String code;
  final String message;
  final int status;

  ApiException(this.code, this.message, this.status);

  @override
  String toString() => '$code: $message';
}

/// core-service/bff-service의 표준 ApiResponse({success, data, error}) 포맷에 맞춘 공통 클라이언트.
/// 웹(frontend)의 shared/api/client.ts와 같은 계약을 따른다 — 화면/프로바이더는 이 클라이언트를
/// 통해서만 백엔드를 호출하고, 직접 http 패키지를 쓰지 않는다.
class ApiClient {
  final String baseUrl;
  final bool attachAuth;
  final bool attachTenant;

  ApiClient({
    required this.baseUrl,
    this.attachAuth = false,
    this.attachTenant = false,
  });

  Future<T> get<T>(String path, T Function(dynamic json) parse) => _request('GET', path, null, parse);

  Future<T> post<T>(String path, Object? body, T Function(dynamic json) parse) =>
      _request('POST', path, body, parse);

  Future<Map<String, String>> _buildHeaders() async {
    final headers = <String, String>{'Content-Type': 'application/json'};

    if (attachTenant) {
      headers['X-Tenant-Id'] = AppConfig.defaultTenantId;
    }
    if (attachAuth) {
      final token = await TokenStore.read();
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }

    return headers;
  }

  Future<T> _request<T>(
    String method,
    String path,
    Object? body,
    T Function(dynamic json) parse,
  ) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = await _buildHeaders();

    final http.Response response;
    switch (method) {
      case 'GET':
        response = await http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await http.post(uri, headers: headers, body: body != null ? jsonEncode(body) : null);
        break;
      default:
        throw UnsupportedError('Unsupported method: $method');
    }

    final decoded = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    final success = decoded['success'] as bool? ?? false;

    if (!success) {
      final error = decoded['error'] as Map<String, dynamic>?;
      throw ApiException(
        error?['code'] as String? ?? 'UNKNOWN',
        error?['message'] as String? ?? '요청 처리 중 오류가 발생했습니다.',
        response.statusCode,
      );
    }

    return parse(decoded['data']);
  }
}

/// bff-service 호출용 (agent-tasks 등). 인증 불필요.
final bffClient = ApiClient(baseUrl: '${AppConfig.bffBaseUrl}/api/v1');

/// core-service 호출용 (auth/me/admin 등). JWT + 테넌트 헤더를 자동으로 붙인다.
final coreClient = ApiClient(
  baseUrl: '${AppConfig.coreBaseUrl}/api/v1',
  attachAuth: true,
  attachTenant: true,
);
