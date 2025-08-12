import os
import sys
import subprocess
import shutil
import json
import webbrowser
import traceback

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, Qt, QPoint, QRect, QSize
from PySide6.QtWidgets import QMainWindow, QMessageBox, QGraphicsOpacityEffect, QGraphicsColorizeEffect
from PySide6.QtGui import QPalette, QColor, QPainterPath, QRegion, QFont
from PySide6.QtGui import QAction

from ui.Ui_install import Ui_MainWindows
from config.config import (
    APP_NAME, PLUGIN, GAME_INFO, BLOCK_SIZE,
    PLUGIN_HASH, UA, CONFIG_URL, LOG_FILE,
    DOWNLOAD_THREADS, DEFAULT_DOWNLOAD_THREAD_LEVEL, APP_VERSION
)
from utils import (
    load_config, save_config, HashManager, AdminPrivileges, msgbox_frame, load_image_from_file
)
from workers import (
    IpOptimizerThread, 
    HashThread, ConfigFetchThread
)
from core import (
    MultiStageAnimations, UIManager, DownloadManager, DebugManager,
    WindowManager, GameDetector, PatchManager, ConfigManager, PatchDetector
)
from core.managers.ipv6_manager import IPv6Manager
from core.handlers import PatchToggleHandler, UninstallHandler
from utils.logger import setup_logger


