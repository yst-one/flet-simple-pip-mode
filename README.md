# flet-simple-pip-mode

把 [simple_pip_mode](https://pub.dev/packages/simple_pip_mode)（Android 画中画插件）封装成 Flet 用户扩展。

- Python 侧：`SimplePipMode` 服务（异步方法 + 回调事件）、`PipWidget` 控件（按 PiP 状态切换内容）
- Flutter 侧：单例 `PipController` 统一接管插件的固定 MethodChannel，服务和控件共享状态
- 版本基线：Flet **1.1.3**、simple_pip_mode **2.0.0**（要求 Android SDK **37**，JDK 17）
- 原生配置脚本同时兼容 Flet 0.86 的 `FlutterActivity` 和 Flet 1.1.x 的 `FlutterFragmentActivity` 模板
- 示例 App 已按 [官方 example](https://github.com/PuntitOwO/simple_pip_mode_flutter/tree/main/example) 一一对应实现，覆盖其全部 API 演示点

## 平台支持

| 平台 | Android | iOS | Web | Windows | macOS | Linux |
|------|---------|-----|-----|---------|-------|-------|
| PiP 功能 | ✅（API 26+） | ❌ | ❌ | ❌ | ❌ | ❌ |

非 Android 平台上方法安全降级返回 `False`，`PipWidget` 始终显示 `child`，不会抛异常。

## 目录结构

```
src/
├── flet_simple_pip_mode/           # Python 包
│   ├── __init__.py                 # 对外 API
│   ├── pip_service.py              # SimplePipMode 服务、枚举、事件
│   ├── pip_widget.py               # PipWidget 控件
│   └── patch_android.py            # Android 原生配置补丁（幂等）
└── flutter/flet_simple_pip_mode/   # Flutter 扩展包
    ├── pubspec.yaml
    └── lib/
        ├── flet_simple_pip_mode.dart
        └── src/
            ├── extension.dart      # createWidget + createService 注册
            ├── pip_controller.dart # 单例 PiP 状态中心
            ├── pip_service.dart    # FletService 实现
            └── pip_widget.dart     # LayoutControl 包装
examples/flet_simple_pip_mode_example/
├── pyproject.toml                  # 示例 App（path dependency）
├── src/main.py                     # 声明式示例 UI
└── u2_scripts/                     # 真机验证脚本
```

## 快速开始

### 1. 添加依赖

在 App 的 `pyproject.toml` 中（本地路径 / Git / PyPI 三选一）：

```toml
[project]
dependencies = [
  "flet-simple-pip-mode @ file:///D:/auto_phone/flet_pip_ex",
  "flet>=1.1.3",
]
```

### 2. 写 UI

```python
import asyncio
import flet as ft
from flet_simple_pip_mode import PipWidget, SimplePipMode

@ft.component
def App(page: ft.Page, pip: SimplePipMode, hub: StatusHub):
    in_pip, set_in_pip = ft.use_state(hub.in_pip)

    async def enter_pip():
        # 先切到 pip_child 并立即推送；扩展会在内部等一帧画完后才进 PiP，
        # 无需在 Python 侧 sleep。系统截取的首帧就是 pip_child。
        hub.set_pip(True, "切换内容：画中画布局")
        page.update()
        await pip.enter_pip_mode(aspect_ratio=(16, 9))

    def on_enter():
        # Flet 1.1.x：run_task 传协程函数，不要传协程对象；事件处理器不收参数。
        page.run_task(enter_pip)

    pip_view = PipWidget(
        active=in_pip,
        child=ft.Container(
            expand=True,
            bgcolor=ft.Colors.PURPLE_200,
            content=ft.Text("普通界面"),
        ),
        # 画中画里显示什么完全由 pip_child 决定，可以是任意 Flet 控件。
        pip_child=ft.Container(
            expand=True,
            bgcolor=ft.Colors.GREEN_300,
            content=ft.Text("画中画界面"),
        ),
    )

    # PiP 期间只保留 pip_child，避免系统把旧表头 / 按钮截图当成画中画内容。
    if in_pip:
        return ft.SafeArea(expand=True, content=pip_view)

    return ft.Column(controls=[ft.Button(content="进入 PiP", on_click=on_enter), pip_view])

def main(page: ft.Page):
    hub = StatusHub()
    pip = SimplePipMode(
        on_pip_entered=lambda e: hub.set_pip(True, "回调：已进入 PiP"),
        on_pip_exited=lambda e: hub.set_pip(False, "回调：已退出 PiP"),
    )
    page.render(lambda: App(page, pip, hub))

ft.run(main)
```

服务回调示例：

```python
pip = SimplePipMode(
    on_pip_entered=lambda e: print("进入 PiP"),
    on_pip_exited=lambda e: print("退出 PiP"),
    on_pip_action=lambda e: print("动作：", e.action.value),
)
```

回调发生在 PiP 窗口里时，回到全屏后只靠 `print` / 单行状态是看不到的。推荐像示例
`src/main.py` 那样把回调写进**独立的多行记录区**（`StatusHub.logs` + `ft.Text("\n".join(logs))`），
事件按时间倒序保留最近 10 条，返回 App 后可直接查看：

```python
class StatusHub:
    def set(self, value: str) -> None:
        self.value = value
        self.logs = [value] + self.logs[:9]   # 最新在最上面
        self._notify()

    def set_pip(self, active: bool, value: str | None = None) -> None:
        self.in_pip = active                 # 驱动 PipWidget.active
        if value is not None:
            self.set(value)
        else:
            self._notify()
```

`on_pip_entered` / `on_pip_exited` 接到 `hub.set_pip(True/False, "回调：...")`；状态行显示最新一条，
事件记录区显示完整历史。

### 3. Android 原生配置（关键）

simple_pip_mode 需要在宿主 App 的 Android 工程里做两件事，Flet CLI 没有对应选项：

1. `<activity>` 添加 `android:supportsPictureInPicture="true"`
2. `MainActivity` 接入 PiP 回调（否则收不到进入/退出回调）：
   - Flet 0.86 模板（`FlutterActivity`）→ 继承 `PipCallbackHelperActivityWrapper()`
   - Flet 1.1.x 模板（`FlutterFragmentActivity`）→ 注入 `PipCallbackHelper` 覆写

扩展提供幂等补丁脚本，自动识别上面两种模板，首次 `flet build` 之后运行，再构建一次即可：

```bash
cd examples/flet_simple_pip_mode_example
uv run flet build apk --arch arm64-v8a          # 首次构建，生成 build/flutter
uv run python -m flet_simple_pip_mode.patch_android build/flutter
uv run flet build apk --arch arm64-v8a          # 带原生配置的最终构建
```

脚本输出 `patched: ...` 表示改动已写入；重复运行会提示 `already patched`。
升级 Flet 或 `flet clean` 后需要重新打补丁。

### 4. 安装到真机

```bash
u2cli app-install build/apk/flet-simple-pip-mode-example.apk
u2cli app-start com.mycompany.flet_simple_pip_mode_example
```

## API

### `SimplePipMode`（服务）

| 方法 | 返回 | 说明 |
|------|------|------|
| `is_pip_available()` | `bool` | 设备是否支持 PiP（API 26+） |
| `is_auto_pip_available()` | `bool` | 是否支持自动进入（API 31+） |
| `is_pip_activated()` | `bool` | 当前是否处于 PiP |
| `enter_pip_mode(aspect_ratio=(16,9), auto_enter=False, seamless_resize=False)` | `bool` | 请求进入 PiP |
| `set_auto_pip_mode(aspect_ratio=(16,9), seamless_resize=False, auto_enter=True)` | `bool` | 离开 App 时自动进入 PiP |
| `set_pip_actions_layout(layout)` | `bool` | 设置 PiP 动作布局 |
| `set_is_playing(is_playing)` | `bool` | 更新播放/暂停图标 |

事件：`on_pip_entered`、`on_pip_exited`、`on_pip_action`（`PipActionEvent.action` 为 `PipAction` 枚举）。

### 枚举

| 枚举 | 值 |
|------|----|
| `PipAction` | `PLAY/PAUSE/PREVIOUS/NEXT/LIVE/REWIND/FORWARD` |
| `PipActionsLayout` | `NONE/MEDIA/MEDIA_ONLY_PAUSE/MEDIA_LIVE/MEDIA_WITH_SEEK_10` |

### `PipWidget`（LayoutControl）

| 属性 | 说明 |
|------|------|
| `active` | `True` 时显示 `pip_child`，`False` 时显示 `child`；由 PiP 回调或调用方驱动 |
| `child` | 非 PiP 状态显示的内容 |
| `pip_child` | PiP 状态显示的内容，缺省时复用 `child`（可放任意 Flet 控件） |

继承 Flet `LayoutControl` 的 `width/height/opacity/tooltip` 等布局属性。

**内容切换时序（重要）**：Android 在进入 PiP 时会截取当前页面，进入后的切换会截到旧画面。
所以要在调用 `enter_pip_mode()` **之前**把 `PipWidget.active` 设为 `True` 并 `page.update()`
立即推送；扩展内部会用 `addPostFrameCallback` 等 `pip_child` 画完一帧后再请求系统 PiP，
无需在 Python 侧 `sleep`。同时把 PiP 期间的页面收敛为只显示 `pip_child`；
退出回调再把 `active` 置回 `False`。这样悬浮窗里就是指定的内容，而不是旧表头。

## 官方 example 功能对齐

示例 `examples/flet_simple_pip_mode_example/src/main.py` 与
[官方 Flutter example](https://github.com/PuntitOwO/simple_pip_mode_flutter/tree/main/example) 一一对应：

| 官方 example 功能 | Flet 实现 | 验证脚本检查项 |
|-------------------|-----------|----------------|
| `SimplePip.isPipAvailable` | `await pip.is_pip_available()` | `PiP Available: ✅` |
| `SimplePip.isAutoPipAvailable` | `await pip.is_auto_pip_available()` | Auto Enter 开关可用 |
| `SimplePip.isPipActivated` | `await pip.is_pip_activated()` | 初始 `PiP Activated: ❌` |
| 宽高比预设 `(1,1)/(2,3)/(3,2)/(16,9)/(9,16)` | `ASPECT_RATIOS` 下拉 + `enter_pip_mode(aspect_ratio=...)` | 5 个选项可见 |
| `pip.setAutoPipMode(...)` | `await pip.set_auto_pip_mode(...)` | 下拉/开关触发后日志 |
| `pip.enterPipMode(...)` | `await pip.enter_pip_mode(...)` | Activity `mode=pinned` |
| `PipActionsLayout` 5 种布局 | `await pip.set_pip_actions_layout(...)` | 5 种布局切换日志 |
| `pip.setIsPlaying(...)` | `await pip.set_is_playing(...)` | 模拟播放器按钮 |
| `PipWidget(child/pipChild)` | `PipWidget(child/pip_child, active=...)` | PiP 内外两套内容 |
| `onPipEntered/onPipExited` | `on_pip_entered/on_pip_exited` 事件 | 多行回调记录区 |
| `onPipAction`（7 种动作） | `on_pip_action` 事件 + `PipActionEvent.action` | 点悬浮窗动作后看日志 |

示例的**布局也按官方对齐**：AppBar 标题 + body 整体居中（状态用 check/close Icon、
Divider、PIP Actions 区块、仅在非 none 布局显示 Simulated player），
`pip_child` 是独立的 "Pip Mode" 居中屏。回调日志与随机数收敛到底部小字，
不破坏居中观感。另外加了持续刷新的随机数，用来肉眼确认 PiP 窗口是实时重绘而非静态截图。

## 真机验证

两个脚本（uiautomator2 / u2cli，真机 Redmi，Android 17，Flet 1.1.3 + simple_pip_mode 2.0.0）：

- `u2_scripts/验证画中画.py`：基础流程（进入/退出/内容切换/截图），结果 `验证结果.json`
- `u2_scripts/验证全部功能.py`：对照官方 example 的 8 类功能逐项检查，结果 `全部功能验证.json`

`验证全部功能.py` 最近一次实测 **19 项检查全部通过**（`passed: true`）：能力检测、5 种宽高比、
Auto Enter 开关、5 种动作布局（含 none 下隐藏播放器 / 非 none 下显示）、`set_is_playing`、
进入 PiP 且 `mode=pinned`、PiP 内自定义内容与随机数、退出与回调日志。
截图见 `验证结果/全功能_01~04*.png`。

**关于 7 种 PiP 动作按钮**：动作回调链路已在代码层打通（Dart `onPipAction` → `pip_action`
事件 → Python `PipActionEvent`），并修复了 Dart `action.name` 大写与 Python 枚举 value
小写不匹配导致 `ValueError` 的问题（现在 Dart 发小写，Python `PipAction._missing_`
也兼容大写）。但实测 **MIUI 的 PiP 悬浮窗不渲染 simple_pip_mode 的 RemoteAction
动作按钮**（点击/上滑/双击均不展开系统动作栏），这是 ROM 限制，非扩展缺陷。
在原生 Android / 其他 ROM 上动作按钮出现时，回调会写入「回调：PiP 动作 xxx →
Playing/Paused/Next/...」日志；如你的设备也不显示，可用 App 内 Simulated player
按钮验证 `set_is_playing` 与 PiP 内图标的双向同步。

运行方式：

```bash
cd examples/flet_simple_pip_mode_example/u2_scripts
python 验证画中画.py       # 基础
python 验证全部功能.py     # 全功能对照
```

## 常见问题

- **按钮点了没反应 / `handler must be a coroutine function`**：Flet 1.1.x 的
  `page.run_task()` 只接收**协程函数**（写 `page.run_task(my_async_fn)`，不要写
  `my_async_fn()`，更不要包 `lambda: my_async_fn()`）。事件处理器本身声明成
  `async def` 后可直接 `await` 异步方法——`_trigger_event` 会自动 await 返回的协程。
- **事件回调报 `tuple index out of range`**：事件字段必须用**具名 Event dataclass**
  （如 `PipStateEvent`），且定义文件**不能**有 `from __future__ import annotations`——
  Flet 1.1.3 的事件解析器不处理字符串化注解。Dart 侧 `triggerEvent` 必须带非空 map payload。
- **`flet run` 显示未知控件**：扩展需编译进客户端，请用 `flet build` / `flet debug`，不要直接用预构建客户端运行。
- **`platforms;android-37.0` 找不到**：simple_pip_mode 2.0.0 用 API 37 编译，执行
  `sdkmanager "platforms;android-37.0"` 后重建（Flet 只会自动装到 API 35/36，注意包名带 `.0`）。
- **Kotlin 编译报 `onPictureInPictureModeChanged overrides nothing`**：`newConfig` 必须是
  非空 `Configuration`；补丁脚本已适配，重新运行即可。
- **`Error running app: name 'x' is not defined`**：Flet 1.1.x 声明式组件里每个 UI 用到的
  状态都要有对应的 `x, set_x = ft.use_state(...)`，并在 hub 通知回调里 `set_x(...)`；
  漏声明的变量只在 rendering 时才暴露（编译期发现不了）。
- **下拉框点不到**：a11y 层级里 Flet Dropdown 的可点节点是 `android.widget.Button`
  的 text（如 `16:9` / `MEDIA`），label 只是 desc；u2 需解析按钮坐标点击，选项用 desc 选。
- **非 Android 报错**：所有平台方法都做了异常降级，但 PiP 本身只有 Android 支持。
