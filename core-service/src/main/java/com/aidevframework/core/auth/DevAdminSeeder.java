package com.aidevframework.core.auth;

import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.Set;

/**
 * 로컬 개발 편의를 위해 admin/admin1234 계정을 최초 1회 시딩한다.
 * "prod" 프로파일에서는 실행되지 않는다 — 운영 환경에서는 별도의 관리자 계정 발급 절차를 사용해야 한다.
 */
@Component
@Profile("!prod")
public class DevAdminSeeder implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public DevAdminSeeder(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) {
        if (!userRepository.existsByUsername("admin")) {
            userRepository.save(new User("admin", passwordEncoder.encode("admin1234"), Set.of("ADMIN", "USER")));
        }
    }
}
