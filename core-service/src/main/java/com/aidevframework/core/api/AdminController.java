package com.aidevframework.core.api;

import com.aidevframework.core.common.ApiResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * RBAC 데모용 엔드포인트. 경로 기반 규칙(SecurityConfig의 /api/v1/admin/**)과
 * 메서드 기반 규칙(@PreAuthorize) 둘 다 걸어서, 이후 도메인 컨트롤러가 어느 쪽 패턴을
 * 따라도 되는지 예시로 남겨둔다.
 */
@RestController
public class AdminController {

    @GetMapping("/api/v1/admin/ping")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<String> adminPing() {
        return ApiResponse.success("admin pong");
    }
}
