"""Patch a Flet-generated Android project for Picture-in-Picture support.

simple_pip_mode needs two native changes in the host app:

1. ``android:supportsPictureInPicture="true"`` on the launcher activity.
2. ``MainActivity`` must extend ``PipCallbackHelperActivityWrapper`` so PiP
   enter/exit/action callbacks reach Dart (and therefore Python).

Flet's ``flet build`` does not expose either setting, so this script patches
the generated Flutter project in place. It is idempotent and safe to run after
every build.

Usage::

    python -m flet_simple_pip_mode.patch_android [FLUTTER_PROJECT_DIR]

``FLUTTER_PROJECT_DIR`` defaults to ``build/flutter`` in the current directory.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WRAPPER_IMPORT = "import cl.puntito.simple_pip_mode.PipCallbackHelperActivityWrapper"
WRAPPER_CLASS = "PipCallbackHelperActivityWrapper"
HELPER_MARKER = "pipCallbackHelper"
PIP_ATTRIBUTE = 'android:supportsPictureInPicture="true"'

FRAGMENT_ACTIVITY_BODY = """class MainActivity : FlutterFragmentActivity() {
    private val pipCallbackHelper = PipCallbackHelper()

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        pipCallbackHelper.configureFlutterEngine(flutterEngine)
    }

    override fun onPictureInPictureModeChanged(
        isInPictureInPictureMode: Boolean,
        newConfig: Configuration
    ) {
        super.onPictureInPictureModeChanged(isInPictureInPictureMode, newConfig)
        pipCallbackHelper.onPictureInPictureModeChanged(isInPictureInPictureMode)
    }
}"""


def patch_manifest(manifest: Path) -> bool:
    text = manifest.read_text(encoding="utf-8")
    if PIP_ATTRIBUTE in text:
        return False
    pattern = re.compile(r"(<activity\b[^>]*?)(/?>)", re.DOTALL)
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"No <activity> element found in {manifest}")
    text = text[: match.start()] + f"{match.group(1)} {PIP_ATTRIBUTE}{match.group(2)}" + text[match.end() :]
    manifest.write_text(text, encoding="utf-8")
    return True


def patch_main_activity(kt_file: Path) -> bool:
    text = kt_file.read_text(encoding="utf-8")
    if WRAPPER_CLASS in text:
        return False

    if HELPER_MARKER in text:
        # Re-patch an older helper injection with the corrected override
        # signature (newConfig is non-null on modern Android SDKs).
        updated, count = re.subn(
            r"class\s+MainActivity\s*:\s*FlutterFragmentActivity\s*\(\)\s*\{[\s\S]*",
            FRAGMENT_ACTIVITY_BODY + "\n",
            text,
            count=1,
        )
        if count == 1 and updated != text:
            kt_file.write_text(updated, encoding="utf-8")
            return True
        return False

    if "FlutterFragmentActivity" in text:
        # Flet 1.1.x templates use FlutterFragmentActivity. Wrapping it is not
        # possible (the plugin wrapper extends FlutterActivity), so wire the
        # callback helper directly instead.
        text = text.replace(
            "import io.flutter.embedding.android.FlutterFragmentActivity",
            "import android.content.res.Configuration\n"
            "import io.flutter.embedding.android.FlutterFragmentActivity\n"
            "import io.flutter.embedding.engine.FlutterEngine\n"
            "import cl.puntito.simple_pip_mode.PipCallbackHelper",
            1,
        )
        text, count = re.subn(
            r"class\s+MainActivity\s*:\s*FlutterFragmentActivity\s*\(\s*\)",
            FRAGMENT_ACTIVITY_BODY,
            text,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"Could not patch FlutterFragmentActivity in {kt_file}")
    else:
        if "import io.flutter.embedding.android.FlutterActivity" in text:
            text = text.replace(
                "import io.flutter.embedding.android.FlutterActivity",
                "import io.flutter.embedding.android.FlutterActivity\n" + WRAPPER_IMPORT,
                1,
            )
        else:
            text = WRAPPER_IMPORT + "\n" + text
        text, count = re.subn(
            r"class\s+MainActivity\s*:\s*FlutterActivity\s*\(\s*\)",
            f"class MainActivity : {WRAPPER_CLASS}()",
            text,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"Could not find 'class MainActivity : FlutterActivity()' in {kt_file}")

    kt_file.write_text(text, encoding="utf-8")
    return True


def patch(flutter_project: Path) -> list[str]:
    flutter_project = flutter_project.resolve()
    main_dir = flutter_project / "android" / "app" / "src" / "main"
    manifest = main_dir / "AndroidManifest.xml"
    if not manifest.exists():
        raise FileNotFoundError(f"Android project not found at {flutter_project}")

    changed: list[str] = []
    if patch_manifest(manifest):
        changed.append(str(manifest))

    for kt_file in sorted((main_dir / "kotlin").rglob("MainActivity.kt")):
        if patch_main_activity(kt_file):
            changed.append(str(kt_file))

    if not list((main_dir / "kotlin").rglob("MainActivity.kt")):
        raise FileNotFoundError(f"No MainActivity.kt found under {main_dir / 'kotlin'}")

    return changed


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    target = Path(argv[0]) if argv else Path("build/flutter")
    try:
        changed = patch(target)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"patch_android: {exc}", file=sys.stderr)
        return 1

    if changed:
        for path in changed:
            print(f"patched: {path}")
    else:
        print("patch_android: already patched, nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
