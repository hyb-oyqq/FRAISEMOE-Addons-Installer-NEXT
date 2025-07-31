import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from core.privacy_manager import PrivacyManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 初始化隐私协议管理器
    privacy_manager = PrivacyManager()
    
    # 显示隐私协议对话框（仅在首次运行或用户未同意时显示）
    if not privacy_manager.show_privacy_dialog():
        print("用户未同意隐私协议，程序退出")
        sys.exit(0)  # 如果用户不同意隐私协议，退出程序
    
    # 用户已同意隐私协议，继续启动程序
    print("隐私协议已同意，启动主程序")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())