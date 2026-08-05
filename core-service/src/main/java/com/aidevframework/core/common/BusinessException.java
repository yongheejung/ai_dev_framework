package com.aidevframework.core.common;

/**
 * 비즈니스 로직에서 의도적으로 던지는 예외. AI 에이전트가 생성하는 서비스 코드도
 * 이 예외를 통해 실패를 표현해야 GlobalExceptionHandler가 표준 응답으로 변환할 수 있다.
 */
public class BusinessException extends RuntimeException {

    private final ErrorCode errorCode;

    public BusinessException(ErrorCode errorCode) {
        super(errorCode.defaultMessage());
        this.errorCode = errorCode;
    }

    public BusinessException(ErrorCode errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public ErrorCode errorCode() {
        return errorCode;
    }
}
