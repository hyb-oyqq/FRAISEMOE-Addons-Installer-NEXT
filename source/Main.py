import sys
import os
import datetime
from PySide6.QtWidgets import QApplication, QMessageBox
from main_window import MainWindow
from core.privacy_manager import PrivacyManager
from utils.logger import setup_logger
from data.config import LOG_FILE, APP_NAME
from utils import load_config

if __name__ == "__main__":
    # 设置主日志
    logger = setup_logger("main")
    logger.info("应用启动")
    
    # 检查配置中是否启用了调试模式
    config = load_config()
    debug_mode = config.get("debug_mode", False)
    
    # 如果调试模式已启用，确保立即创建主日志文件
    if debug_mode:
        try:
            # 确保log目录存在
            log_dir = os.path.dirname(LOG_FILE)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                logger.info(f"已创建日志目录: {log_dir}")
            
            # 创建新的日志文件（使用覆盖模式）
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                current_time = datetime.datetime.now()
                formatted_date = current_time.strftime("%Y-%m-%d")
                formatted_time = current_time.strftime("%H:%M:%S")
                f.write(f"--- 新调试会话开始于 {os.path.basename(LOG_FILE)} ---\n")
                f.write(f"--- 应用版本: {APP_NAME} ---\n")
                f.write(f"--- 日期: {formatted_date} 时间: {formatted_time} ---\n\n")
                
            logger.info(f"调试模式已启用，日志文件路径: {os.path.abspath(LOG_FILE)}")
        except Exception as e:
            logger.error(f"创建日志文件失败: {e}")
    
    app = QApplication(sys.argv)
    
    try:
        privacy_manager = PrivacyManager()
    except Exception as e:
        logger.error(f"初始化隐私协议管理器失败: {e}")
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