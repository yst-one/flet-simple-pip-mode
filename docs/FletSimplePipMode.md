# API 参考

## SimplePipMode

Android 画中画服务。实例化后自动注册到当前 page。

### 方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `is_pip_available()` | `bool` | 设备是否支持 PiP（API 26+） |
| `is_auto_pip_available()` | `bool` | 是否支持自动进入（API 31+） |
| `is_pip_activated()` | `bool` | 当前是否处于 PiP |
| `enter_pip_mode(aspect_ratio=(16,9), auto_enter=False, seamless_resize=False)` | `bool` | 请求进入 PiP |
| `set_auto_pip_mode(aspect_ratio=(16,9), seamless_resize=False, auto_enter=True)` | `bool` | 离开 App 时自动进入 |
| `set_pip_actions_layout(layout)` | `bool` | 设置 PiP 动作布局 |
| `set_is_playing(is_playing)` | `bool` | 更新播放/暂停图标 |

### 事件

| 字段 | 事件类型 | 说明 |
|------|----------|------|
| `on_pip_entered` | `PipStateEvent` | 进入 PiP，`active=True` |
| `on_pip_exited` | `PipStateEvent` | 退出 PiP，`active=False` |
| `on_pip_action` | `PipActionEvent` | PiP 动作按钮，`action` 为 `PipAction` 枚举 |

## PipWidget

继承 `ft.LayoutControl`，按 `active` 属性切换内容。

| 属性 | 说明 |
|------|------|
| `active` | `True` 显示 `pip_child`，`False` 显示 `child`；由回调或调用方驱动 |
| `child` | 非 PiP 状态内容 |
| `pip_child` | PiP 状态内容，缺省时复用 `child`，可放任意 Flet 控件 |

进入 PiP 前先把 `active` 设为 `True` 并 `page.update()` 立即推送；扩展内部会等
`pip_child` 画完一帧后再请求系统 PiP，无需 Python 侧 `sleep`。同时让 PiP 期间的
页面只显示 `pip_child`，否则系统会截取切换前的旧画面。
回调建议写进多行记录区（`ExampleHub.logs`），返回 App 后仍能看到完整事件历史。

## 官方 example 对照

示例 `src/main.py` 是官方 Flutter example 的完整 Flet 移植，API 一一对应：

```python
# 官方: SimplePip.isPipAvailable / isAutoPipAvailable / isPipActivated
await pip.is_pip_available()
await pip.is_auto_pip_available()
await pip.is_pip_activated()

# 官方: pip.enterPipMode(aspectRatio: ..., autoEnter: ..., seamlessResize: ...)
await pip.enter_pip_mode(aspect_ratio=(2, 3), auto_enter=True, seamless_resize=True)

# 官方: pip.setAutoPipMode(...) —— 宽高比下拉 / Auto Enter 开关都走这里
await pip.set_auto_pip_mode(aspect_ratio=(9, 16), auto_enter=True, seamless_resize=True)

# 官方: pip.setPipActionsLayout(...) / pip.setIsPlaying(...)
await pip.set_pip_actions_layout(PipActionsLayout.MEDIA_LIVE)
await pip.set_is_playing(False)

# 官方: PipWidget(pipLayout: ..., onPipAction: ..., child: ..., pipChild: ...)
pip = SimplePipMode(
    on_pip_action=lambda e: hub.set_action(e.action),  # e.action 为 PipAction 枚举
)
PipWidget(active=in_pip, child=普通布局, pip_child=画中画布局)
```

动作响应文案与官方一致：`play → Playing`、`pause → Paused`、`live → Go to live view`、
`next → Next`、`previous → Previous`、`rewind → Rewind`、`forward → Forward`。

Dart 侧发送的动作名会转成小写再交给 Python（`PipAction` value 为小写）；
`PipAction._missing_` 同时兼容大写，避免枚举反序列化报 `ValueError`。
注意：MIUI 的 PiP 悬浮窗实测不渲染 simple_pip_mode 的 RemoteAction 动作按钮，
动作栏能否显示取决于 ROM；回调链路本身已打通。

## 枚举

`PipAction`：`PLAY / PAUSE / PREVIOUS / NEXT / LIVE / REWIND / FORWARD`

`PipActionsLayout`：`NONE / MEDIA / MEDIA_ONLY_PAUSE / MEDIA_LIVE / MEDIA_WITH_SEEK_10`
