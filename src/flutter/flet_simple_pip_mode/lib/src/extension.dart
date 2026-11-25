import 'package:flet/flet.dart';
import 'package:flutter/widgets.dart';

import 'pip_service.dart';
import 'pip_widget.dart';

class Extension extends FletExtension {
  @override
  Widget? createWidget(Key? key, Control control) {
    switch (control.type) {
      case "PipWidget":
        return PipWidgetControl(key: key, control: control);
      default:
        return null;
    }
  }

  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "SimplePipMode":
        return SimplePipModeService(control: control);
      default:
        return null;
    }
  }
}
