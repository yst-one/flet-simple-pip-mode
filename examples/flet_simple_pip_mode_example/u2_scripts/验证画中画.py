"""用 uiautomator2 真机验证 flet-simple-pip-mode 扩展。

运行前：
  - 真机已连接（u2cli device-info 可返回设备信息）
  - 已安装 APK（见 README 构建/安装步骤）

运行：
  python 验证画中画.py

脚本会恢复起始界面、点击「进入 PiP」、检查系统 PiP 窗口状态与退出回调，
并把截图与结果 JSON 保存到 验证结果/ 目录。
"""

from __future__ import annotations

import json
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
    cmd = ["u2cli", *args]
    result = subprocess.run(
        cmd,
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
        out = u2("wait", "--description", text, "--timeout", str(seconds))
        return "result: True" in out
    except RuntimeError:
        return False


def is_pinned() -> bool:
    return "mode=pin" in u2("shell", "dumpsys activity activities | grep mode=pin")


def check_baseline() -> bool:
    """恢复起始界面并验证。"""
    u2("app-stop", PACKAGE)
    u2("app-start", PACKAGE)
    return wait_description("Flet × simple_pip_mode")


def run_once() -> dict:
    result: dict = {"time": datetime.now().isoformat(timespec="seconds"), "steps": []}

    if not check_baseline():
        result["error"] = "起始界面未出现 Flet × simple_pip_mode 标题"
        return result
    result["steps"].append("起始界面已验证")
    result["screenshot_start"] = screenshot("01_起始界面")
    result["normal_card_visible"] = "普通模式" in dump()
    result["service_ready"] = "PiP 支持: True" in dump()

    # 等按钮完全可交互后再点击；MIUI 首次点击偶发被吞，循环到状态切换为止
    time.sleep(2)
    for attempt in range(1, 4):
        u2("click", "--description", "进入 PiP")
        time.sleep(1)
        if "自定义 PiP 内容" in dump():
            result["steps"].append(f"点击「进入 PiP」生效（第 {attempt} 次）")
            break
    result["content_swapped"] = "自定义 PiP 内容" in dump()

    pinned = False
    for _ in range(8):
        time.sleep(1)
        if is_pinned():
            pinned = True
            break
    result["pip_window_visible"] = pinned
    result["screenshot_pip"] = screenshot("02_画中画")

    # 等 PiP 进入动画与回调完成后再恢复，避免回调被系统合并丢失
    time.sleep(3)
    u2("shell", f"am start -n {ACTIVITY}")
    result["callback_exited"] = wait_description("回调：已退出 PiP", 20)
    result["steps"].append(
        "退出回调：" + ("已捕获" if result["callback_exited"] else "本次未捕获（MIUI 可能合并 PiP 事件）")
    )
    result["screenshot_exit"] = screenshot("03_退出回调")
    result["no_runtime_error"] = "Error running app" not in dump()
    result["callback_log_visible"] = "回调：已退出 PiP\n回调：已进入 PiP" in dump()
    result["steps"].append("回调记录区：" + ("多行可见" if result["callback_log_visible"] else "未捕获完整历史"))

    # 核心判据：服务可用、内容切换、PiP 窗口、回调历史、UI 无错误。
    result["passed"] = bool(
        result["normal_card_visible"]
        and result["service_ready"]
        and result["content_swapped"]
        and result["pip_window_visible"]
        and result["callback_log_visible"]
        and result["no_runtime_error"]
    )
    return result


def main() -> int:
    try:
        result = run_once()
    except Exception as exc:  # noqa: BLE001 - 验证脚本需要完整记录失败原因
        result = {"time": datetime.now().isoformat(timespec="seconds"), "error": repr(exc)}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = OUT_DIR / "验证结果.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"报告: {report}")
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
