package com.aidevframework.core.api;

import com.aidevframework.core.common.ApiResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class MeController {

    @GetMapping("/api/v1/me")
    public ApiResponse<MeResponse> me(Authentication authentication) {
        List<String> roles = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .toList();
        return ApiResponse.success(new MeResponse(authentication.getName(), roles));
    }

    public record MeResponse(String username, List<String> roles) {
    }
}
