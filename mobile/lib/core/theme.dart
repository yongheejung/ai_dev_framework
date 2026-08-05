import 'package:flutter/material.dart';

/// 색상을 위젯에서 직접 하드코딩하지 않는다 — 항상 Theme.of(context).colorScheme을 통해 쓴다.
/// 브랜드 색상을 바꾸려면 이 파일의 seedColor 한 줄만 바꾸면 앱 전체에 반영된다
/// (웹의 globals.css 디자인 토큰과 동일한 원칙 — ColorScheme.fromSeed가 그 역할을 한다).
class AppTheme {
  AppTheme._();

  static const _seedColor = Color(0xFF171717);

  static final ThemeData light = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: _seedColor,
      brightness: Brightness.light,
    ),
  );

  static final ThemeData dark = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: _seedColor,
      brightness: Brightness.dark,
    ),
  );
}
