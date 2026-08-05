/// 웹(frontend)과 다르게 모바일 앱은 서버 사이드 프록시가 없다 — 앱이 백엔드 주소를 직접 알아야
/// 한다. 그래서 빌드 시점에 --dart-define으로 실제 주소를 주입한다 (예:
/// `flutter run --dart-define=BFF_BASE_URL=https://api.example.com/bff`).
///
/// 기본값은 Android 에뮬레이터에서 호스트 PC의 localhost를 가리키는 특수 주소(10.0.2.2)다.
/// 실제 기기나 iOS 시뮬레이터에서는 각각 다른 주소가 필요하니 반드시 --dart-define으로 넘길 것.
class AppConfig {
  AppConfig._();

  static const String bffBaseUrl = String.fromEnvironment(
    'BFF_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static const String coreBaseUrl = String.fromEnvironment(
    'CORE_BASE_URL',
    defaultValue: 'http://10.0.2.2:8080',
  );

  // 실제 멀티테넌트 UI(테넌트 선택 화면)는 아직 없다 — 웹과 동일하게 기본 테넌트 하나로 데모/개발한다.
  static const String defaultTenantId = String.fromEnvironment(
    'TENANT_ID',
    defaultValue: 'demo',
  );
}
