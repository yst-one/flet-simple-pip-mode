import 'package:flet/flet.dart';
import 'package:flutter/widgets.dart';

/// Builds [child] normally and [pip_child] when the Python-side `active`
/// attribute is true. Driven from Python so the swap can happen *before*
/// the system takes the PiP window snapshot.
class PipWidgetControl extends StatelessWidget {
  final Control control;

  const PipWidgetControl({super.key, required this.control});

  @override
  Widget build(BuildContext context) {
    final child = control.buildWidget("child") ?? const SizedBox.shrink();
    final pipChild = control.buildWidget("pip_child") ?? child;
    final active = control.getBool("active", false) ?? false;

    return LayoutControl(
      control: control,
      child: active ? pipChild : child,
    );
  }
}
