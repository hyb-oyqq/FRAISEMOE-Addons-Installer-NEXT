# FRAISEMOE Addons Installer NEXT - 项目结构

## 目录结构

```
source/
├── assets/                  # 所有静态资源文件
│   ├── fonts/              # 字体文件
│   ├── images/             # 图片资源
│   └── resources/          # 其他资源文件
├── bin/                    # 二进制工具文件
├── config/                 # 配置文件
├── core/                   # 核心功能模块
│   ├── managers/           # 所有管理器类
│   └── handlers/           # 处理器类
├── data/                   # 数据文件
├── ui/                     # 用户界面相关
│   ├── components/         # UI组件
│   ├── windows/            # 窗口定义
│   └── views/              # 视图定义
├── utils/                  # 工具类和辅助函数
├── workers/                # 后台工作线程
└── main.py                 # 主入口文件
```

## 文件路径映射

| 重构前 | 重构后 |
| ------ | ------ |
| source/Main.py | source/main.py |
| source/fonts/* | source/assets/fonts/* |
| source/IMG/* | source/assets/images/* |
| source/resources/* | source/assets/resources/* |
| source/data/config.py | source/config/config.py |
| source/data/privacy_policy.py | source/config/privacy_policy.py |
| source/core/animations.py | source/core/managers/animations.py |
| source/core/cloudflare_optimizer.py | source/core/managers/cloudflare_optimizer.py |
| source/core/config_manager.py | source/core/managers/config_manager.py |
| source/core/debug_manager.py | source/core/managers/debug_manager.py |
| source/core/download_manager.py | source/core/managers/download_manager.py |
| source/core/download_task_manager.py | source/core/managers/download_task_manager.py |
| source/core/extraction_handler.py | source/core/handlers/extraction_handler.py |
| source/core/game_detector.py | source/core/managers/game_detector.py |
| source/core/ipv6_manager.py | source/core/managers/ipv6_manager.py |
| source/core/offline_mode_manager.py | source/core/managers/offline_mode_manager.py |
| source/core/patch_detector.py | source/core/managers/patch_detector.py |
| source/core/patch_manager.py | source/core/managers/patch_manager.py |
| source/core/privacy_manager.py | source/core/managers/privacy_manager.py |
| source/core/ui_manager.py | source/core/managers/ui_manager.py |
| source/core/window_manager.py | source/core/managers/window_manager.py |
| source/handlers/* | source/core/handlers/* |

## 模块职责划分

1. **managers**: 负责管理应用程序的各个方面，如配置、下载、游戏检测等。
2. **handlers**: 负责处理特定的操作，如提取文件、打补丁、卸载等。
3. **assets**: 存储应用程序使用的静态资源。
4. **config**: 存储应用程序的配置信息。
5. **ui**: 负责用户界面相关的组件和视图。
6. **utils**: 提供各种实用工具函数。
7. **workers**: 负责在后台执行耗时操作的线程。

这种结构更加清晰地区分了各个模块的职责，使代码更容易维护和扩展。 