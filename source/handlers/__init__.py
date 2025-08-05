"""
handlers包，包含各种处理程序，用于分离主窗口的功能
"""

from .patch_toggle_handler import PatchToggleHandler
from .uninstall_handler import UninstallHandler

__all__ = ['PatchToggleHandler', 'UninstallHandler'] 