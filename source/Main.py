import sys
import os
import datetime
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from main_window import MainWindow
from core.managers.privacy_manager import PrivacyManager
from utils.logger import setup_logger, cleanup_old_logs, log_uncaught_exceptions
from config.config import LOG_FILE, APP_NAME, LOG_RETENTION_DAYS
from utils import load_config

def excepthook(exc_type, exc_value, exc_traceback):
    """全局异常处理钩子，将未捕获的异常记录到日志并显示错误对话框"""
    # 记录异常到日志
    if hasattr(sys, '_excepthook'):
        sys._excepthook(exc_type, exc_value, exc_traceback)
    else:
        log_uncaught_exceptions(exc_type, exc_value, exc_traceback)
    
    # 将异常格式化为易读的形式
    exception_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # 创建错误对话框
    msg = f"程序遇到未处理的异常：\n\n{str(exc_value)}\n\n详细错误已记录到日志文件。"
    try:
        # 尝试使用QMessageBox显示错误
        app = QApplication.instance()
        if app:
            QMessageBox.critical(None, f"错误 - {APP_NAME}", msg)
    except Exception:
        # 如果QMessageBox失败，则使用标准输出
        print(f"严重错误: {msg}")
        print(f"详细错误: {exception_text}")

if __name__ == "__main__":
    # 设置主日志
    logger = setup_logger("main")
    logger.info("应用启动")
    
    # 设置全局异常处理钩子
    sys._excepthook = sys.excepthook
    sys.excepthook = excepthook
    
    # 记录程序启动信息
    logger.debug(f"Python版本: {sys.version}")
    logger.debug(f"运行平台: {sys.platform}")
    
    # 检查配置中是否启用了调试模式
    config = load_config()
    debug_mode = config.get("debug_mode", False)
    
    # 在应用启动时清理过期的日志文件
    cleanup_old_logs(LOG_RETENTION_DAYS)
    logger.debug(f"已执行日志清理，保留最近{LOG_RETENTION_DAYS}天的日志")
    
    # 如果调试模式已启用，确保立即创建主日志文件
    if debug_mode:
        try:
            # 确保log目录存在
            log_dir = os.path.dirname(LOG_FILE)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                logger.debug(f"已创建日志目录: {log_dir}")
            
            # 记录调试会话信息
            logger.debug(f"--- 新调试会话开始于 {os.path.basename(LOG_FILE)} ---")
            logger.debug(f"--- 应用版本: {APP_NAME} ---")
            current_time = datetime.datetime.now()
            formatted_date = current_time.strftime("%Y-%m-%d")
            formatted_time = current_time.strftime("%H:%M:%S")
            logger.debug(f"--- 日期: {formatted_date} 时间: {formatted_time} ---")
                
            logger.debug(f"调试模式已启用，日志文件路径: {os.path.abspath(LOG_FILE)}")
        except Exception as e:
            logger.error(f"创建日志文件失败: {e}")
    
    app = QApplication(sys.argv)
    
    try:
        privacy_manager = PrivacyManager()
    except Exception as e:
        logger.error(f"初始化隐私协议管理器失败: {e}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        QMessageBox.critical(
            None, 
            "隐私协议加载错误", 
            f"无法加载隐私协议管理器，程序将退出。\n\n错误信息：{e}"
        )
        sys.exit(1)
    
    if not privacy_manager.show_privacy_dialog():
        logger.info("用户未同意隐私协议，程序退出")
        sys.exit(0)
    
    logger.info("隐私协议已同意，启动主程序")
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 