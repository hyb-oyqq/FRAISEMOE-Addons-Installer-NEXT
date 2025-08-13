import os
import sys
from PySide6 import QtWidgets
from config.config import LOG_FILE
from utils.logger import setup_logger
from utils import Logger
import datetime
from config.config import APP_NAME

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
        
        # 创建或删除debug_mode.txt标记文件
        try:
            from config.config import CACHE
            debug_file = os.path.join(os.path.dirname(CACHE), "debug_mode.txt")
            
            if checked:
                # 确保目录存在
                os.makedirs(os.path.dirname(debug_file), exist_ok=True)
                # 创建标记文件
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"Debug mode enabled at {os.path.abspath(debug_file)}\n")
                logger.info(f"已创建调试模式标记文件: {debug_file}")
            elif os.path.exists(debug_file):
                # 删除标记文件
                os.remove(debug_file)
                logger.debug(f"已删除调试模式标记文件: {debug_file}")
        except Exception as e:
            logger.warning(f"处理调试模式标记文件时发生错误: {e}")
        
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
                # 确保log目录存在
                log_dir = os.path.dirname(LOG_FILE)
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                    logger.debug(f"已创建日志目录: {log_dir}")
                
                # 创建新的日志文件，使用覆盖模式而不是追加模式
                with open(LOG_FILE, 'w', encoding='utf-8') as f:
                    current_time = datetime.datetime.now()
                    formatted_date = current_time.strftime("%Y-%m-%d")
                    formatted_time = current_time.strftime("%H:%M:%S")
                    f.write(f"--- 新调试会话开始于 {os.path.basename(LOG_FILE)} ---\n")
                    f.write(f"--- 应用版本: {APP_NAME} ---\n")
                    f.write(f"--- 日期: {formatted_date} 时间: {formatted_time} ---\n\n")
                    logger.debug(f"已创建日志文件: {os.path.abspath(LOG_FILE)}")
                
                # 保存原始的 stdout 并创建Logger实例
                self.original_stdout = sys.stdout
                self.logger = Logger(LOG_FILE, self.original_stdout)
                
                logger.debug(f"--- Debug mode enabled (log file: {os.path.abspath(LOG_FILE)}) ---")
            except (IOError, OSError) as e:
                QtWidgets.QMessageBox.critical(self.main_window, "错误", f"无法创建日志文件: {e}")
                self.logger = None

    def stop_logging(self):
        """停止日志记录"""
        if self.logger:
            logger.debug("--- Debug mode disabled ---")
            # 恢复stdout到原始状态
            if hasattr(self, 'original_stdout') and self.original_stdout:
                sys.stdout = self.original_stdout
            # 关闭日志文件
            if hasattr(self.logger, 'close'):
                self.logger.close()
            self.logger = None

    def open_log_file(self):
        """打开当前日志文件"""
        try:
            # 检查日志文件是否存在
            if os.path.exists(LOG_FILE):
                # 获取日志文件大小
                file_size = os.path.getsize(LOG_FILE)
                if file_size == 0:
                    from utils import msgbox_frame
                    msg_box = msgbox_frame(
                        f"提示 - {APP_NAME}",
                        f"\n当前日志文件 {os.path.basename(LOG_FILE)} 存在但为空。\n\n日志文件位置：{os.path.abspath(LOG_FILE)}",
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )
                    msg_box.exec()
                    return
                
                # 根据文件大小决定是使用文本查看器还是直接打开
                if file_size > 1024 * 1024:  # 大于1MB
                    # 文件较大，显示警告
                    from utils import msgbox_frame
                    msg_box = msgbox_frame(
                        f"警告 - {APP_NAME}",
                        f"\n日志文件较大 ({file_size / 1024 / 1024:.2f} MB)，是否仍要打开？\n\n日志文件位置：{os.path.abspath(LOG_FILE)}",
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                    )
                    if msg_box.exec() != QtWidgets.QMessageBox.StandardButton.Yes:
                        return
                
                # 使用操作系统默认程序打开日志文件
                if os.name == 'nt':  # Windows
                    os.startfile(LOG_FILE)
                else:  # macOS 和 Linux
                    import subprocess
                    subprocess.call(['xdg-open', LOG_FILE])
            else:
                # 文件不存在，显示信息和搜索其他日志文件
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                log_dir = os.path.join(root_dir, "log")
                
                # 如果log文件夹不存在，尝试创建它
                if not os.path.exists(log_dir):
                    try:
                        os.makedirs(log_dir, exist_ok=True)
                        from utils import msgbox_frame
                        msg_box = msgbox_frame(
                            f"信息 - {APP_NAME}",
                            f"\n日志文件夹不存在，已创建新的日志文件夹：\n{log_dir}\n\n请在启用调试模式后重试。",
                            QtWidgets.QMessageBox.StandardButton.Ok
                        )
                        msg_box.exec()
                        return
                    except Exception as e:
                        from utils import msgbox_frame
                        msg_box = msgbox_frame(
                            f"错误 - {APP_NAME}",
                            f"\n创建日志文件夹失败：\n\n{str(e)}",
                            QtWidgets.QMessageBox.StandardButton.Ok
                        )
                        msg_box.exec()
                        return
                
                # 搜索log文件夹中的日志文件
                try:
                    log_files = [f for f in os.listdir(log_dir) if f.startswith("log-") and f.endswith(".txt")]
                except Exception as e:
                    from utils import msgbox_frame
                    msg_box = msgbox_frame(
                        f"错误 - {APP_NAME}",
                        f"\n无法读取日志文件夹：\n\n{str(e)}",
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )
                    msg_box.exec()
                    return
                
                if log_files:
                    # 按照修改时间排序，获取最新的日志文件
                    log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
                    latest_log = os.path.join(log_dir, log_files[0])
                    
                    # 获取最新日志文件的创建时间信息
                    try:
                        log_datetime = "-".join(os.path.basename(latest_log)[4:-4].split("-")[:2])
                        log_date = log_datetime.split("-")[0]
                        log_time = log_datetime.split("-")[1] if "-" in log_datetime else "未知时间"
                        date_info = f"日期: {log_date[:4]}-{log_date[4:6]}-{log_date[6:]}"
                        time_info = f"时间: {log_time[:2]}:{log_time[2:4]}:{log_time[4:]}"
                    except:
                        date_info = "日期未知"
                        time_info = "时间未知"
                    
                    from utils import msgbox_frame
                    msg_box = msgbox_frame(
                        f"信息 - {APP_NAME}",
                        f"\n当前日志文件 {os.path.basename(LOG_FILE)} 不存在。\n\n"
                        f"发现最新的日志文件: {os.path.basename(latest_log)}\n"
                        f"({date_info} {time_info})\n\n"
                        f"是否打开此文件？",
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                    )
                    
                    if msg_box.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
                        if os.name == 'nt':  # Windows
                            os.startfile(latest_log)
                        else:  # macOS 和 Linux
                            import subprocess
                            subprocess.call(['xdg-open', latest_log])
                        return
                
                # 如果没有找到任何日志文件
                from utils import msgbox_frame
                msg_box = msgbox_frame(
                    f"信息 - {APP_NAME}",
                    f"\n没有找到有效的日志文件。\n\n"
                    f"预期的日志文件夹：{log_dir}\n\n"
                    f"请确认调试模式已启用，并执行一些操作后再查看日志。",
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
                msg_box.exec()
                
        except Exception as e:
            from utils import msgbox_frame
            msg_box = msgbox_frame(
                f"错误 - {APP_NAME}",
                f"\n处理日志文件时出错：\n\n{str(e)}\n\n文件位置：{os.path.abspath(LOG_FILE)}",
                QtWidgets.QMessageBox.StandardButton.Ok
            )
            msg_box.exec() 