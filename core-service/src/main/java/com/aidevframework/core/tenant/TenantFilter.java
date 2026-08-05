package com.aidevframework.core.tenant;

import com.aidevframework.core.common.ErrorCode;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * 요청 헤더(X-Tenant-Id)에서 테넌트를 추출해 TenantContext에 세팅한다.
 * actuator 헬스체크, 로그인 전 인증(auth) 경로 등 테넌트를 아직 알 수 없는 경로는 그냥 통과시킨다.
 */
@Component
public class TenantFilter extends HttpFilter {

    private static final String TENANT_HEADER = "X-Tenant-Id";

    @Override
    protected void doFilter(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        String path = request.getRequestURI();
        if (path.startsWith("/actuator") || path.startsWith("/api/v1/auth")) {
            chain.doFilter(request, response);
            return;
        }

        String tenantId = request.getHeader(TENANT_HEADER);
        if (tenantId == null || tenantId.isBlank()) {
            response.setStatus(ErrorCode.TENANT_NOT_RESOLVED.status().value());
            response.setCharacterEncoding("UTF-8");
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write(
                    "{\"success\":false,\"data\":null,\"error\":{\"code\":\"%s\",\"message\":\"%s\"}}"
                            .formatted(ErrorCode.TENANT_NOT_RESOLVED.name(), ErrorCode.TENANT_NOT_RESOLVED.defaultMessage()));
            return;
        }

        try {
            TenantContext.set(tenantId);
            chain.doFilter(request, response);
        } finally {
            TenantContext.clear();
        }
    }
}
