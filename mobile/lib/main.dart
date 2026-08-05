import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';
import 'home_screen.dart';

void main() {
  runApp(const ProviderScope(child: AiDevFrameworkApp()));
}

class AiDevFrameworkApp extends StatelessWidget {
  const AiDevFrameworkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Dev Framework',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      home: const HomeScreen(),
    );
  }
}
