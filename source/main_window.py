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
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel # Added for progress window

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
    WindowManager, GameDetector, PatchManager, ConfigManager, PatchDetector
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
        self.patch_manager = PatchManager(APP_NAME, GAME_INFO, self.debug_manager, self)
        
        # 6. 初始化补丁检测模块
        self.patch_detector = PatchDetector(self)
        
        # 7. 设置补丁检测器到补丁管理器
        self.patch_manager.set_patch_detector(self.patch_detector)
        
        # 8. 初始化离线模式管理器
        from core.offline_mode_manager import OfflineModeManager
        self.offline_mode_manager = OfflineModeManager(self)
        
        # 9. 初始化下载管理器 - 放在最后，因为它可能依赖于其他管理器
        self.download_manager = DownloadManager(self)
        
        # 10. 初始化功能处理程序
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
            game_version: 游戏版本
            
        Returns:
            DownloadThread: 下载线程实例
        """
        return DownloadThread(url, _7z_path, game_version, self)
        
    def create_progress_window(self):
        """创建进度窗口
        
        Returns:
            QDialog: 进度窗口实例
        """
        progress_window = QDialog(self)
        progress_window.setWindowTitle(f"下载进度 - {APP_NAME}")
        progress_window.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        # 添加进度条
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        layout.addWidget(progress_bar)
        
        # 添加标签
        status_label = QLabel("准备下载...")
        layout.addWidget(status_label)
        
        progress_window.setLayout(layout)
        progress_window.progress_bar = progress_bar
        progress_window.status_label = status_label
        
        return progress_window
        
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
        
    def show_result(self):
        """显示安装结果，调用patch_manager的show_result方法"""
        self.patch_manager.show_result()
        
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
                
                # 显示文件检验窗口
                self.hash_msg_box = self.hash_manager.hash_pop_window(check_type="pre", is_offline=True)
                
                # 获取安装路径
                install_paths = self.download_manager.get_install_paths()
                
                # 创建并启动哈希线程进行预检查
                self.hash_thread = self.patch_detector.create_hash_thread("pre", install_paths)
                self.hash_thread.pre_finished.connect(
                    lambda updated_status: self.patch_detector.on_offline_pre_hash_finished(updated_status, game_dirs)
                )
                self.hash_thread.start()
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

    # 移除on_offline_pre_hash_finished方法

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
                
                # 记录日志
                found_patches = list(self.offline_mode_manager.offline_patches.keys())
                logger.debug(f"DEBUG: 已自动切换到离线模式，找到离线补丁文件: {found_patches}")
                logger.info(f"发现离线补丁文件: {found_patches}，将自动切换到离线模式")
                logger.debug(f"DEBUG: 离线模式下启用开始安装按钮")
                
                # 显示提示弹窗
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    f"离线模式提示 - {APP_NAME}",
                    f"已找到本地补丁，将主动转为离线模式。\n\n检测到的补丁文件: {', '.join(found_patches)}"
                )
                
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



 