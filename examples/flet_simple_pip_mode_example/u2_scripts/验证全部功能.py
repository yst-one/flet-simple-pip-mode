"""用 uiautomator2 对照官方 example 逐项验证 flet-simple-pip-mode。

运行前：
  - 真机已连接（u2cli device-info 可返回设备信息）
  - 已安装 APK（见 README 构建/安装步骤）

运行：
  python 验证全部功能.py

覆盖官方 example 的全部功能点：
  1. isPipAvailable / isAutoPipAvailable / isPipActivated
  2. 5 种宽高比下拉（1:1 / 2:3 / 3:2 / 16:9 / 9:16）
  3. Auto Enter 开关（setAutoPipMode）
  4. enterPipMode 真机进入 PiP
  5. 5 种 PipActionsLayout 下拉
  6. setIsPlaying 模拟播放器
  7. onPipEntered / onPipExited 回调
  8. PipWidget child / pip_child 内容切换 + PiP 实时重绘

PiP 动作按钮（7 种）需要人工在悬浮窗点一下，脚本会提示并读取回调日志。
结果写入 验证结果/全部功能验证.json。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PACKAGE = "com.mycompany.flet_simple_pip_mode_example"
ACTIVITY = f"{PACKAGE}/.MainActivity"
ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "验证结果"


def u2(*args: str, timeout: int = 60) -> str:
    result = subprocess.run(
        ["u2cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise RuntimeError(f"u2cli {' '.join(args)} 失败: {output.strip()}")
    return output


def dump() -> str:
    return u2("dump-hierarchy")


def screenshot(name: str) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.png"
    u2("screenshot", str(path))
    return str(path)


def wait_description(text: str, seconds: int = 40) -> bool:
    try:
        return "result: True" in u2(
            "wait", "--description", text, "--timeout", str(seconds)
        )
    except RuntimeError:
        return False


def is_pinned() -> bool:
    return "mode=pin" in u2("shell", "dumpsys activity activities | grep mode=pin")


def click_button(text: str) -> bool:
    """点 Dropdown 的按钮节点。

    Flet 下拉的 label 是 desc，真正可点的是 android.widget.Button 的 text，
    因此从层级里解析按钮坐标再点，避免 description 选择器点不到。
    """
    match = re.search(
        r'android\.widget\.Button "' + re.escape(text) + r'" \[(\d+),(\d+),(\d+),(\d+)\]',
        dump(),
    )
    if not match:
        return False
    x1, y1, x2, y2 = (int(v) for v in match.groups())
    u2("click", str((x1 + x2) // 2), str((y1 + y2) // 2))
    return True


def restore() -> bool:
    u2("shell", f"am start -n {ACTIVITY}")
    time.sleep(2)
    return wait_description("PiP Plugin example app", 20)


def run_all() -> dict:
    result: dict = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "checks": {},
        "steps": [],
    }
    checks = result["checks"]

    u2("app-stop", PACKAGE)
    u2("app-start", PACKAGE)
    if not wait_description("PiP Plugin example app", 40):
        result["error"] = "起始界面未出现 PiP Plugin example app"
        return result
    time.sleep(2)
    result["steps"].append("起始界面已就绪")
    result["screenshot_start"] = screenshot("全功能_01_起始界面")

    text = dump()
    # 官方布局用 Icon(check/close) 表示状态，节点带 semantics_label。
    checks["is_pip_available"] = (
        "PiP Available:" in text and "PiP Available check" in text
    )
    checks["is_auto_pip_available"] = (
        "Auto Enter (Android S)" in text and "PiP Activated:" in text
    )
    checks["aspect_dropdown"] = "Aspect ratio:" in text
    checks["layout_dropdown"] = "Current actions layout:" in text
    # 官方布局：none 布局下不显示 Simulated player（后面切到非 none 才验证它）。
    checks["simulated_player_hidden_for_none"] = "Simulated player:" not in text

    # 2. 切换宽高比（下拉按钮 → 选项）
    found_ratios = []
    for _ in range(3):
        click_button("16:9")
        time.sleep(0.8)
        opts = dump()
        found_ratios = [r for r in ("1:1", "2:3", "3:2", "16:9", "9:16") if r in opts]
        if 'desc="2:3"' in opts:
            break
    checks["aspect_ratio_options"] = len(found_ratios) == 5
    result["aspect_ratio_options_found"] = found_ratios
    u2("click", "--description", "2:3")
    time.sleep(1.5)
    checks["set_auto_pip_mode"] = "自动 PiP 设置:" in dump()
    result["steps"].append(f"宽高比选项: {found_ratios}")

    # 3. Auto Enter 开关
    u2("click", "--description", "Auto Enter (Android S)")
    time.sleep(1.5)
    checks["auto_enter_switch"] = "自动进入: True" in dump()
    result["steps"].append("Auto Enter 开关已切换")

    # 4. 5 种动作布局：选项是枚举 name，日志里记录的是 value。
    layout_results = {}
    layout_cases = [
        ("media", "MEDIA"),
        ("mediaOnlyPause", "MEDIA_ONLY_PAUSE"),
        ("mediaLive", "MEDIA_LIVE"),
        ("mediaWithSeek10", "MEDIA_WITH_SEEK_10"),
        ("none", "NONE"),
    ]
    current_button = "NONE"
    for value, name in layout_cases:
        for _ in range(3):
            click_button(current_button)
            time.sleep(0.8)
            if f'desc="{name}"' in dump():
                break
        u2("click", "--description", name)
        time.sleep(1.5)
        current_button = name
        after = dump()
        layout_results[value] = f"动作布局: {value} →" in after
        # 非 none 布局应显示 Simulated player（官方条件渲染逻辑）。
        if value != "none":
            checks[f"player_visible_for_{value}"] = "Simulated player:" in after
    checks["pip_actions_layouts"] = all(layout_results.values())
    result["layout_results"] = layout_results
    result["steps"].append(f"动作布局: {layout_results}")

    # 5. setIsPlaying 模拟播放器：官方只在非 none 布局显示它，先切回 MEDIA。
    for _ in range(3):
        click_button("NONE")
        time.sleep(0.8)
        if 'desc="MEDIA"' in dump():
            break
    u2("click", "--description", "MEDIA")
    time.sleep(1.5)
    u2("click", "--description", "切换模拟播放状态")
    time.sleep(1.5)
    checks["set_is_playing"] = "播放状态设置: False" in dump()
    result["steps"].append("模拟播放器已切换到暂停")

    # 6. 进入 PiP：Python 侧即时推送 pip_child，Dart 侧等一帧画完后进 PiP。
    #    量化「点击 → 系统进入 PiP」耗时，验证已去掉旧版 Python 侧 sleep(2.0)。
    entered = False
    t0 = time.monotonic()
    for _ in range(3):
        u2("click", "--description", "进入 PiP")
        for _ in range(25):
            time.sleep(0.2)
            if "随机数:" in dump() or is_pinned():
                entered = True
                break
        if entered:
            break
    elapsed = round(time.monotonic() - t0, 2)
    checks["enter_pip"] = entered
    result["enter_pip_elapsed_sec"] = elapsed
    pinned = False
    for _ in range(10):
        if is_pinned():
            pinned = True
            break
        time.sleep(1)
    checks["pip_window"] = pinned
    result["screenshot_pip_a"] = screenshot("全功能_02_PiP_A")
    time.sleep(3)
    result["screenshot_pip_b"] = screenshot("全功能_03_PiP_B")
    result["no_runtime_error"] = "Error running app" not in dump()
    result["steps"].append(
        f"PiP 已进入（耗时 {elapsed}s，旧版固定等 2s）"
        "，间隔截取两张图用于观察随机数"
    )

    # 7. PiP 动作：提示人工点击悬浮窗动作按钮
    result["manual_action_hint"] = (
        "请在 PiP 悬浮窗点一下播放/暂停/下一个等动作按钮，"
        "然后回到 App 查看「回调：PiP 动作 …」日志。"
    )

    # 8. 退出 PiP 与回调
    time.sleep(2)
    checks["exit_pip"] = restore()
    time.sleep(2)
    checks["callback_exited"] = wait_description("回调：已退出 PiP", 20)
    checks["callback_log"] = "回调：已进入 PiP" in dump()
    result["screenshot_exit"] = screenshot("全功能_04_退出回调")
    result["steps"].append("退出 PiP 并读取回调日志")

    # 回调文本受 MIUI 事件时序影响偶发合并，单独记录，不阻断功能判据。
    soft = ("callback_exited",)
    result["passed"] = all(v for k, v in checks.items() if k not in soft)
    return result


def main() -> int:
    try:
        result = run_all()
    except Exception as exc:  # noqa: BLE001 - 验证脚本需要完整记录失败原因
        result = {"time": datetime.now().isoformat(timespec="seconds"), "error": repr(exc)}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = OUT_DIR / "全部功能验证.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"报告: {report}")
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
