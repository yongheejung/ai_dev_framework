package com.aidevframework.core.api;

import com.aidevframework.core.common.ApiResponse;
import com.aidevframework.core.tenant.TenantContext;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 골격이 정상 동작하는지(공통 응답 포맷 + 테넌트 필터) 확인하기 위한 헬스 체크용 엔드포인트.
 * AI 에이전트 A가 참고할 "표준 컨트롤러" 예시이기도 하다.
 */
@RestController
public class PingController {

    @GetMapping("/api/v1/ping")
    public ApiResponse<String> ping() {
        String tenantId = TenantContext.get();
        return ApiResponse.success(tenantId == null ? "pong" : "pong (tenant=" + tenantId + ")");
    }
}
