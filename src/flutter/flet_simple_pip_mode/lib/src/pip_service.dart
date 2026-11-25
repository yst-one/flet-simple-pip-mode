import 'dart:async';

import 'package:flet/flet.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:simple_pip_mode/actions/pip_action.dart';
import 'package:simple_pip_mode/actions/pip_actions_layout.dart';
import 'package:simple_pip_mode/aspect_ratio.dart';
import 'package:simple_pip_mode/simple_pip.dart';

import 'pip_controller.dart';

class SimplePipModeService extends FletService {
  late final void Function(bool) _stateListener;
  late final void Function(PipAction) _actionListener;

  SimplePipModeService({required super.control});

  @override
  void init() {
    super.init();
    debugPrint("SimplePipModeService(${control.id}).init");
    control.addInvokeMethodListener(_invokeMethod);

    _stateListener = (active) {
      // Named event dataclasses on the Python side expect a payload map.
      control.triggerEvent(
        active ? "pip_entered" : "pip_exited",
        {"active": active},
      );
    };
    _actionListener = (action) {
      // Python PipAction enum values are lowercase (play, pause, ...), while
      // Dart's action.name is upper case. Convert so from_dict can resolve it.
      control.triggerEvent(
        "pip_action",
        {"action": action.name.toLowerCase()},
      );
    };
    PipController.instance.addStateListener(_stateListener);
    PipController.instance.addActionListener(_actionListener);
  }

  @override
  void dispose() {
    debugPrint("SimplePipModeService(${control.id}).dispose()");
    control.removeInvokeMethodListener(_invokeMethod);
    PipController.instance.removeStateListener(_stateListener);
    PipController.instance.removeActionListener(_actionListener);
    super.dispose();
  }

  Future<bool> _safe(Future<bool> Function() action) async {
    try {
      return await action();
    } catch (e) {
      debugPrint("SimplePipModeService: platform unavailable ($e)");
      return false;
    }
  }

  static AspectRatio _aspectRatio(dynamic args) {
    final value = args is Map ? args["aspect_ratio"] : null;
    if (value is List && value.length == 2) {
      return ((value[0] as num).toInt(), (value[1] as num).toInt());
    }
    return (16, 9);
  }

  static bool _flag(dynamic args, String key, bool defaultValue) {
    final value = args is Map ? args[key] : null;
    return value is bool ? value : defaultValue;
  }

  /// Wait until the freshly-pushed control tree has been painted.
  ///
  /// The Python side flips `PipWidget.active` and pushes it right before
  /// invoking `enter_pip_mode`. Building the new widget tree is scheduled for
  /// the next frame, so without this the system can snapshot the previous
  /// (main-page) frame as the PiP window. One painted frame is enough.
  Future<void> _waitForPaintedFrame() async {
    final completer = Completer<void>();
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!completer.isCompleted) completer.complete();
    });
    SchedulerBinding.instance.scheduleFrame();
    await completer.future.timeout(
      const Duration(seconds: 2),
      onTimeout: () {},
    );
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    final pip = PipController.instance.pip;
    switch (name) {
      case "is_pip_available":
        return await _safe(() => SimplePip.isPipAvailable);
      case "is_auto_pip_available":
        return await _safe(() => SimplePip.isAutoPipAvailable);
      case "is_pip_activated":
        return await _safe(() => SimplePip.isPipActivated);
      case "enter_pip_mode":
        await _waitForPaintedFrame();
        return await _safe(
          () => pip.enterPipMode(
            aspectRatio: _aspectRatio(args),
            autoEnter: _flag(args, "auto_enter", false),
            seamlessResize: _flag(args, "seamless_resize", false),
          ),
        );
      case "set_auto_pip_mode":
        await _waitForPaintedFrame();
        return await _safe(
          () => pip.setAutoPipMode(
            aspectRatio: _aspectRatio(args),
            autoEnter: _flag(args, "auto_enter", true),
            seamlessResize: _flag(args, "seamless_resize", false),
          ),
        );
      case "set_pip_actions_layout":
        final layoutName = args is Map ? args["layout"] : null;
        final layout = PipActionsLayout.values.firstWhere(
          (e) => e.name == layoutName,
          orElse: () => PipActionsLayout.none,
        );
        return await _safe(() => pip.setPipActionsLayout(layout));
      case "set_is_playing":
        return await _safe(
          () => pip.setIsPlaying(_flag(args, "is_playing", false)),
        );
      default:
        throw Exception("Unknown SimplePipMode method: $name");
    }
  }
}
