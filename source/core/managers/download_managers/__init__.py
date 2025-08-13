"""
下载管理器模块
包含下载相关的管理器类
"""

from .download_manager import DownloadManager
from .download_task_manager import DownloadTaskManager

__all__ = [
    'DownloadManager',
    'DownloadTaskManager',
]