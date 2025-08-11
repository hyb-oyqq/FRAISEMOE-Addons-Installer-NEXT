# Managers package initialization
from .ui_manager import UIManager
from .download_manager import DownloadManager
from .debug_manager import DebugManager
from .window_manager import WindowManager
from .game_detector import GameDetector
from .patch_manager import PatchManager
from .config_manager import ConfigManager
from .privacy_manager import PrivacyManager
from .cloudflare_optimizer import CloudflareOptimizer
from .download_task_manager import DownloadTaskManager
from .patch_detector import PatchDetector
from .animations import MultiStageAnimations

__all__ = [
    'UIManager',
    'DownloadManager',
    'DebugManager',
    'WindowManager',
    'GameDetector',
    'PatchManager',
    'ConfigManager',
    'PrivacyManager',
    'CloudflareOptimizer',
    'DownloadTaskManager',
    'PatchDetector',
    'MultiStageAnimations',
] 