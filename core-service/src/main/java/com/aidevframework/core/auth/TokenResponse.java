package com.aidevframework.core.auth;

public record TokenResponse(String accessToken, String tokenType, long expiresInSeconds) {
}
