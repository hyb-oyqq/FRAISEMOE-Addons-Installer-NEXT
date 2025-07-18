import os
import sys
from PySide6 import QtWidgets
from data.config import LOG_FILE
from utils import Logger

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
    
    def toggle_debug_mode(self, checked):
        """切换调试模式
        
        Args:
            checked: 是否启用调试模式
        """
        self.main_window.config["debug_mode"] = checked
        self.main_window.save_config(self.main_window.config)
        if checked:
            self.start_logging()
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
                print("--- Debug mode enabled ---")
            except (IOError, OSError) as e:
                QtWidgets.QMessageBox.critical(self.main_window, "错误", f"无法创建日志文件: {e}")
                self.logger = None

    def stop_logging(self):
        """停止日志记录"""
        if self.logger:
            print("--- Debug mode disabled ---")
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.logger.close()
            self.logger = None 