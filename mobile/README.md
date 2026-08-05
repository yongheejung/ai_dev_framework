# mobile

AI Dev Framework의 모바일 앱 표준 (Flutter). `frontend.md` 스펙의 "하나의 코드로 iOS/Android
동시 출시" 원칙을 따르며, `frontend/`(웹)와 최대한 같은 구조 원칙을 쓴다.

## ⚠️ 빌드 미검증

이 환경(Windows, Flutter/Android SDK/Xcode 미설치)에서는 `flutter analyze`/`flutter build`를
실행해볼 수 없었다 — **코드는 작성했지만 실제로 컴파일/실행해서 검증하지 못했다.** 아래 "다음 단계"에
정리해둔 순서대로 로컬 Flutter 환경에서 먼저 `flutter pub get` + `flutter analyze`를 돌려볼 것.

## 폴더 구조

```
lib/
├── main.dart              # 앱 진입점, 테마(라이트/다크) 설정
├── home_screen.dart        # 메인 화면 (웹의 app/page.tsx에 대응)
├── core/
│   ├── api_client.dart     # bffClient/coreClient — core/bff의 ApiResponse 포맷 공통 클라이언트
│   ├── app_config.dart     # 백엔드 주소 (--dart-define으로 환경별 주입)
│   ├── theme.dart          # 색상 토큰 (ColorScheme.fromSeed — 웹의 globals.css 원칙과 동일)
│   └── token_store.dart    # JWT 보관 (flutter_secure_storage)
└── features/
    ├── agent_task/         # bff-service agent-tasks 연동 예시 (웹의 features/agent-task와 동일 도메인)
    │   ├── models/
    │   ├── data/            # Repository (HTTP 호출)
    │   ├── providers/        # Riverpod AsyncNotifier (TanStack Query에 대응)
    │   └── screens/
    └── auth/               # core-service JWT 로그인/회원가입/RBAC (웹의 features/auth와 동일 도메인)
        ├── models/
        ├── data/
        ├── providers/
        ├── screens/         # LoginScreen
        └── widgets/          # AdminPingButton (RBAC 데모)
```

## 원칙 (웹 frontend와 동일한 것들)

1. **백엔드 호출은 항상 `core/api_client.dart`의 `bffClient`/`coreClient`로만.** 화면/위젯에서 직접
   `http` 패키지를 쓰지 않는다.
2. **서버 상태는 Riverpod `AsyncNotifier`로만 관리** (`features/<domain>/providers/`) — 웹의
   TanStack Query 훅과 같은 역할. 화면(위젯)은 `ref.watch(...Provider)`로 구독만 한다.
3. **색상은 하드코딩 금지, `Theme.of(context).colorScheme`만 사용.** 브랜드 색상을 바꾸려면
   `core/theme.dart`의 `_seedColor` 한 줄만 바꾸면 된다.
4. 다크모드는 `ThemeMode.system`으로 OS 설정을 따라간다(`main.dart`) — 별도 토글 UI는 아직 없다.

## 웹과의 결정적인 차이: 백엔드 주소를 앱이 직접 안다

웹은 Next.js 서버가 브라우저 대신 백엔드를 프록시해서 브라우저가 백엔드 주소를 몰라도 됐다
(`frontend/README.md`의 "백엔드 연결" 참고). **모바일 앱은 그런 서버 사이드 중계가 없다** — 앱
바이너리 자체가 기기에서 실행되며 백엔드에 직접 접속해야 한다. 그래서:

- `AppConfig`의 `bffBaseUrl`/`coreBaseUrl`은 빌드 시점에 `--dart-define`으로 주입한다.
- 환경(dev/staging/prod)마다 다른 주소로 빌드해야 한다 — 웹처럼 "이미지 하나로 전부 대응"은 안 된다.

```bash
flutter run \
  --dart-define=BFF_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=CORE_BASE_URL=http://10.0.2.2:8080
```

`10.0.2.2`는 Android 에뮬레이터가 호스트 PC의 `localhost`를 가리키는 특수 주소다. 실기기/iOS
시뮬레이터는 실제 네트워크에서 접근 가능한 주소(사설 IP, 또는 배포된 도메인)를 넣어야 한다.

## 다음 단계 (로컬에서 해야 할 것)

1. Flutter SDK 설치 (https://docs.flutter.dev/get-started/install)
2. `flutter pub get` — 의존성 설치되면서 pubspec.yaml의 버전 제약이 실제로 맞는지도 같이 확인됨
3. `flutter analyze` — 이 세션에서 손으로 작성만 하고 못 돌려본 부분이라 문법/타입 오류가 있을 수 있음
4. core-service/bff-service를 로컬(`docker compose up`)에 띄운 상태에서 에뮬레이터로 `flutter run`
5. 로그인(admin/admin1234) → 관리자 핑 성공, 에이전트 작업 등록/조회까지 실제로 눌러서 확인

## CI/CD (제안)

물리 Mac 없이 iOS 빌드를 검증하려면 GitHub Actions의 `macos-latest` 러너(Xcode 사전 설치됨)를 쓰면
된다 — `subosito/flutter-action`으로 Flutter SDK를 세팅한 뒤 `flutter build ipa`/
`flutter build appbundle`을 돌리는 게 표준 패턴이다. 앱스토어 실제 배포까지 가려면 Apple Developer
Program 가입 + 인증서/프로비저닝 프로파일(iOS), 키스토어(Android)를 GitHub Secrets로 관리해야 한다
(보통 iOS 쪽은 `fastlane`을 같이 씀). 아직 GitHub 저장소가 없어서 워크플로우 파일은 만들지 않았다 —
필요해지면 `.github/workflows/mobile-ci.yml`로 추가하면 된다.

## 아직 안 된 것

- 실제 빌드/실행 검증 (위 "빌드 미검증" 참고)
- 다크모드 토글 UI (시스템 설정만 따라감)
- GitHub Actions CI 워크플로우 (저장소 생기면 추가)
