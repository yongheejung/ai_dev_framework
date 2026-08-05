class TokenResponse {
  final String accessToken;
  final String tokenType;
  final int expiresInSeconds;

  TokenResponse({
    required this.accessToken,
    required this.tokenType,
    required this.expiresInSeconds,
  });

  factory TokenResponse.fromJson(Map<String, dynamic> json) => TokenResponse(
        accessToken: json['accessToken'] as String,
        tokenType: json['tokenType'] as String,
        expiresInSeconds: json['expiresInSeconds'] as int,
      );
}

class MeResponse {
  final String username;
  final List<String> roles;

  MeResponse({required this.username, required this.roles});

  factory MeResponse.fromJson(Map<String, dynamic> json) => MeResponse(
        username: json['username'] as String,
        roles: (json['roles'] as List).cast<String>(),
      );
}
