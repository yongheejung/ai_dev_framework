package com.aidevframework.core.tenant;

/**
 * 요청 스레드 동안 현재 테넌트 식별자를 보관한다.
 * 스키마 분리 멀티테넌시 전략에서 Hibernate 테넌트 리졸버가 이 값을 참조한다.
 */
public final class TenantContext {

    private static final ThreadLocal<String> CURRENT_TENANT = new ThreadLocal<>();

    private TenantContext() {
    }

    public static void set(String tenantId) {
        CURRENT_TENANT.set(tenantId);
    }

    public static String get() {
        return CURRENT_TENANT.get();
    }

    public static void clear() {
        CURRENT_TENANT.remove();
    }
}
