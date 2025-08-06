import os
import sys
import subprocess
import shutil
import json
import webbrowser

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, Qt, QPoint, QRect, QSize
from PySide6.QtWidgets import QMainWindow, QMessageBox, QGraphicsOpacityEffect, QGraphicsColorizeEffect
from PySide6.QtGui import QPalette, QColor, QPainterPath, QRegion, QFont
from PySide6.QtGui import QAction # Added for menu actions

from ui.Ui_install import Ui_MainWindows
from data.config import (
    APP_NAME, PLUGIN, GAME_INFO, BLOCK_SIZE,
    PLUGIN_HASH, UA, CONFIG_URL, LOG_FILE,
    DOWNLOAD_THREADS, DEFAULT_DOWNLOAD_THREAD_LEVEL, APP_VERSION # 添加APP_VERSION导入
)
from utils import (
    load_config, save_config, HashManager, AdminPrivileges, msgbox_frame, load_image_from_file
)
from workers import (
    DownloadThread, ProgressWindow, IpOptimizerThread, 
    HashThread, ExtractionThread, ConfigFetchThread
)
from core import (
    MultiStageAnimations, UIManager, DownloadManager, DebugManager,
    WindowManager, GameDetector, PatchManager, ConfigManager
)
from core.ipv6_manager import IPv6Manager
from handlers import PatchToggleHandler, UninstallHandler
from utils.logger import setup_logger

