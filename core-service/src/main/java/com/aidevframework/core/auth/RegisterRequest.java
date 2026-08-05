package com.aidevframework.core.auth;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record RegisterRequest(
        @NotBlank(message = "아이디를 입력해 주세요.") String username,
        @NotBlank @Size(min = 8, message = "비밀번호는 8자 이상이어야 합니다.") String password) {
}
