"""测试全局配置：使 source/ 下的模块可被导入，并让 Qt 在无显示环境运行。"""

import os
import sys
from pathlib import Path

# source/ 不是 Python 包，其内部模块以 `from config.config import ...` 形式互相引用。
# 把 source/ 插入 sys.path 使这些 import 在测试中同样成立，避免改动现有源码。
SOURCE_DIR = Path(__file__).resolve().parent.parent / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

# Qt 测试在无显示环境（CI、SSH）下运行需要 offscreen 平台插件。
# 必须在任何 PySide6 模块被导入之前设置。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