# 初始化logger
logger = setup_logger("main_window")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口为无边框
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # 设置窗口背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 调整窗口大小以适应背景图片比例 (1280x720)
        self.resize(1280, 720)
        # 设置固定尺寸范围
        self.setMinimumSize(QSize(1024, 576))
        self.setMaximumSize(QSize(1280, 720))
        
        # 初始化UI (从Ui_install.py导入)
        self.ui = Ui_MainWindows()
        self.ui.setupUi(self)
        
        # 初始化配置
        self.config = load_config()
        
        # 初始化工具类
        self.hash_manager = HashManager(BLOCK_SIZE)
        self.admin_privileges = AdminPrivileges()
        
        # 初始化各种管理器 - 调整初始化顺序，避免循环依赖
        # 1. 首先创建必要的基础管理器
        self.animator = MultiStageAnimations(self.ui, self)
        self.window_manager = WindowManager(self)
        self.debug_manager = DebugManager(self)
        
        # 2. 初始化IPv6Manager(应在UIManager之前)
        self.ipv6_manager = IPv6Manager(self)
        
        # 3. 创建UIManager(依赖IPv6Manager)
        self.ui_manager = UIManager(self)
        
        # 4. 为debug_manager设置ui_manager引用
        self.debug_manager.set_ui_manager(self.ui_manager)
        
        # 5. 初始化其他管理器
        self.config_manager = ConfigManager(APP_NAME, CONFIG_URL, UA, self.debug_manager)
        self.game_detector = GameDetector(GAME_INFO, self.debug_manager)
        self.patch_manager = PatchManager(APP_NAME, GAME_INFO, self.debug_manager)
        
        # 6. 初始化离线模式管理器
        from core.offline_mode_manager import OfflineModeManager
        self.offline_mode_manager = OfflineModeManager(self)
        
        # 7. 初始化下载管理器 - 放在最后，因为它可能依赖于其他管理器
        self.download_manager = DownloadManager(self)
        
        # 8. 初始化功能处理程序
        self.uninstall_handler = UninstallHandler(self)
        self.patch_toggle_handler = PatchToggleHandler(self)
        
        # 加载用户下载线程设置
        if "download_thread_level" in self.config and self.config["download_thread_level"] in DOWNLOAD_THREADS:
            self.download_manager.download_thread_level = self.config["download_thread_level"]
        
        # 初始化状态变量
        self.cloud_config = None
        self.config_valid = False  # 添加配置有效标志
        self.patch_manager.initialize_status()
        self.installed_status = self.patch_manager.get_status()  # 获取初始化后的状态
        self.hash_msg_box = None
        self.last_error_message = ""  # 添加错误信息记录
        self.version_warning = False  # 添加版本警告标志
        self.install_button_enabled = True  # 默认启用安装按钮
        self.progress_window = None
        
        # 设置关闭按钮事件连接
        if hasattr(self.ui, 'close_btn'):
            self.ui.close_btn.clicked.connect(self.close)
        
        if hasattr(self.ui, 'minimize_btn'):
            self.ui.minimize_btn.clicked.connect(self.showMinimized)
        
        # 创建缓存目录
        if not os.path.exists(PLUGIN):
            try:
                os.makedirs(PLUGIN)
            except OSError as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    f"错误 - {APP_NAME}",
                    f"\n无法创建缓存位置\n\n使用管理员身份运行或检查文件读写权限\n\n【错误信息】：{e}\n",
                )
                sys.exit(1)
        
        # 连接信号 - 绑定到新按钮
        self.ui.start_install_btn.clicked.connect(self.handle_install_button_click)
        self.ui.uninstall_btn.clicked.connect(self.uninstall_handler.handle_uninstall_button_click)  # 使用卸载处理程序
        self.ui.toggle_patch_btn.clicked.connect(self.patch_toggle_handler.handle_toggle_patch_button_click)  # 使用补丁切换处理程序
        self.ui.exit_btn.clicked.connect(self.shutdown_app)
        
        # 初始化按钮状态标记
        self.install_button_enabled = False
        self.last_error_message = ""
        
        # 检查管理员权限和进程
        try:
            # 检查管理员权限
            self.admin_privileges.request_admin_privileges()
            # 检查并终止相关进程
            self.admin_privileges.check_and_terminate_processes()
        except KeyboardInterrupt:
            logger.warning("权限检查或进程检查被用户中断")
            QtWidgets.QMessageBox.warning(
                self,
                f"警告 - {APP_NAME}",
                "\n操作被中断，请重新启动应用。\n"
            )
            sys.exit(1)
        except Exception as e:
            logger.error(f"权限检查或进程检查时发生错误: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                f"错误 - {APP_NAME}",
                f"\n权限检查或进程检查时发生错误，请重新启动应用。\n\n【错误信息】：{e}\n"
            )
            sys.exit(1)
        
        # 备份hosts文件
        self.download_manager.hosts_manager.backup()
        
        # 根据初始配置决定是否开启Debug模式
        if "debug_mode" in self.config and self.config["debug_mode"]:
            # 先启用日志系统
            self.debug_manager.start_logging()
            logger.info("通过配置启动调试模式")
        # 检查UI设置
        if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action:
            if self.ui_manager.debug_action.isChecked():
                # 如果通过UI启用了调试模式，确保日志系统已启动
                if not self.debug_manager.logger:
                    self.debug_manager.start_logging()
                    logger.info("通过UI启动调试模式")
        
        # 设置UI，包括窗口图标和菜单
        self.ui_manager.setup_ui()
        
        # 检查是否有离线补丁文件，如果有则自动切换到离线模式
        self.check_and_set_offline_mode()
        
        # 获取云端配置
        self.fetch_cloud_config()
        
        # 启动动画
        self.start_animations()
    
    # 窗口事件处理 - 委托给WindowManager
    def mousePressEvent(self, event):
        self.window_manager.handle_mouse_press(event)
    
    def mouseMoveEvent(self, event):
        self.window_manager.handle_mouse_move(event)
    
    def mouseReleaseEvent(self, event):
        self.window_manager.handle_mouse_release(event)
    
    def resizeEvent(self, event):
        self.window_manager.handle_resize(event)
        super().resizeEvent(event)
    
    def start_animations(self):
        """开始启动动画"""
        # 不再禁用退出按钮的交互性，只通过样式表控制外观
        # 但仍然需要跟踪动画状态，防止用户在动画播放过程中退出
        self.animation_in_progress = True
        
        # 按钮容器初始是隐藏的，无需在这里禁用
        # 但确保开始安装按钮仍然处于禁用状态
        self.set_start_button_enabled(False)
        
        # 在动画开始前初始化
        self.animator.initialize()
        
        # 连接动画完成信号
        self.animator.animation_finished.connect(self.on_animations_finished)
        
        # 启动动画
        self.animator.start_animations()

    def on_animations_finished(self):
        """动画完成后启用按钮"""
        self.animation_in_progress = False
        
        # 启用所有菜单按钮
        self.ui.start_install_btn.setEnabled(True)
        self.ui.uninstall_btn.setEnabled(True)
        self.ui.toggle_patch_btn.setEnabled(True)  # 启用禁/启用补丁按钮
        self.ui.exit_btn.setEnabled(True)
        
        # 检查是否处于离线模式
        is_offline_mode = False
        if hasattr(self, 'offline_mode_manager'):
            is_offline_mode = self.offline_mode_manager.is_in_offline_mode()
            
        # 如果是离线模式，始终启用开始安装按钮
        if is_offline_mode:
            self.set_start_button_enabled(True)
        # 否则，只有在配置有效时才启用开始安装按钮
        elif self.config_valid:
            self.set_start_button_enabled(True)
        else:
            self.set_start_button_enabled(False)
            
    def set_start_button_enabled(self, enabled, installing=False):
        """[已弃用] 设置按钮启用状态的旧方法，保留以兼容旧代码
        
        现在推荐使用主窗口的setEnabled方法和直接设置按钮文本
        
        Args:
            enabled: 是否启用按钮
            installing: 是否正在安装中
        """
        # 直接设置按钮文本，不改变窗口启用状态
        if installing:
            self.ui.start_install_text.setText("正在安装")
            self.install_button_enabled = False
        else:
            if enabled:
                self.ui.start_install_text.setText("开始安装")
            else:
                self.ui.start_install_text.setText("!无法安装!")
                
            self.install_button_enabled = enabled

    def fetch_cloud_config(self):
        """获取云端配置（异步方式）"""
        self.config_manager.fetch_cloud_config(
            lambda url, headers, debug_mode, parent=None: ConfigFetchThread(url, headers, debug_mode, self),
            self.on_config_fetched
        )

    def on_config_fetched(self, data, error_message):
        """云端配置获取完成的回调处理
        
        Args:
            data: 获取到的配置数据
            error_message: 错误信息，如果有
        """
        # 处理返回结果
        result = self.config_manager.on_config_fetched(data, error_message)
        
        # 根据返回的操作执行相应动作
        if result and "action" in result:
            if result["action"] == "exit":
                # 强制关闭程序
                self.shutdown_app(force_exit=True)
            elif result["action"] == "disable_button":
                # 禁用开始安装按钮
                self.set_start_button_enabled(False)
            elif result["action"] == "enable_button":
                # 启用开始安装按钮
                self.set_start_button_enabled(True)
                # 检查是否需要记录版本警告
                if "version_warning" in result and result["version_warning"]:
                    self.version_warning = True
                else:
                    self.version_warning = False
        
        # 同步状态
        self.cloud_config = self.config_manager.get_cloud_config()
        self.config_valid = self.config_manager.is_config_valid()
        self.last_error_message = self.config_manager.get_last_error()
        
        # 重新启用窗口，恢复用户交互
        self.setEnabled(True)

    def toggle_debug_mode(self, checked):
        """切换调试模式
        
        Args:
            checked: 是否启用调试模式
        """
        self.debug_manager.toggle_debug_mode(checked)
    
    def save_config(self, config):
        """保存配置的便捷方法"""
        self.config_manager.save_config(config)
        
    def create_download_thread(self, url, _7z_path, game_version):
        """创建下载线程
        
        Args:
            url: 下载URL
            _7z_path: 7z文件保存路径
            game_version: 游戏版本名称
            
        Returns:
            DownloadThread: 下载线程实例
        """
        from workers import DownloadThread
        return DownloadThread(url, _7z_path, game_version, parent=self)
        
    def create_progress_window(self):
        """创建下载进度窗口
        
        Returns:
            ProgressWindow: 进度窗口实例
        """
        return ProgressWindow(self)
        
    def create_hash_thread(self, mode, install_paths):
        """创建哈希检查线程
        
        Args:
            mode: 检查模式，"pre"或"after"
            install_paths: 安装路径字典
            
        Returns:
            HashThread: 哈希检查线程实例
        """
        return HashThread(mode, install_paths, PLUGIN_HASH, self.installed_status, self)
        
    def create_extraction_thread(self, _7z_path, game_folder, plugin_path, game_version):
        """创建解压线程
        
        Args:
            _7z_path: 7z文件路径
            game_folder: 游戏文件夹路径
            plugin_path: 插件路径
            game_version: 游戏版本
            
        Returns:
            ExtractionThread: 解压线程实例
        """
        return ExtractionThread(_7z_path, game_folder, plugin_path, game_version, self)
        
    def after_hash_compare(self):
        """进行安装后哈希比较"""
        # 禁用窗口已在安装流程开始时完成
        
        # 检查是否处于离线模式
        is_offline = False
        if hasattr(self, 'offline_mode_manager'):
            is_offline = self.offline_mode_manager.is_in_offline_mode()
        
        self.hash_msg_box = self.hash_manager.hash_pop_window(check_type="after", is_offline=is_offline)

        install_paths = self.download_manager.get_install_paths()
        
        self.hash_thread = self.create_hash_thread("after", install_paths)
        self.hash_thread.after_finished.connect(self.on_after_hash_finished)
        self.hash_thread.start()

    def on_after_hash_finished(self, result):
        """哈希比较完成后的处理
        
        Args:
            result: 哈希比较结果
        """
        # 确保哈希检查窗口关闭，无论是否还在显示
        if self.hash_msg_box:
            try:
                if self.hash_msg_box.isVisible():
                    self.hash_msg_box.close()
                else:
                    # 如果窗口已经不可见但没有关闭，也要尝试关闭
                    self.hash_msg_box.close()
            except:
                pass  # 忽略任何关闭窗口时的错误
            self.hash_msg_box = None

        if not result["passed"]:
            # 启用窗口以显示错误消息
            self.setEnabled(True)
            
            game = result.get("game", "未知游戏")
            message = result.get("message", "发生未知错误。")
            msg_box = msgbox_frame(
                f"文件校验失败 - {APP_NAME}",
                message,
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()

        # 恢复窗口状态
        self.setEnabled(True)
        self.ui.start_install_text.setText("开始安装")
        
        # 添加短暂延迟确保UI更新
        QTimer.singleShot(100, self.show_result)

    def show_result(self):
        """显示安装结果，区分不同情况"""
        # 获取当前安装状态
        installed_versions = []  # 成功安装的版本
        skipped_versions = []    # 已有补丁跳过的版本
        failed_versions = []     # 安装失败的版本
        not_found_versions = []  # 未找到的版本
        
        # 获取所有游戏版本路径
        install_paths = self.download_manager.get_install_paths() if hasattr(self.download_manager, "get_install_paths") else {}
        
        for game_version, is_installed in self.installed_status.items():
            # 只处理install_paths中存在的游戏版本
            if game_version in install_paths:
                path = install_paths[game_version]
                
                # 检查游戏是否存在但未通过本次安装补丁
                if is_installed:
                    # 游戏已安装补丁
                    if hasattr(self, 'download_queue_history') and game_version not in self.download_queue_history:
                        # 已有补丁，被跳过下载
                        skipped_versions.append(game_version)
                    else:
                        # 本次成功安装
                        installed_versions.append(game_version)
                else:
                    # 游戏未安装补丁
                    if os.path.exists(path):
                        # 游戏文件夹存在，但安装失败
                        failed_versions.append(game_version)
                    else:
                        # 游戏文件夹不存在
                        not_found_versions.append(game_version)
        
        # 构建结果信息
        result_text = f"\n安装结果：\n"
        
        # 总数统计 - 不再显示已跳过的数量
        total_installed = len(installed_versions)
        total_failed = len(failed_versions)
        
        result_text += f"安装成功：{total_installed} 个  安装失败：{total_failed} 个\n\n"
        
        # 详细列表
        if installed_versions:
            result_text += f"【成功安装】:\n{chr(10).join(installed_versions)}\n\n"
            
        if failed_versions:
            result_text += f"【安装失败】:\n{chr(10).join(failed_versions)}\n\n"
            
        if not_found_versions:
            # 只有在真正检测到了游戏但未安装补丁时才显示
            result_text += f"【尚未安装补丁的游戏】:\n{chr(10).join(not_found_versions)}\n"
        
        QMessageBox.information(
            self,
            f"安装完成 - {APP_NAME}",
            result_text
        )

    def closeEvent(self, event):
        """窗口关闭事件处理
        
        Args:
            event: 关闭事件
        """
        self.shutdown_app(event)

    def shutdown_app(self, event=None, force_exit=False):
        """关闭应用程序
        
        Args:
            event: 关闭事件，如果是从closeEvent调用的
            force_exit: 是否强制退出
        """
        # 检查是否有动画或任务正在进行
        if hasattr(self, 'animation_in_progress') and self.animation_in_progress and not force_exit:
            # 如果动画正在进行，阻止退出
            if event:
                event.ignore()
            return
            
        # 检查是否有下载任务正在进行
        if hasattr(self.download_manager, 'current_download_thread') and \
           self.download_manager.current_download_thread and \
           self.download_manager.current_download_thread.isRunning() and not force_exit:
            # 询问用户是否确认退出
            reply = QMessageBox.question(
                self,
                f"确认退出 - {APP_NAME}",
                "\n下载任务正在进行中，确定要退出吗？\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                if event:
                    event.ignore()
                return
                
        # 恢复hosts文件（如果未禁用自动还原）
        self.download_manager.hosts_manager.restore()
        
        # 额外检查并清理hosts文件中的残留记录（如果未禁用自动还原）
        self.download_manager.hosts_manager.check_and_clean_all_entries()
        
        # 停止日志记录
        self.debug_manager.stop_logging()

        if not force_exit:
            reply = QMessageBox.question(
                self,
                f"确认退出 - {APP_NAME}",
                "\n确定要退出吗？\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                if event:
                    event.ignore()
                return

        # 退出应用程序
        if event:
            event.accept()
        else:
            sys.exit(0)

    def handle_install_button_click(self):
        """处理安装按钮点击事件
        根据按钮当前状态决定是显示错误还是执行安装
        """
        # 检查是否处于离线模式
        is_offline_mode = False
        if hasattr(self, 'offline_mode_manager'):
            is_offline_mode = self.offline_mode_manager.is_in_offline_mode()
        
        # 如果版本过低且在在线模式下，提示用户更新
        if self.last_error_message == "update_required" and not is_offline_mode:
            # 在线模式下提示用户更新软件
            msg_box = msgbox_frame(
                f"更新提示 - {APP_NAME}",
                "\n当前版本过低，请及时更新。\n如需联网下载补丁，请更新到最新版，否则无法下载。\n\n是否切换到离线模式继续使用？\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if msg_box.exec() == QMessageBox.StandardButton.Yes:
                # 切换到离线模式
                if self.ui_manager and hasattr(self.ui_manager, 'switch_work_mode'):
                    self.ui_manager.switch_work_mode("offline")
            return
            
        if not self.install_button_enabled:
            # 按钮处于"无法安装"状态
            if self.last_error_message == "directory_not_found":
                # 目录识别失败的特定错误信息
                reply = msgbox_frame(
                    f"目录错误 - {APP_NAME}",
                    "\n未能识别游戏目录，请确认选择的是游戏的上级目录，并且目录中包含Nekopara游戏文件夹。\n\n是否重新选择目录？\n",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply.exec() == QMessageBox.StandardButton.Yes:
                    # 重新启用按钮并允许用户选择目录
                    self.set_start_button_enabled(True)
                    # 直接调用文件对话框
                    self.download_manager.file_dialog()
            else:
                # 检查是否处于离线模式
                if is_offline_mode and self.last_error_message == "network_error":
                    # 如果是离线模式且错误是网络相关的，提示切换到在线模式
                    reply = msgbox_frame(
                        f"离线模式提示 - {APP_NAME}",
                        "\n当前处于离线模式，但本地补丁文件不完整。\n\n是否切换到在线模式尝试下载？\n",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply.exec() == QMessageBox.StandardButton.Yes:
                        # 切换到在线模式
                        if self.ui_manager and hasattr(self.ui_manager, 'switch_work_mode'):
                            self.ui_manager.switch_work_mode("online")
                            # 重试获取配置
                            self.fetch_cloud_config()
                else:
                    # 网络错误或其他错误
                    reply = msgbox_frame(
                        f"错误 - {APP_NAME}",
                        "\n访问云端配置失败，请检查网络状况或稍后再试。\n\n是否重新尝试连接？\n",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply.exec() == QMessageBox.StandardButton.Yes:
                        # 重试获取配置
                        self.fetch_cloud_config()
        else:
            # 按钮处于"开始安装"状态，正常执行安装流程
            # 检查是否处于离线模式
            if is_offline_mode:
                # 如果是离线模式，使用离线安装流程
                # 先选择游戏目录
                self.selected_folder = QtWidgets.QFileDialog.getExistingDirectory(
                    self, f"选择游戏所在【上级目录】 {APP_NAME}"
                )
                if not self.selected_folder:
                    QtWidgets.QMessageBox.warning(
                        self, f"通知 - {APP_NAME}", "\n未选择任何目录,请重新选择\n"
                    )
                    return
                
                # 保存选择的目录到下载管理器
                self.download_manager.selected_folder = self.selected_folder
                
                # 设置按钮状态
                self.ui.start_install_text.setText("正在安装")
                self.setEnabled(False)
                
                # 清除游戏检测器的目录缓存
                if hasattr(self, 'game_detector') and hasattr(self.game_detector, 'clear_directory_cache'):
                    self.game_detector.clear_directory_cache()
                
                # 识别游戏目录
                game_dirs = self.game_detector.identify_game_directories_improved(self.selected_folder)
                
                if not game_dirs:
                    self.last_error_message = "directory_not_found"
                    QtWidgets.QMessageBox.warning(
                        self, 
                        f"目录错误 - {APP_NAME}", 
                        "\n未能识别到任何游戏目录。\n\n请确认您选择的是游戏的上级目录，并且该目录中包含NEKOPARA系列游戏文件夹。\n"
                    )
                    self.setEnabled(True)
                    self.ui.start_install_text.setText("开始安装")
                    return
                
                # 显示游戏选择对话框
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("选择要安装的游戏")
                dialog.resize(400, 300)
                
                layout = QtWidgets.QVBoxLayout(dialog)
                
                # 添加"选择要安装的游戏"标签
                title_label = QtWidgets.QLabel("选择要安装的游戏", dialog)
                title_label.setFont(QFont(title_label.font().family(), title_label.font().pointSize(), QFont.Bold))
                layout.addWidget(title_label)
                
                # 添加游戏列表控件
                list_widget = QtWidgets.QListWidget(dialog)
                list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)  # 允许多选
                for game_version in game_dirs.keys():
                    list_widget.addItem(game_version)
                    # 默认选中所有项目
                    list_widget.item(list_widget.count() - 1).setSelected(True)
                layout.addWidget(list_widget)
                
                # 添加全选按钮
                select_all_btn = QtWidgets.QPushButton("全选", dialog)
                select_all_btn.clicked.connect(lambda: list_widget.selectAll())
                layout.addWidget(select_all_btn)
                
                # 添加确定和取消按钮
                buttons_layout = QtWidgets.QHBoxLayout()
                ok_button = QtWidgets.QPushButton("确定", dialog)
                cancel_button = QtWidgets.QPushButton("取消", dialog)
                buttons_layout.addWidget(ok_button)
                buttons_layout.addWidget(cancel_button)
                layout.addLayout(buttons_layout)
                
                # 连接按钮事件
                ok_button.clicked.connect(dialog.accept)
                cancel_button.clicked.connect(dialog.reject)
                
                # 显示对话框
                if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                    # 获取选择的游戏
                    selected_games = [item.text() for item in list_widget.selectedItems()]
                    
                    if selected_games:
                        # 使用离线模式管理器进行安装
                        self.offline_mode_manager.install_offline_patches(selected_games)
                    else:
                        QtWidgets.QMessageBox.information(
                            self, 
                            f"通知 - {APP_NAME}", 
                            "\n未选择任何游戏，安装已取消。\n"
                        )
                        self.setEnabled(True)
                        self.ui.start_install_text.setText("开始安装")
                else:
                    # 用户取消了选择
                    self.setEnabled(True)
                    self.ui.start_install_text.setText("开始安装")
            else:
                # 在线模式下，检查版本是否过低
                if hasattr(self, 'version_warning') and self.version_warning:
                    # 版本过低，提示用户更新
                    msg_box = msgbox_frame(
                        f"版本过低 - {APP_NAME}",
                        "\n当前版本过低，无法使用在线下载功能。\n\n请更新到最新版本或切换到离线模式。\n",
                        QMessageBox.StandardButton.Ok
                    )
                    msg_box.exec()
                else:
                    # 版本正常，使用原有的下载流程
                    self.download_manager.file_dialog()

    def check_and_set_offline_mode(self):
        """检查是否有离线补丁文件，如果有则自动启用离线模式
        
        Returns:
            bool: 是否成功切换到离线模式
        """
        try:
            # 初始化离线模式管理器
            if not hasattr(self, 'offline_mode_manager') or self.offline_mode_manager is None:
                from core.offline_mode_manager import OfflineModeManager
                self.offline_mode_manager = OfflineModeManager(self)
            
            # 扫描离线补丁文件
            self.offline_mode_manager.scan_for_offline_patches()
            
            # 如果找到离线补丁文件，启用离线模式
            if self.offline_mode_manager.has_offline_patches():
                self.offline_mode_manager.set_offline_mode(True)
                
                # 启用开始安装按钮
                self.set_start_button_enabled(True)
                
                logger.debug(f"DEBUG: 已自动切换到离线模式，找到离线补丁文件: {list(self.offline_mode_manager.offline_patches.keys())}")
                logger.debug(f"DEBUG: 离线模式下启用开始安装按钮")
                return True
            else:
                # 如果没有找到离线补丁文件，禁用离线模式
                self.offline_mode_manager.set_offline_mode(False)
                
                # 检查是否有云端配置，如果没有则禁用开始安装按钮
                if not self.config_valid:
                    self.set_start_button_enabled(False)
                
                logger.debug("DEBUG: 未找到离线补丁文件，使用在线模式")
                return False
                
        except Exception as e:
            # 如果出现异常，禁用离线模式
            if hasattr(self, 'offline_mode_manager') and self.offline_mode_manager is not None:
                self.offline_mode_manager.set_offline_mode(False)
            
            # 检查是否有云端配置，如果没有则禁用开始安装按钮
            if not self.config_valid:
                self.set_start_button_enabled(False)
                
            logger.error(f"错误: 检查离线模式时发生异常: {e}")
            return False



 