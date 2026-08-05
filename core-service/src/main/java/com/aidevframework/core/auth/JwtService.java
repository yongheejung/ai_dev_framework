package com.aidevframework.core.auth;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Collection;
import java.util.List;

@Service
public class JwtService {

    private static final long EXPIRY_SECONDS = 3600;

    private final JwtEncoder jwtEncoder;

    public JwtService(JwtEncoder jwtEncoder) {
        this.jwtEncoder = jwtEncoder;
    }

    public long expirySeconds() {
        return EXPIRY_SECONDS;
    }

    public String issueToken(String username, Collection<? extends GrantedAuthority> authorities) {
        Instant now = Instant.now();
        // Spring Security가 인증 방식을 추적하려고 붙이는 FACTOR_PASSWORD 같은 pseudo-authority가
        // 섞여 있을 수 있어 ROLE_ 접두사가 붙은 실제 역할만 골라낸다.
        List<String> roles = authorities.stream()
                .map(GrantedAuthority::getAuthority)
                .filter(authority -> authority.startsWith("ROLE_"))
                .map(authority -> authority.substring(5))
                .toList();

        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer("core-service")
                .issuedAt(now)
                .expiresAt(now.plus(EXPIRY_SECONDS, ChronoUnit.SECONDS))
                .subject(username)
                .claim("roles", roles)
                .build();

        JwsHeader header = JwsHeader.with(SignatureAlgorithm.RS256).build();
        return jwtEncoder.encode(JwtEncoderParameters.from(header, claims)).getTokenValue();
    }
}
