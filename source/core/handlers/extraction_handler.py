import os
import shutil
from PySide6 import QtWidgets
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer, QCoreApplication

from utils.logger import setup_logger
from workers.extraction_thread import ExtractionThread

# 初始化logger
logger = setup_logger("extraction_handler")

class ExtractionHandler:
    """解压处理器，负责管理解压任务和结果处理"""
    
    def __init__(self, main_window):
        """初始化解压处理器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
        """
        self.main_window = main_window
        self.APP_NAME = main_window.APP_NAME if hasattr(main_window, 'APP_NAME') else ""
        self.extraction_progress_window = None
        
    def start_extraction(self, _7z_path, game_folder, plugin_path, game_version, extracted_path=None):
        """开始解压任务
        
        Args:
            _7z_path: 7z文件路径
            game_folder: 游戏文件夹路径
            plugin_path: 插件路径
            game_version: 游戏版本名称
            extracted_path: 已解压的补丁文件路径，如果提供则直接使用它而不进行解压
        """
        # 检查是否处于离线模式
        is_offline = False
        if hasattr(self.main_window, 'offline_mode_manager'):
            is_offline = self.main_window.offline_mode_manager.is_in_offline_mode()
        
        # 创建并显示解压进度窗口，替代原来的消息框
        self.extraction_progress_window = self.main_window.create_extraction_progress_window()
        self.extraction_progress_window.show()
        
        # 确保UI更新
        QCoreApplication.processEvents()
        
        # 创建并启动解压线程
        self.main_window.extraction_thread = ExtractionThread(
            _7z_path, game_folder, plugin_path, game_version, self.main_window, extracted_path
        )
        
        # 连接进度信号
        self.main_window.extraction_thread.progress.connect(self.update_extraction_progress)
        
        # 连接完成信号
        self.main_window.extraction_thread.finished.connect(self.on_extraction_finished_with_hash_check)
        
        # 启动线程
        self.main_window.extraction_thread.start()
        
    def update_extraction_progress(self, progress, status_text):
        """更新解压进度
        
        Args:
            progress: 进度百分比
            status_text: 状态文本
        """
        if self.extraction_progress_window and hasattr(self.extraction_progress_window, 'progress_bar'):
            self.extraction_progress_window.progress_bar.setValue(progress)
            self.extraction_progress_window.status_label.setText(status_text)
            
            # 确保UI更新
            QCoreApplication.processEvents()
            
    def on_extraction_finished_with_hash_check(self, success, error_message, game_version):
        """解压完成后进行哈希校验
        
        Args:
            success: 是否解压成功
            error_message: 错误信息
            game_version: 游戏版本
        """
        # 关闭解压进度窗口
        if self.extraction_progress_window:
            self.extraction_progress_window.close()
            self.extraction_progress_window = None

        # 如果解压失败，显示错误并询问是否继续
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
                if hasattr(self.main_window, 'window_manager'):
                    self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
                # 通知DownloadManager停止下载队列
                self.main_window.download_manager.on_extraction_finished(False)
            return
            
        # 解压成功，进行哈希校验
        self._perform_hash_check(game_version)
        
    def _perform_hash_check(self, game_version):
        """解压成功后进行哈希校验
        
        Args:
            game_version: 游戏版本
        """
        # 导入所需模块
        from config.config import GAME_INFO, PLUGIN_HASH
        from workers.hash_thread import HashThread
        
        # 获取安装路径
        install_paths = {}
        if hasattr(self.main_window, 'game_detector') and hasattr(self.main_window, 'download_manager'):
            game_dirs = self.main_window.game_detector.identify_game_directories_improved(
                self.main_window.download_manager.selected_folder
            )
            
            for game, info in GAME_INFO.items():
                if game in game_dirs and game == game_version:
                    game_dir = game_dirs[game]
                    install_path = os.path.join(game_dir, os.path.basename(info["install_path"]))
                    install_paths[game] = install_path
                    break
        
        if not install_paths:
            # 如果找不到安装路径，直接认为安装成功
            logger.warning(f"未找到 {game_version} 的安装路径，跳过哈希校验")
            self.main_window.installed_status[game_version] = True
            self.main_window.download_manager.on_extraction_finished(True)
            return
        
        # 关闭可能存在的哈希校验窗口
        self.main_window.close_hash_msg_box()
            
        # 显示哈希校验窗口
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(
            check_type="post", 
            auto_close=True,  # 添加自动关闭参数
            close_delay=1000  # 1秒后自动关闭
        )
        
        # 直接创建并启动哈希线程进行校验
        hash_thread = HashThread(
            "after", 
            install_paths, 
            PLUGIN_HASH, 
            self.main_window.installed_status,
            self.main_window
        )
        hash_thread.after_finished.connect(self.on_hash_check_finished)
        
        # 保存引用以便后续使用
        self.hash_thread = hash_thread
        hash_thread.start()
        
    def on_hash_check_finished(self, result):
        """哈希校验完成后的处理
        
        Args:
            result: 校验结果，包含通过状态、游戏版本和消息
        """
        # 导入所需模块
        from config.config import GAME_INFO
        
        # 关闭哈希检查窗口
        self.main_window.close_hash_msg_box()
            
        if not result["passed"]:
            # 校验失败，删除已解压的文件并提示重新下载
            game_version = result["game"]
            error_message = result["message"]
            
            # 临时启用窗口以显示错误消息
            self.main_window.setEnabled(True)
            
            # 获取安装路径
            install_path = None
            if hasattr(self.main_window, 'game_detector') and hasattr(self.main_window, 'download_manager'):
                game_dirs = self.main_window.game_detector.identify_game_directories_improved(
                    self.main_window.download_manager.selected_folder
                )
                
                if game_version in game_dirs and game_version in GAME_INFO:
                    game_dir = game_dirs[game_version]
                    install_path = os.path.join(game_dir, os.path.basename(GAME_INFO[game_version]["install_path"]))
            
            # 如果找到安装路径，尝试删除已解压的文件
            if install_path and os.path.exists(install_path):
                try:
                    os.remove(install_path)
                    logger.debug(f"已删除校验失败的文件: {install_path}")
                except Exception as e:
                    logger.error(f"删除文件失败: {e}")
            
            # 显示错误消息并询问是否重试
            reply = QtWidgets.QMessageBox.question(
                self.main_window,
                f"校验失败 - {self.APP_NAME}",
                f"{error_message}\n\n是否重新下载并安装？",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # 重新下载，将游戏重新添加到下载队列
                self.main_window.setEnabled(False)
                self.main_window.installed_status[game_version] = False
                
                # 获取游戏目录和下载URL
                if hasattr(self.main_window, 'download_manager') and hasattr(self.main_window, 'game_detector'):
                    game_dirs = self.main_window.game_detector.identify_game_directories_improved(
                        self.main_window.download_manager.selected_folder
                    )
                    
                    if game_version in game_dirs:
                        # 重新将游戏添加到下载队列
                        self.main_window.download_manager.download_queue.appendleft([game_version])
                        # 继续下一个下载任务
                        self.main_window.download_manager.next_download_task()
                    else:
                        # 如果找不到游戏目录，继续下一个
                        self.main_window.download_manager.on_extraction_finished(True)
                else:
                    # 如果无法重新下载，继续下一个
                    self.main_window.download_manager.on_extraction_finished(True)
            else:
                # 用户选择不重试，继续下一个
                self.main_window.installed_status[game_version] = False
                self.main_window.download_manager.on_extraction_finished(True)
        else:
            # 校验通过，更新安装状态
            game_version = result["game"]
            self.main_window.installed_status[game_version] = True
            # 通知DownloadManager继续下一个下载任务
            self.main_window.download_manager.on_extraction_finished(True)
            
    def on_extraction_finished(self, success, error_message, game_version):
        """兼容旧版本的回调函数
        
        Args:
            success: 是否解压成功
            error_message: 错误信息
            game_version: 游戏版本
        """
        # 调用新的带哈希校验的回调函数
        self.on_extraction_finished_with_hash_check(success, error_message, game_version) 