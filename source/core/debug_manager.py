import os
import sys
from PySide6 import QtWidgets
from data.config import LOG_FILE
from utils.logger import setup_logger
from utils import Logger

# 初始化logger
logger = setup_logger("debug_manager")

class DebugManager:
    def __init__(self, main_window):
        """初始化调试管理器
        
        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        self.logger = None
        self.original_stdout = None
        self.original_stderr = None
        self.ui_manager = None  # 添加ui_manager属性
    
    def set_ui_manager(self, ui_manager):
        """设置UI管理器引用
        
        Args:
            ui_manager: UI管理器实例
        """
        self.ui_manager = ui_manager
    
    def _is_debug_mode(self):
        """检查是否处于调试模式
        
        Returns:
            bool: 是否处于调试模式
        """
        try:
            # 首先尝试从UI管理器获取状态
            if hasattr(self, 'ui_manager') and self.ui_manager and hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action:
                return self.ui_manager.debug_action.isChecked()
            
            # 如果UI管理器还没准备好，尝试从配置中获取
            if hasattr(self.main_window, 'config') and isinstance(self.main_window.config, dict):
                return self.main_window.config.get('debug_mode', False)
                
            # 如果以上都不可行，返回False
            return False
        except Exception:
            # 捕获任何异常，默认返回False
            return False
    
    def toggle_debug_mode(self, checked):
        """切换调试模式
        
        Args:
            checked: 是否启用调试模式
        """
        logger.info(f"Toggle debug mode: {checked}")
        self.main_window.config["debug_mode"] = checked
        self.main_window.save_config(self.main_window.config)
        
        # 更新打开log文件按钮状态
        if hasattr(self, 'ui_manager') and hasattr(self.ui_manager, 'open_log_action'):
            self.ui_manager.open_log_action.setEnabled(checked)
            
        if checked:
            self.start_logging()
            
            # 如果启用了调试模式，检查是否需要强制启用离线模式
            if hasattr(self.main_window, 'offline_mode_manager'):
                # 检查配置中是否已设置离线模式
                offline_mode_enabled = self.main_window.config.get("offline_mode", False)
                
                # 如果配置中已设置离线模式，则在调试模式下强制启用
                if offline_mode_enabled:
                    logger.debug("DEBUG: 调试模式下强制启用离线模式")
                    self.main_window.offline_mode_manager.set_offline_mode(True)
                    
                    # 更新UI中的离线模式选项
                    if hasattr(self.ui_manager, 'offline_mode_action') and self.ui_manager.offline_mode_action:
                        self.ui_manager.offline_mode_action.setChecked(True)
                        self.ui_manager.online_mode_action.setChecked(False)
        else:
            self.stop_logging()

    def start_logging(self):
        """启动日志记录"""
        if self.logger is None:
            try:
                if os.path.exists(LOG_FILE):
                    os.remove(LOG_FILE)
                # 保存原始的 stdout 和 stderr
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr
                # 创建 Logger 实例
                self.logger = Logger(LOG_FILE, self.original_stdout)
                sys.stdout = self.logger
                sys.stderr = self.logger
                logger.info("--- Debug mode enabled ---")
            except (IOError, OSError) as e:
                QtWidgets.QMessageBox.critical(self.main_window, "错误", f"无法创建日志文件: {e}")
                self.logger = None

    def stop_logging(self):
        """停止日志记录"""
        if self.logger:
            logger.info("--- Debug mode disabled ---")
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.logger.close()
            self.logger = None 