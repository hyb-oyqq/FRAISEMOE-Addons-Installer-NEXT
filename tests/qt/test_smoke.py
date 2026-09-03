# tests/qt/test_smoke.py
"""Qt 测试基础设施冒烟验证。

本轮只证明 QApplication 可创建、信号可被 qtbot 捕获。
线程生命周期与窗口状态机的测试留到子项目 3。
"""

from PySide6.QtCore import QObject, Signal


class _Emitter(QObject):
    fired = Signal(str)


def test_qapplication_is_available(qapp):
    assert qapp is not None


def test_qtbot_captures_signal(qtbot):
    emitter = _Emitter()
    with qtbot.waitSignal(emitter.fired, timeout=1000) as blocker:
        emitter.fired.emit("hello")
    assert blocker.args == ["hello"]


def test_offscreen_platform_is_active():
    import os

    assert os.environ["QT_QPA_PLATFORM"] == "offscreen"
