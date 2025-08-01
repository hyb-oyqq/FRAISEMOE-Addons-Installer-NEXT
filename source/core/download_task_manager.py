from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QPushButton, QLabel, QButtonGroup, QHBoxLayout
from PySide6.QtGui import QFont

from data.config import DOWNLOAD_THREADS


class DownloadTaskManager:
    """下载任务管理器，负责管理下载任务和线程设置"""
    
    def __init__(self, main_window, download_thread_level="medium"):
        """初始化下载任务管理器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
            download_thread_level: 下载线程级别，默认为"medium"
        """
        self.main_window = main_window
        self.APP_NAME = main_window.APP_NAME if hasattr(main_window, 'APP_NAME') else ""
        self.current_download_thread = None
        self.download_thread_level = download_thread_level
    
    def start_download(self, url, _7z_path, game_version, game_folder, plugin_path):
        """启动下载线程
        
        Args:
            url: 下载URL
            _7z_path: 7z文件保存路径
            game_version: 游戏版本名称
            game_folder: 游戏文件夹路径
            plugin_path: 插件路径
        """
        # 按钮在file_dialog中已设置为禁用状态
        
        # 创建并连接下载线程
        self.current_download_thread = self.main_window.create_download_thread(url, _7z_path, game_version)
        self.current_download_thread.progress.connect(self.main_window.progress_window.update_progress)
        self.current_download_thread.finished.connect(
            lambda success, error: self.main_window.download_manager.on_download_finished(
                success,
                error,
                url,
                game_folder,
                game_version,
                _7z_path,
                plugin_path,
            )
        )
        
        # 连接停止按钮到download_manager的on_download_stopped方法
        self.main_window.progress_window.stop_button.clicked.connect(self.main_window.download_manager.on_download_stopped)
        
        # 连接暂停/恢复按钮
        self.main_window.progress_window.pause_resume_button.clicked.connect(self.toggle_download_pause)
        
        # 启动线程和显示进度窗口
        self.current_download_thread.start()
        self.main_window.progress_window.exec()

    def toggle_download_pause(self):
        """切换下载的暂停/恢复状态"""
        if not self.current_download_thread:
            return
            
        # 获取当前暂停状态
        is_paused = self.current_download_thread.is_paused()
        
        if is_paused:
            # 如果已暂停，则恢复下载
            success = self.current_download_thread.resume()
            if success:
                self.main_window.progress_window.update_pause_button_state(False)
        else:
            # 如果未暂停，则暂停下载
            success = self.current_download_thread.pause()
            if success:
                self.main_window.progress_window.update_pause_button_state(True)
    
    def get_download_thread_count(self):
        """获取当前下载线程设置对应的线程数
        
        Returns:
            int: 下载线程数
        """
        # 获取当前线程级别对应的线程数
        thread_count = DOWNLOAD_THREADS.get(self.download_thread_level, DOWNLOAD_THREADS["medium"])
        return thread_count
        
    def set_download_thread_level(self, level):
        """设置下载线程级别
        
        Args:
            level: 线程级别 (low, medium, high, extreme, insane)
            
        Returns:
            bool: 设置是否成功
        """
        if level in DOWNLOAD_THREADS:
            old_level = self.download_thread_level
            self.download_thread_level = level
            
            # 只有非极端级别才保存到配置
            if level not in ["extreme", "insane"]:
                if hasattr(self.main_window, 'config'):
                    self.main_window.config["download_thread_level"] = level
                    self.main_window.save_config(self.main_window.config)
                    
            return True
        return False
    
    def show_download_thread_settings(self):
        """显示下载线程设置对话框"""
        # 创建对话框
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(f"下载线程设置 - {self.APP_NAME}")
        dialog.setMinimumWidth(350)
        
        layout = QVBoxLayout(dialog)
        
        # 添加说明标签
        info_label = QLabel("选择下载线程数量（更多线程通常可以提高下载速度）：", dialog)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 创建按钮组
        button_group = QButtonGroup(dialog)
        
        # 添加线程选项
        thread_options = {
            "low": f"低速 - {DOWNLOAD_THREADS['low']}线程（慢慢来，不着急）",
            "medium": f"中速 - {DOWNLOAD_THREADS['medium']}线程（快人半步）",
            "high": f"高速 - {DOWNLOAD_THREADS['high']}线程（默认，推荐配置）",
            "extreme": f"极速 - {DOWNLOAD_THREADS['extreme']}线程（如果你对你的网和电脑很自信的话）",
            "insane": f"狂暴 - {DOWNLOAD_THREADS['insane']}线程（看看是带宽和性能先榨干还是牛牛先榨干）"
        }
        
        radio_buttons = {}
        
        for level, text in thread_options.items():
            radio = QRadioButton(text, dialog)
            
            # 选中当前使用的线程级别
            if level == self.download_thread_level:
                radio.setChecked(True)
                
            button_group.addButton(radio)
            layout.addWidget(radio)
            radio_buttons[level] = radio
            
        layout.addSpacing(10)
        
        # 添加按钮区域
        btn_layout = QHBoxLayout()
        
        ok_button = QPushButton("确定", dialog)
        cancel_button = QPushButton("取消", dialog)
        
        btn_layout.addWidget(ok_button)
        btn_layout.addWidget(cancel_button)
        
        layout.addLayout(btn_layout)
        
        # 连接按钮事件
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        # 显示对话框
        result = dialog.exec()
        
        # 处理结果
        if result == QDialog.DialogCode.Accepted:
            # 获取用户选择的线程级别
            selected_level = None
            for level, radio in radio_buttons.items():
                if radio.isChecked():
                    selected_level = level
                    break
                    
            if selected_level:
                # 为极速和狂暴模式显示警告
                if selected_level in ["extreme", "insane"]:
                    warning_result = QtWidgets.QMessageBox.warning(
                        self.main_window,
                        f"高风险警告 - {self.APP_NAME}",
                        "警告！过高的线程数可能导致CPU负载过高或其他恶性问题！\n你确定要这么做吗？",
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                        QtWidgets.QMessageBox.StandardButton.No
                    )
                    
                    if warning_result != QtWidgets.QMessageBox.StandardButton.Yes:
                        return False
                
                success = self.set_download_thread_level(selected_level)
                
                if success:
                    # 显示设置成功消息
                    thread_count = DOWNLOAD_THREADS[selected_level]
                    message = f"\n已成功设置下载线程为: {thread_count}线程\n"
                    
                    # 对于极速和狂暴模式，添加仅本次生效的提示
                    if selected_level in ["extreme", "insane"]:
                        message += "\n注意：极速/狂暴模式仅本次生效。软件重启后将恢复默认设置。\n"
                    
                    QtWidgets.QMessageBox.information(
                        self.main_window,
                        f"设置成功 - {self.APP_NAME}",
                        message
                    )
                
            return True
            
        return False 
    
    def stop_download(self):
        """停止当前下载线程"""
        if self.current_download_thread and self.current_download_thread.isRunning():
            self.current_download_thread.stop()
            self.current_download_thread.wait()  # 等待线程完全终止
            return True
        return False 