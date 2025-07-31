import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from main_window import MainWindow
from core.privacy_manager import PrivacyManager
from utils.logger import setup_logger

if __name__ == "__main__":
    # 初始化日志
    logger = setup_logger("main")
    logger.info("应用启动")
    
    app = QApplication(sys.argv)
    
    # 初始化隐私协议管理器
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
    
    # 显示隐私协议对话框
    if not privacy_manager.show_privacy_dialog():
        logger.info("用户未同意隐私协议，程序退出")
        sys.exit(0)  # 如果用户不同意隐私协议，退出程序
    
    # 用户已同意隐私协议，继续启动程序
    logger.info("隐私协议已同意，启动主程序")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())