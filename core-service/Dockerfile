# ---- build ----
FROM eclipse-temurin:21-jdk AS build
WORKDIR /workspace

# 의존성만 먼저 받아서 레이어 캐싱 — build.gradle.kts가 안 바뀌면 이 레이어는 재사용된다.
COPY gradlew gradlew.bat ./
COPY gradle ./gradle
COPY build.gradle.kts settings.gradle.kts ./
RUN chmod +x gradlew && ./gradlew --no-daemon dependencies > /dev/null 2>&1 || true

COPY src ./src
RUN ./gradlew --no-daemon bootJar -x test

# ---- runtime ----
# SQLite 드라이버가 glibc 기준 네이티브 라이브러리를 번들하므로 alpine(musl) 대신 debian 계열을 쓴다.
FROM eclipse-temurin:21-jre
RUN useradd -r -m appuser
WORKDIR /app
# WORKDIR은 root 소유로 생성되므로 appuser로 chown 해줘야 sqlite 프로파일(현재 디렉터리에
# DB 파일을 직접 생성)이 컨테이너 안에서도 동작한다.
RUN chown appuser:appuser /app
COPY --from=build --chown=appuser:appuser /workspace/build/libs/*.jar app.jar
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
