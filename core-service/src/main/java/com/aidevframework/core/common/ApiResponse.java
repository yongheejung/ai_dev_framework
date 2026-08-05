package com.aidevframework.core.common;

/**
 * 모든 API가 따라야 하는 표준 응답 포맷.
 * AI 에이전트가 생성하는 컨트롤러도 이 포맷을 그대로 사용해야 한다.
 */
public record ApiResponse<T>(boolean success, T data, ErrorPayload error) {

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, data, null);
    }

    public static <T> ApiResponse<T> failure(String code, String message) {
        return new ApiResponse<>(false, null, new ErrorPayload(code, message));
    }

    public record ErrorPayload(String code, String message) {
    }
}
