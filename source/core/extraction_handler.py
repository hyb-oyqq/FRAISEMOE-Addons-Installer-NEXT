import os
from PySide6 import QtWidgets
from PySide6.QtWidgets import QMessageBox


class ExtractionHandler:
    """解压处理器，负责管理解压任务和结果处理"""
    
    def __init__(self, main_window):
        """初始化解压处理器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
        """
        self.main_window = main_window
        self.APP_NAME = main_window.APP_NAME if hasattr(main_window, 'APP_NAME') else ""
        
    def start_extraction(self, _7z_path, game_folder, plugin_path, game_version):
        """开始解压任务
        
        Args:
            _7z_path: 7z文件路径
            game_folder: 游戏文件夹路径
            plugin_path: 插件路径
            game_version: 游戏版本名称
        """
        # 显示解压中的消息窗口
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="extraction")
        
        # 创建并启动解压线程
        self.main_window.extraction_thread = self.main_window.create_extraction_thread(
            _7z_path, game_folder, plugin_path, game_version
        )
        self.main_window.extraction_thread.finished.connect(self.on_extraction_finished)
        self.main_window.extraction_thread.start()
        
    def on_extraction_finished(self, success, error_message, game_version):
        """解压完成后的处理
        
        Args:
            success: 是否解压成功
            error_message: 错误信息
            game_version: 游戏版本
        """
        # 关闭哈希检查窗口
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.close()
            self.main_window.hash_msg_box = None

        # 处理解压结果
        if not success:
            # 临时启用窗口以显示错误消息
            self.main_window.setEnabled(True)
            
            QtWidgets.QMessageBox.critical(self.main_window, f"错误 - {self.APP_NAME}", error_message)
            self.main_window.installed_status[game_version] = False
            
            # 询问用户是否继续其他游戏的安装
            reply = QtWidgets.QMessageBox.question(
                self.main_window,
                f"继续安装? - {self.APP_NAME}",
                f"\n{game_version} 的补丁安装失败。\n\n是否继续安装其他游戏的补丁？\n",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # 继续下一个，重新禁用窗口
                self.main_window.setEnabled(False)
                # 通知DownloadManager继续下一个下载任务
                self.main_window.download_manager.on_extraction_finished(True)
            else:
                # 用户选择停止，保持窗口启用状态
                self.main_window.ui.start_install_text.setText("开始安装")
                # 通知DownloadManager停止下载队列
                self.main_window.download_manager.on_extraction_finished(False)
        else:
            # 更新安装状态
            self.main_window.installed_status[game_version] = True
            # 通知DownloadManager继续下一个下载任务
            self.main_window.download_manager.on_extraction_finished(True) 