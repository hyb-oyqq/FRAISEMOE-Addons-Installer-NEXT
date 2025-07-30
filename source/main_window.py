import os
import sys
import shutil
import json
import webbrowser

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, Qt, QPoint, QRect, QSize
from PySide6.QtWidgets import QMainWindow, QMessageBox, QGraphicsOpacityEffect, QGraphicsColorizeEffect
from PySide6.QtGui import QPalette, QColor, QPainterPath, QRegion
from PySide6.QtGui import QAction # Added for menu actions

from ui.Ui_install import Ui_MainWindows
from data.config import (
    APP_NAME, PLUGIN, GAME_INFO, BLOCK_SIZE,
    PLUGIN_HASH, UA, CONFIG_URL, LOG_FILE
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
        
        # 初始化管理器
        self.animator = MultiStageAnimations(self.ui, self)
        self.ui_manager = UIManager(self)
        
        # 首先设置UI - 确保debug_action已初始化
        self.ui_manager.setup_ui()
        
        # 初始化新的管理器类
        self.window_manager = WindowManager(self)
        self.debug_manager = DebugManager(self)
        # 为debug_manager设置ui_manager引用
        self.debug_manager.set_ui_manager(self.ui_manager)
        self.config_manager = ConfigManager(APP_NAME, CONFIG_URL, UA, self.debug_manager)
        self.game_detector = GameDetector(GAME_INFO, self.debug_manager)
        self.patch_manager = PatchManager(APP_NAME, GAME_INFO, self.debug_manager)
        
        # 初始化下载管理器 - 应该放在其他管理器之后，因为它可能依赖于它们
        self.download_manager = DownloadManager(self)
        
        # 初始化状态变量
        self.cloud_config = None
        self.config_valid = False  # 添加配置有效标志
        self.patch_manager.initialize_status()
        self.installed_status = self.patch_manager.get_status()  # 获取初始化后的状态
        self.hash_msg_box = None
        self.progress_window = None
        
        # 设置关闭按钮事件连接
        if hasattr(self.ui, 'close_btn'):
            self.ui.close_btn.clicked.connect(self.close)
        
        if hasattr(self.ui, 'minimize_btn'):
            self.ui.minimize_btn.clicked.connect(self.showMinimized)
        
        # 检查管理员权限和进程
        self.admin_privileges.request_admin_privileges()
        self.admin_privileges.check_and_terminate_processes()
        
        # 备份hosts文件
        self.download_manager.hosts_manager.backup()
        
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
        self.ui.uninstall_btn.clicked.connect(self.handle_uninstall_button_click)  # 添加卸载补丁按钮事件连接
        self.ui.exit_btn.clicked.connect(self.shutdown_app)
        
        # 初始化按钮状态标记
        self.install_button_enabled = False
        self.last_error_message = ""
        
        # 根据初始配置决定是否开启Debug模式
        if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action:
            if self.ui_manager.debug_action.isChecked():
                self.debug_manager.start_logging()
        
        # 在窗口显示前设置初始状态
        self.animator.initialize()
        
        # 窗口显示后延迟100ms启动动画
        QTimer.singleShot(100, self.start_animations)
    
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
        
        self.animator.animation_finished.connect(self.on_animations_finished)
        self.animator.start_animations()
        self.fetch_cloud_config()

    def on_animations_finished(self):
        """动画完成后启用按钮"""
        self.animation_in_progress = False
        
        # 只有在配置有效时才启用开始安装按钮
        if self.config_valid:
            self.set_start_button_enabled(True)
        else:
            self.set_start_button_enabled(False)
            
    def set_start_button_enabled(self, enabled, installing=False):
        """设置开始安装按钮的启用状态和视觉效果
        
        Args:
            enabled: 是否启用按钮
            installing: 是否正在安装中
        """
        if installing:
            # 安装中状态 - 按钮被禁用但显示"正在安装"
            self.ui.start_install_btn.setEnabled(False)
            self.ui.start_install_text.setText("正在安装")
            self.install_button_enabled = False
        else:
            # 正常状态 - 按钮可点击，但根据enabled决定是否显示"无法安装"
            self.ui.start_install_btn.setEnabled(True)  # 始终启用按钮，以便捕获点击事件
            
            # 根据状态修改文本内容
            if enabled:
                self.ui.start_install_text.setText("开始安装")
            else:
                self.ui.start_install_text.setText("!无法安装!")
                
            # 记录当前按钮状态，用于点击事件处理
            self.install_button_enabled = enabled

    def fetch_cloud_config(self):
        """获取云端配置"""
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
                
                # 检查是否有后续操作
                if "then" in result and result["then"] == "exit":
                    # 强制关闭程序
                    self.shutdown_app(force_exit=True)
            elif result["action"] == "enable_button":
                # 启用开始安装按钮
                self.set_start_button_enabled(True)
        
        # 同步状态
        self.cloud_config = self.config_manager.get_cloud_config()
        self.config_valid = self.config_manager.is_config_valid()
        self.last_error_message = self.config_manager.get_last_error()

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
        # 禁用退出按钮
        self.ui.exit_btn.setEnabled(False)
        
        self.hash_msg_box = self.hash_manager.hash_pop_window(check_type="after")

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
            game = result.get("game", "未知游戏")
            message = result.get("message", "发生未知错误。")
            msg_box = msgbox_frame(
                f"文件校验失败 - {APP_NAME}",
                message,
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()

        # 重新启用退出按钮和开始安装按钮
        self.ui.exit_btn.setEnabled(True)
        self.set_start_button_enabled(True)
        
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
            path = install_paths.get(game_version, "")
            
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
        
        # 总数统计
        total_installed = len(installed_versions)
        total_skipped = len(skipped_versions)
        total_failed = len(failed_versions)
        
        result_text += f"安装成功：{total_installed} 个  已跳过：{total_skipped} 个  安装失败：{total_failed} 个\n\n"
        
        # 详细列表
        if installed_versions:
            result_text += f"【成功安装】:\n{chr(10).join(installed_versions)}\n\n"
            
        if skipped_versions:
            result_text += f"【已安装跳过】:\n{chr(10).join(skipped_versions)}\n\n"
            
        if failed_versions:
            result_text += f"【安装失败】:\n{chr(10).join(failed_versions)}\n\n"
            
        if not_found_versions and (installed_versions or failed_versions):
            # 只有当有其他版本存在时，才显示未找到的版本
            result_text += f"【未在指定目录找到】:\n{chr(10).join(not_found_versions)}\n"
        
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
                
        # 恢复hosts文件
        self.download_manager.hosts_manager.restore()
        
        # 额外检查并清理hosts文件中的残留记录
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
        if not self.install_button_enabled:
            # 按钮处于"无法安装"状态
            if self.last_error_message == "update_required":
                msg_box = msgbox_frame(
                    f"更新提示 - {APP_NAME}",
                    "\n当前版本过低，请及时更新。\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
            elif self.last_error_message == "directory_not_found":
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
            self.download_manager.file_dialog()

    def handle_uninstall_button_click(self):
        """处理卸载补丁按钮点击事件
        打开文件选择对话框选择游戏目录，然后卸载对应游戏的补丁
        """
        # 获取游戏目录
        from PySide6.QtWidgets import QFileDialog
        
        debug_mode = self.debug_manager._is_debug_mode()
        
        # 提示用户选择目录
        file_dialog_info = "选择游戏上级目录" if debug_mode else "选择游戏目录"
        selected_folder = QFileDialog.getExistingDirectory(self, file_dialog_info, "")
        
        if not selected_folder or selected_folder == "":
            return  # 用户取消了选择
        
        if debug_mode:
            print(f"DEBUG: 卸载功能 - 用户选择了目录: {selected_folder}")
        
        # 首先尝试将选择的目录视为上级目录，使用增强的目录识别功能
        game_dirs = self.game_detector.identify_game_directories_improved(selected_folder)
        
        if game_dirs and len(game_dirs) > 0:
            # 找到了游戏目录，显示选择对话框
            if debug_mode:
                print(f"DEBUG: 卸载功能 - 在上级目录中找到以下游戏: {list(game_dirs.keys())}")
            
            # 如果只有一个游戏，直接选择它
            if len(game_dirs) == 1:
                game_version = list(game_dirs.keys())[0]
                game_dir = game_dirs[game_version]
                self._confirm_and_uninstall(game_dir, game_version)
            else:
                # 有多个游戏，让用户选择
                from PySide6.QtWidgets import QInputDialog
                game_versions = list(game_dirs.keys())
                # 添加"全部卸载"选项
                game_versions.append("全部卸载")
                
                selected_game, ok = QInputDialog.getItem(
                    self, "选择游戏", "选择要卸载补丁的游戏:", 
                    game_versions, 0, False
                )
                
                if ok and selected_game:
                    if selected_game == "全部卸载":
                        # 卸载所有游戏补丁
                        reply = QMessageBox.question(
                            self,
                            f"确认卸载 - {APP_NAME}",
                            f"\n确定要卸载所有游戏的补丁吗？\n这将卸载以下游戏的补丁:\n{chr(10).join(list(game_dirs.keys()))}\n",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No
                        )
                        
                        if reply == QMessageBox.StandardButton.Yes:
                            # 使用批量卸载方法
                            success_count, fail_count = self.patch_manager.batch_uninstall_patches(game_dirs)
                            self.patch_manager.show_uninstall_result(success_count, fail_count)
                    else:
                        # 卸载选中的单个游戏
                        game_version = selected_game
                        game_dir = game_dirs[game_version]
                        self._confirm_and_uninstall(game_dir, game_version)
        else:
            # 未找到游戏目录，尝试将选择的目录作为游戏目录
            if debug_mode:
                print(f"DEBUG: 卸载功能 - 未在上级目录找到游戏，尝试将选择的目录视为游戏目录")
                
            game_version = self.game_detector.identify_game_version(selected_folder)
            
            if game_version:
                if debug_mode:
                    print(f"DEBUG: 卸载功能 - 识别为游戏: {game_version}")
                self._confirm_and_uninstall(selected_folder, game_version)
            else:
                # 两种方式都未识别到游戏
                if debug_mode:
                    print(f"DEBUG: 卸载功能 - 无法识别游戏")
                    
                msg_box = msgbox_frame(
                    f"错误 - {APP_NAME}",
                    "\n所选目录不是有效的NEKOPARA游戏目录。\n请选择包含游戏可执行文件的目录或其上级目录。\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
    
    def _confirm_and_uninstall(self, game_dir, game_version):
        """确认并卸载补丁
        
        Args:
            game_dir: 游戏目录
            game_version: 游戏版本
        """
        debug_mode = self.debug_manager._is_debug_mode()
        
        # 确认卸载
        reply = QMessageBox.question(
            self,
            f"确认卸载 - {APP_NAME}",
            f"\n确定要卸载 {game_version} 的补丁吗？\n游戏目录: {game_dir}\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
            
        # 开始卸载补丁
        self.patch_manager.uninstall_patch(game_dir, game_version)

 