# 初始化logger
logger = setup_logger("main_window")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self._setup_window_properties()
        self._init_ui()
        self._init_config_and_tools()
        self._init_managers()
        self._connect_signals()
        self._setup_environment()
        
        self.download_manager.hosts_manager.backup()
        self._setup_debug_mode()
        
        self.check_and_set_offline_mode()
        self.fetch_cloud_config()
        self.start_animations()
    
    def _setup_window_properties(self):
        """设置窗口的基本属性，如无边框、透明背景和大小."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1280, 720)
        self.setMinimumSize(QSize(1024, 576))
        self.setMaximumSize(QSize(1280, 720))

    def _init_ui(self):
        """初始化UI组件."""
        self.ui = Ui_MainWindows()
        self.ui.setupUi(self)

    def _init_config_and_tools(self):
        """加载配置并初始化核心工具."""
        self.config = load_config()
        self.hash_manager = HashManager(BLOCK_SIZE)
        self.admin_privileges = AdminPrivileges()
        self.patch_detector = PatchDetector(self)
        
        # 初始化状态变量
        self.cloud_config = None
        self.config_valid = False
        self.last_error_message = ""
        self.version_warning = False
        self.install_button_enabled = True
        self.progress_window = None
        self.pre_hash_thread = None
        self.hash_thread = None
        self.installed_status = {}  
        self.hash_msg_box = None    
        
        # 验证关键资源
        self._verify_resources()
        
    def _verify_resources(self):
        """验证关键资源文件是否存在，帮助调试资源加载问题"""
        from utils import resource_path
        logger.info("开始验证关键资源文件...")
        
        # 关键字体文件
        font_files = [
            os.path.join("assets", "fonts", "SmileySans-Oblique.ttf")
        ]
        
        # 关键图标文件
        icon_files = [
            os.path.join("assets", "images", "ICO", "icon.png"),
            os.path.join("assets", "images", "ICO", "icon.ico"),
            os.path.join("assets", "images", "BTN", "Button.png"),
            os.path.join("assets", "images", "BTN", "exit.bmp"),
            os.path.join("assets", "images", "BTN", "start_install.bmp")
        ]
        
        # 关键背景图片
        bg_files = [
            os.path.join("assets", "images", "BG", "bg1.jpg"),
            os.path.join("assets", "images", "BG", "bg2.jpg"),
            os.path.join("assets", "images", "BG", "bg3.jpg"),
            os.path.join("assets", "images", "BG", "bg4.jpg"),
            os.path.join("assets", "images", "BG", "menubg.jpg")
        ]
        
        # 记录缺失的资源
        missing_resources = []
        
        # 验证字体文件
        for font_file in font_files:
            path = resource_path(font_file)
            if not os.path.exists(path):
                missing_resources.append(font_file)
                logger.warning(f"缺失字体文件: {font_file}, 尝试路径: {path}")
            else:
                logger.info(f"已找到字体文件: {font_file}")
        
        # 验证图标文件
        for icon_file in icon_files:
            path = resource_path(icon_file)
            if not os.path.exists(path):
                missing_resources.append(icon_file)
                logger.warning(f"缺失图标文件: {icon_file}, 尝试路径: {path}")
            else:
                logger.info(f"已找到图标文件: {icon_file}")
                
        # 验证背景图片
        for bg_file in bg_files:
            path = resource_path(bg_file)
            if not os.path.exists(path):
                missing_resources.append(bg_file)
                logger.warning(f"缺失背景图片: {bg_file}, 尝试路径: {path}")
            else:
                logger.info(f"已找到背景图片: {bg_file}")
        
        # 如果有缺失资源，记录摘要
        if missing_resources:
            logger.error(f"总计 {len(missing_resources)} 个关键资源文件缺失!")
            # 如果在调试模式下，显示警告对话框
            if self.config.get("debug_mode", False):
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("资源加载警告")
                msg.setText("检测到缺失的关键资源文件!")
                msg.setInformativeText(f"有 {len(missing_resources)} 个资源文件未找到。\n请检查日志文件获取详细信息。")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()
        else:
            logger.info("所有关键资源文件验证通过")
            
        # 测试资源加载功能
        self._test_resource_loading()
    
    def _test_resource_loading(self):
        """测试资源加载功能，验证图片和字体是否可以正确加载"""
        logger.info("开始测试资源加载功能...")
        
        from PySide6.QtGui import QFontDatabase, QPixmap, QImage, QFont
        from utils import resource_path, load_image_from_file
        
        # 测试字体加载
        logger.info("测试字体加载...")
        font_path = resource_path(os.path.join("assets", "fonts", "SmileySans-Oblique.ttf"))
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    logger.info(f"字体加载测试成功: {font_families[0]}")
                else:
                    logger.error("字体加载测试失败: 无法获取字体族")
            else:
                logger.error(f"字体加载测试失败: 无法加载字体文件 {font_path}")
        else:
            logger.error(f"字体加载测试失败: 文件不存在 {font_path}")
        
        # 测试图片加载 - 使用QPixmap直接加载
        logger.info("测试图片加载 (QPixmap)...")
        icon_path = resource_path(os.path.join("assets", "images", "ICO", "icon.png"))
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                logger.info(f"QPixmap加载测试成功: {icon_path}, 大小: {pixmap.width()}x{pixmap.height()}")
            else:
                logger.error(f"QPixmap加载测试失败: {icon_path}")
        else:
            logger.error(f"QPixmap加载测试失败: 文件不存在 {icon_path}")
            
        # 测试图片加载 - 使用QImage加载
        logger.info("测试图片加载 (QImage)...")
        bg_path = resource_path(os.path.join("assets", "images", "BG", "bg1.jpg"))
        if os.path.exists(bg_path):
            image = QImage(bg_path)
            if not image.isNull():
                logger.info(f"QImage加载测试成功: {bg_path}, 大小: {image.width()}x{image.height()}")
            else:
                logger.error(f"QImage加载测试失败: {bg_path}")
        else:
            logger.error(f"QImage加载测试失败: 文件不存在 {bg_path}")
            
        # 测试自定义加载函数
        logger.info("测试自定义图片加载函数...")
        btn_path = resource_path(os.path.join("assets", "images", "BTN", "Button.png"))
        pixmap = load_image_from_file(btn_path)
        if not pixmap.isNull():
            logger.info(f"自定义图片加载函数测试成功: {btn_path}, 大小: {pixmap.width()}x{pixmap.height()}")
        else:
            logger.error(f"自定义图片加载函数测试失败: {btn_path}")
        
        logger.info("资源加载功能测试完成")

    def _init_managers(self):
        """初始化所有管理器."""
        self.animator = MultiStageAnimations(self.ui, self)
        self.window_manager = WindowManager(self)
        self.debug_manager = DebugManager(self)
        self.ipv6_manager = IPv6Manager(self)
        self.ui_manager = UIManager(self)
        self.debug_manager.set_ui_manager(self.ui_manager)
        self.config_manager = ConfigManager(APP_NAME, CONFIG_URL, UA, self.debug_manager)
        self.game_detector = GameDetector(GAME_INFO, self.debug_manager)
        self.patch_manager = PatchManager(APP_NAME, GAME_INFO, self.debug_manager, self)
        self.patch_manager.set_patch_detector(self.patch_detector)
        from core.managers.offline_mode_manager import OfflineModeManager
        self.offline_mode_manager = OfflineModeManager(self)
        self.download_manager = DownloadManager(self)
        self.uninstall_handler = UninstallHandler(self)
        self.patch_toggle_handler = PatchToggleHandler(self)
        
        # Load user's download thread setting
        if "download_thread_level" in self.config and self.config["download_thread_level"] in DOWNLOAD_THREADS:
            self.download_manager.download_thread_level = self.config["download_thread_level"]

    def _connect_signals(self):
        """连接UI组件的信号到相应的槽函数."""
        if hasattr(self.ui, 'close_btn'):
            self.ui.close_btn.clicked.connect(self._on_close_clicked)
        if hasattr(self.ui, 'minimize_btn'):
            self.ui.minimize_btn.clicked.connect(self._on_minimize_clicked)
        
        self.ui.start_install_btn.clicked.connect(self.handle_install_button_click)
        self.ui.uninstall_btn.clicked.connect(self.uninstall_handler.handle_uninstall_button_click)
        self.ui.toggle_patch_btn.clicked.connect(self.patch_toggle_handler.handle_toggle_patch_button_click)
        self.ui.exit_btn.clicked.connect(self.shutdown_app)

    def _setup_environment(self):
        """准备应用运行所需的环境，如创建缓存目录和检查权限."""
        if not os.path.exists(PLUGIN):
            try:
                os.makedirs(PLUGIN)
            except OSError as e:
                QtWidgets.QMessageBox.critical(self, f"错误 - {APP_NAME}", f"无法创建缓存位置: {e}")
                sys.exit(1)
        
        try:
            self.admin_privileges.request_admin_privileges()
            self.admin_privileges.check_and_terminate_processes()
        except Exception as e:
            logger.error(f"权限或进程检查失败: {e}")
            QtWidgets.QMessageBox.critical(self, f"错误 - {APP_NAME}", f"权限检查失败: {e}")
            sys.exit(1)

    def _setup_debug_mode(self):
        """根据配置设置调试模式."""
        if self.config.get("debug_mode"):
            self.debug_manager.start_logging()
            logger.info("通过配置启动调试模式")
        
        if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action and self.ui_manager.debug_action.isChecked():
            if not self.debug_manager.logger:
                self.debug_manager.start_logging()
                logger.info("通过UI启动调试模式")
        
        self.ui_manager.setup_ui()
    
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
        # 按钮状态由WindowManager统一管理
        self.ui.uninstall_btn.setEnabled(True)
        self.ui.toggle_patch_btn.setEnabled(True)
        self.ui.exit_btn.setEnabled(True)
        
        # 检查是否处于离线模式
        is_offline_mode = False
        if hasattr(self, 'offline_mode_manager'):
            is_offline_mode = self.offline_mode_manager.is_in_offline_mode()
            
        # 根据离线模式和配置状态设置按钮
        if is_offline_mode or self.config_valid:
            self.window_manager.change_window_state(self.window_manager.STATE_READY)
        else:
            self.window_manager.change_window_state(self.window_manager.STATE_ERROR)
            
    def set_start_button_enabled(self, enabled, installing=False):
        """[过渡方法] 设置按钮状态，将调用委托给WindowManager
        
        这个方法将逐步被淘汰，请使用 self.window_manager.change_window_state()
        
        Args:
            enabled: 是否启用按钮
            installing: 是否正在安装中
        """
        if installing:
            self.window_manager.change_window_state(self.window_manager.STATE_INSTALLING)
        elif enabled:
            self.window_manager.change_window_state(self.window_manager.STATE_READY)
        else:
            self.window_manager.change_window_state(self.window_manager.STATE_ERROR)

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
        
        # 先同步状态
        self.cloud_config = self.config_manager.get_cloud_config()
        self.config_valid = self.config_manager.is_config_valid()
        self.last_error_message = self.config_manager.get_last_error()
        
        # 根据返回的操作执行相应动作
        if result and "action" in result:
            if result["action"] == "exit":
                # 强制关闭程序
                self.shutdown_app(force_exit=True)
            elif result["action"] == "disable_button":
                # 禁用开始安装按钮
                self.window_manager.change_window_state(self.window_manager.STATE_ERROR)
            elif result["action"] == "enable_button":
                # 启用开始安装按钮
                self.window_manager.change_window_state(self.window_manager.STATE_READY)
                # 检查是否需要记录版本警告
                if "version_warning" in result and result["version_warning"]:
                    self.version_warning = True
                else:
                    self.version_warning = False
        
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
        """关闭应用程序"""
        logger = setup_logger("main_window")
        logger.info("用户点击退出按钮")
        logger.debug("开始关闭应用程序")
        
        if hasattr(self, 'animation_in_progress') and self.animation_in_progress and not force_exit:
            if event:
                event.ignore()
            return

        threads_to_stop = {
            'pre_hash': getattr(self, 'pre_hash_thread', None),
            'hash': getattr(self, 'hash_thread', None),
            'offline_hash': getattr(self.offline_mode_manager, 'hash_thread', None),
            'extraction': getattr(self.offline_mode_manager, 'extraction_thread', None),
            'config_fetch': getattr(self.config_manager, 'config_fetch_thread', None),
            'game_detector': getattr(self.game_detector, 'detection_thread', None),
            'patch_check': getattr(self.patch_detector, 'patch_check_thread', None)
        }
        
        # Add current download thread if it's running
        if hasattr(self.download_manager, 'current_download_thread') and self.download_manager.current_download_thread:
            threads_to_stop['download'] = self.download_manager.current_download_thread

        self.download_manager.graceful_stop_threads(threads_to_stop)


        self.debug_manager.stop_logging()

        if not force_exit:
            reply = QMessageBox.question(
                self, f"确认退出 - {APP_NAME}", "\n确定要退出吗？\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                if event:
                    event.ignore()
                return
            
            # 用户确认退出后，再执行hosts相关操作
            self.download_manager.hosts_manager.restore()
            self.download_manager.hosts_manager.check_and_clean_all_entries()
        else:
            # 强制退出时，也需执行hosts相关操作
            self.download_manager.hosts_manager.restore()
            self.download_manager.hosts_manager.check_and_clean_all_entries()

        if event:
            event.accept()
        else:
            sys.exit(0)

    def handle_install_button_click(self):
        """处理安装按钮点击事件
        根据按钮当前状态决定是显示错误还是执行安装
        """
        logger = setup_logger("main_window")
        logger.info("用户点击开始安装按钮")
        logger.debug("开始处理安装按钮点击事件")
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
            if self.offline_mode_manager.is_in_offline_mode():
                self.selected_folder = QtWidgets.QFileDialog.getExistingDirectory(
                    self, f"选择游戏所在【上级目录】 {APP_NAME}"
                )
                if not self.selected_folder:
                    QtWidgets.QMessageBox.warning(self, f"通知 - {APP_NAME}", "\n未选择任何目录,请重新选择\n")
                    return
                
                self.download_manager.selected_folder = self.selected_folder
                self.ui_manager.show_loading_dialog("正在识别游戏目录...")
                self.setEnabled(False)

                # 异步识别游戏目录
                self.game_detector.identify_game_directories_async(self.selected_folder, self.on_game_directories_identified)
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

    def on_game_directories_identified(self, game_dirs):
        self.ui_manager.hide_loading_dialog()

        if not game_dirs:
            self.setEnabled(True)
            self.window_manager.change_window_state(self.window_manager.STATE_READY)
            QtWidgets.QMessageBox.warning(
                self, 
                f"目录错误 - {APP_NAME}", 
                "\n未能识别到任何游戏目录。\n\n请确认您选择的是游戏的上级目录，并且该目录中包含NEKOPARA系列游戏文件夹。\n"
            )
            return

        self.ui_manager.show_loading_dialog("正在检查补丁状态...")
        
        install_paths = self.download_manager.get_install_paths()
        
        # 使用异步方式进行哈希预检查
        self.pre_hash_thread = self.patch_detector.create_hash_thread("pre", install_paths)
        self.pre_hash_thread.pre_finished.connect(
            lambda updated_status: self.on_pre_hash_finished(updated_status, game_dirs)
        )
        # 在线程自然结束时清理引用
        try:
            self.pre_hash_thread.finished.connect(lambda: setattr(self, 'pre_hash_thread', None))
        except Exception:
            pass
        self.pre_hash_thread.start()

    def on_pre_hash_finished(self, updated_status, game_dirs):
        self.ui_manager.hide_loading_dialog()
        self.setEnabled(True)
        self.patch_detector.on_offline_pre_hash_finished(updated_status, game_dirs)
        
    

    def check_and_set_offline_mode(self):
        """检查是否有离线补丁文件，如果有则自动启用离线模式
        
        Returns:
            bool: 是否成功切换到离线模式
        """
        try:
            # 初始化离线模式管理器
            if not hasattr(self, 'offline_mode_manager') or self.offline_mode_manager is None:
                from core.managers.offline_mode_manager import OfflineModeManager
                self.offline_mode_manager = OfflineModeManager(self)
            
            # 在调试模式下记录当前执行路径
            is_debug_mode = self.config.get('debug_mode', False) if hasattr(self, 'config') else False
            if is_debug_mode:
                import os
                import sys
                current_dir = os.getcwd()
                logger.debug(f"DEBUG: 当前工作目录: {current_dir}")
                logger.debug(f"DEBUG: 是否为打包环境: {getattr(sys, 'frozen', False)}")
                if getattr(sys, 'frozen', False):
                    logger.debug(f"DEBUG: 可执行文件路径: {sys.executable}")
                
                # 尝试列出当前目录中的文件（调试用）
                try:
                    files = os.listdir(current_dir)
                    logger.debug(f"DEBUG: 当前目录文件列表: {files}")
                    
                    # 检查上级目录
                    parent_dir = os.path.dirname(current_dir)
                    parent_files = os.listdir(parent_dir)
                    logger.debug(f"DEBUG: 上级目录 {parent_dir} 文件列表: {parent_files}")
                except Exception as e:
                    logger.debug(f"DEBUG: 列出目录文件时出错: {str(e)}")
            
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
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False

    def close_hash_msg_box(self):
        """关闭哈希校验窗口，确保在创建新窗口前关闭旧窗口"""
        if hasattr(self, 'hash_msg_box') and self.hash_msg_box:
            try:
                if self.hash_msg_box.isVisible():
                    self.hash_msg_box.close()
                    QtWidgets.QApplication.processEvents()  # 确保UI更新，窗口真正关闭
            except Exception as e:
                logger.error(f"关闭哈希校验窗口时发生错误: {e}")
            self.hash_msg_box = None

    def create_progress_window(self, title="下载进度", initial_text="准备中..."):
        """创建一个用于显示下载进度的窗口
        
        Args:
            title (str): 窗口标题，默认为"下载进度"
            initial_text (str): 初始状态文本，默认为"准备中..."
            
        Returns:
            进度窗口实例
        """
        return self.ui_manager.create_progress_window(title, initial_text)

    def create_extraction_progress_window(self):
        """创建一个用于显示解压进度的窗口
        
        Returns:
            解压进度窗口实例
        """
        return self.ui_manager.create_progress_window("解压进度", "正在准备解压...")

    def show_loading_dialog(self, message):
        """显示加载对话框
        
        Args:
            message: 要显示的消息
        """
        self.ui_manager.show_loading_dialog(message)
    
    def _on_close_clicked(self):
        """处理关闭按钮点击"""
        logger = setup_logger("main_window")
        logger.info("用户点击关闭按钮")
        self.close()
    
    def _on_minimize_clicked(self):
        """处理最小化按钮点击"""
        logger = setup_logger("main_window")
        logger.info("用户点击最小化按钮")
        self.showMinimized()
        
    def hide_loading_dialog(self):
        """隐藏加载对话框"""
        self.ui_manager.hide_loading_dialog()