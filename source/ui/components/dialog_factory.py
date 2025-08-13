"""
对话框工厂
负责创建和管理各种类型的对话框
"""

from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QProgressBar, QLabel, QApplication
from PySide6.QtCore import Qt

from utils import msgbox_frame
from config.config import APP_NAME
from workers.download import ProgressWindow


class DialogFactory:
    """对话框工厂类"""
    
    def __init__(self, main_window):
        """初始化对话框工厂
        
        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        self.loading_dialog = None
    
    def create_message_box(self, title, message, buttons=QMessageBox.StandardButton.Ok):
        """创建统一风格的消息框

        Args:
            title: 消息框标题
            message: 消息内容
            buttons: 按钮类型，默认为确定按钮

        Returns:
            QMessageBox: 配置好的消息框实例
        """
        msg_box = msgbox_frame(
            f"{title} - {APP_NAME}",
            message,
            buttons,
        )
        return msg_box
    
    def create_progress_window(self, title, initial_text="准备中..."):
        """创建并返回一个通用的进度窗口
        
        Args:
            title (str): 窗口标题
            initial_text (str): 初始状态文本

        Returns:
            QDialog: 配置好的进度窗口实例
        """
        # 如果是下载进度窗口，使用专用的ProgressWindow类
        if "下载" in title:
            return ProgressWindow(self.main_window)
        
        # 其他情况使用基本的进度窗口
        progress_window = QDialog(self.main_window)
        progress_window.setWindowTitle(f"{title} - {APP_NAME}")
        progress_window.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        layout.addWidget(progress_bar)
        
        status_label = QLabel(initial_text)
        layout.addWidget(status_label)
        
        progress_window.setLayout(layout)
        # 将控件附加到窗口对象上，以便外部访问
        progress_window.progress_bar = progress_bar
        progress_window.status_label = status_label
        
        return progress_window

    def show_loading_dialog(self, message):
        """显示或更新加载对话框
        
        Args:
            message: 要显示的加载消息
        """
        if not self.loading_dialog:
            self.loading_dialog = QDialog(self.main_window)
            self.loading_dialog.setWindowTitle(f"请稍候 - {APP_NAME}")
            self.loading_dialog.setFixedSize(300, 100)
            self.loading_dialog.setModal(True)
            layout = QVBoxLayout()
            loading_label = QLabel(message)
            loading_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(loading_label)
            self.loading_dialog.setLayout(layout)
            # 将label附加到dialog，方便后续更新
            self.loading_dialog.loading_label = loading_label
        else:
            self.loading_dialog.loading_label.setText(message)
        
        self.loading_dialog.show()
        # 强制UI更新
        QApplication.processEvents()

    def hide_loading_dialog(self):
        """隐藏并销毁加载对话框"""
        if self.loading_dialog:
            self.loading_dialog.hide()
            self.loading_dialog = None
    
    def show_simple_message(self, title, message, message_type="info"):
        """显示简单的消息提示
        
        Args:
            title: 标题
            message: 消息内容
            message_type: 消息类型，可选 "info", "warning", "error", "question"
        """
        if message_type == "question":
            buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        else:
            buttons = QMessageBox.StandardButton.Ok
            
        msg_box = self.create_message_box(title, message, buttons)
        
        if message_type == "question":
            return msg_box.exec()
        else:
            msg_box.exec()
            return None
    
    def show_confirmation_dialog(self, title, message):
        """显示确认对话框
        
        Args:
            title: 标题
            message: 消息内容
            
        Returns:
            bool: 用户是否选择了确认
        """
        msg_box = self.create_message_box(
            title, 
            message, 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return msg_box.exec() == QMessageBox.StandardButton.Yes