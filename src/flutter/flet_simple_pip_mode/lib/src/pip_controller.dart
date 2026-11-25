import 'package:flutter/foundation.dart';
import 'package:simple_pip_mode/actions/pip_action.dart';
import 'package:simple_pip_mode/simple_pip.dart';

/// Single shared SimplePip instance.
///
/// The plugin routes native callbacks through the fixed method channel
/// `puntito.simple_pip_mode`, which supports only one handler. Sharing one
/// controller prevents the service and widgets from overwriting each other.
class PipController {
  static final PipController instance = PipController._();

  PipController._();

  late final SimplePip _pip;
  bool _initialized = false;

  final ValueNotifier<bool> isActive = ValueNotifier<bool>(false);
  final List<void Function(bool)> _stateListeners = <void Function(bool)>[];
  final List<void Function(PipAction)> _actionListeners =
      <void Function(PipAction)>[];

  SimplePip get pip {
    ensureInitialized();
    return _pip;
  }

  void ensureInitialized() {
    if (_initialized) return;
    _initialized = true;
    _pip = SimplePip(
      onPipEntered: () {
        isActive.value = true;
        for (final listener in List<void Function(bool)>.of(_stateListeners)) {
          listener(true);
        }
      },
      onPipExited: () {
        isActive.value = false;
        for (final listener in List<void Function(bool)>.of(_stateListeners)) {
          listener(false);
        }
      },
      onPipAction: (action) {
        for (final listener
            in List<void Function(PipAction)>.of(_actionListeners)) {
          listener(action);
        }
      },
    );
  }

  void addStateListener(void Function(bool) listener) {
    ensureInitialized();
    _stateListeners.add(listener);
  }

  void removeStateListener(void Function(bool) listener) {
    _stateListeners.remove(listener);
  }

  void addActionListener(void Function(PipAction) listener) {
    ensureInitialized();
    _actionListeners.add(listener);
  }

  void removeActionListener(void Function(PipAction) listener) {
    _actionListeners.remove(listener);
  }
}
