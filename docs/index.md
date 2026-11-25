# Introduction

flet-simple-pip-mode 把 Flutter 的 `simple_pip_mode` 插件封装成 Flet 用户扩展，提供：

- `SimplePipMode`：PiP 服务（进入、自动进入、动作布局、进入/退出/动作回调）
- `PipWidget`：按 PiP 状态切换 `child` / `pip_child` 的布局控件

完整安装、Android 原生配置、API 与真机验证说明见项目根目录 [README.md](../README.md)。

## Minimal example

```python
import flet as ft

from flet_simple_pip_mode import PipWidget, SimplePipMode


def main(page: ft.Page):
    pip = SimplePipMode()

    async def enter_pip():
        await pip.enter_pip_mode(aspect_ratio=(16, 9))

    page.add(
        ft.Button(content="进入 PiP", on_click=lambda: page.run_task(enter_pip)),
        PipWidget(
            child=ft.Text("普通界面"),
            pip_child=ft.Text("画中画界面"),
        ),
    )


ft.run(main)
```

注意：Android 上还需给生成的工程打原生补丁，见 README 的「Android 原生配置」章节。
