package com.aidevframework.core.auth;

import com.aidevframework.core.common.ApiResponse;
import com.aidevframework.core.common.BusinessException;
import com.aidevframework.core.common.ErrorCode;
import jakarta.validation.Valid;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Set;

/**
 * 자체 회원가입/로그인 + JWT 발급. 새로 가입한 사용자는 기본적으로 USER 역할만 가진다.
 * ADMIN 역할이 필요한 도메인 로직을 짤 때는 이 컨트롤러가 아니라 별도 관리자 승격 절차를 통해 부여해야 한다.
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;

    public AuthController(UserRepository userRepository, PasswordEncoder passwordEncoder,
            AuthenticationManager authenticationManager, JwtService jwtService) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.authenticationManager = authenticationManager;
        this.jwtService = jwtService;
    }

    @PostMapping("/register")
    public ApiResponse<String> register(@Valid @RequestBody RegisterRequest request) {
        if (userRepository.existsByUsername(request.username())) {
            throw new BusinessException(ErrorCode.VALIDATION_FAILED, "이미 존재하는 사용자명입니다.");
        }
        User user = new User(request.username(), passwordEncoder.encode(request.password()), Set.of("USER"));
        userRepository.save(user);
        return ApiResponse.success(user.getUsername());
    }

    @PostMapping("/login")
    public ApiResponse<TokenResponse> login(@Valid @RequestBody LoginRequest request) {
        Authentication authentication;
        try {
            authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(request.username(), request.password()));
        } catch (BadCredentialsException ex) {
            throw new BusinessException(ErrorCode.UNAUTHORIZED, "아이디 또는 비밀번호가 올바르지 않습니다.");
        }

        String token = jwtService.issueToken(authentication.getName(), authentication.getAuthorities());
        return ApiResponse.success(new TokenResponse(token, "Bearer", jwtService.expirySeconds()));
    }
}
