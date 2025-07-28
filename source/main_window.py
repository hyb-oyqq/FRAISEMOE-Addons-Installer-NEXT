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
    MultiStageAnimations, UIManager, DownloadManager, DebugManager
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
        
        # 窗口比例 (16:9)
        self.aspect_ratio = 16 / 9
        
        # 拖动窗口相关变量
        self._drag_position = QPoint()
        self._is_dragging = False
        
        # 初始化UI (从Ui_install.py导入)
        self.ui = Ui_MainWindows()
        self.ui.setupUi(self)
        
        # 设置圆角窗口
        self.setRoundedCorners()
        
        # 初始化配置
        self.config = load_config()
        
        # 初始化状态变量
        self.cloud_config = None
        self.config_valid = False  # 添加配置有效标志
        self.installed_status = {f"NEKOPARA Vol.{i}": False for i in range(1, 5)}
        self.installed_status["NEKOPARA After"] = False  # 添加After的状态
        self.hash_msg_box = None
        self.progress_window = None
        
        # 初始化工具类
        self.hash_manager = HashManager(BLOCK_SIZE)
        self.admin_privileges = AdminPrivileges()
        
        # 初始化管理器
        self.animator = MultiStageAnimations(self.ui, self)
        self.ui_manager = UIManager(self)
        
        # 首先设置UI - 确保debug_action已初始化
        self.ui_manager.setup_ui()
        
        self.debug_manager = DebugManager(self)
        self.download_manager = DownloadManager(self)
        
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
    
    def setRoundedCorners(self):
        """设置窗口圆角"""
        # 实现圆角窗口
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 20, 20)
        mask = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(mask)
        
        # 更新resize事件时更新圆角
        self.updateRoundedCorners = True
    
    # 添加鼠标事件处理，实现窗口拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 只有当鼠标在标题栏区域时才可以拖动
            if hasattr(self.ui, 'title_bar') and self.ui.title_bar.geometry().contains(event.position().toPoint()):
                self._is_dragging = True
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._is_dragging:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
    
    def resizeEvent(self, event):
        """当窗口大小改变时更新圆角和维持纵横比"""
        # 计算基于当前宽度的合适高度，以维持16:9比例
        new_width = event.size().width()
        new_height = int(new_width / self.aspect_ratio)
        
        if new_height != event.size().height():
            # 阻止变形，保持比例
            self.resize(new_width, new_height)
        
        # 更新主容器大小
        if hasattr(self.ui, 'main_container'):
            self.ui.main_container.setGeometry(0, 0, new_width, new_height)
            
        # 更新内容容器大小    
        if hasattr(self.ui, 'content_container'):
            self.ui.content_container.setGeometry(0, 0, new_width, new_height)
            
        # 更新标题栏宽度和高度
        if hasattr(self.ui, 'title_bar'):
            self.ui.title_bar.setGeometry(0, 0, new_width, 35)
        
        # 更新菜单区域
        if hasattr(self.ui, 'menu_area'):
            self.ui.menu_area.setGeometry(0, 35, new_width, 30)
            
        # 更新内容区域大小
        if hasattr(self.ui, 'inner_content'):
            self.ui.inner_content.setGeometry(0, 65, new_width, new_height - 65)
            
        # 更新背景图大小 - 使用setScaledContents简化处理
        if hasattr(self.ui, 'Mainbg'):
            self.ui.Mainbg.setGeometry(0, 0, new_width, new_height - 65)
            # 使用setScaledContents=True，不需要手动缩放
            
        if hasattr(self.ui, 'loadbg'):
            self.ui.loadbg.setGeometry(0, 0, new_width, new_height - 65)
            
        # 调整按钮位置 - 固定在右侧
        right_margin = 20  # 减小右边距，使按钮更靠右
        if hasattr(self.ui, 'button_container'):
            btn_width = 211  # 扩大后的容器宽度
            btn_height = 111  # 扩大后的容器高度
            x_pos = new_width - btn_width - right_margin
            y_pos = int((new_height - 65) * 0.28) - 10  # 调整为更靠上的位置
            self.ui.button_container.setGeometry(x_pos, y_pos, btn_width, btn_height)
            
        # 添加卸载补丁按钮容器的位置调整
        if hasattr(self.ui, 'uninstall_container'):
            btn_width = 211  # 扩大后的容器宽度
            btn_height = 111  # 扩大后的容器高度
            x_pos = new_width - btn_width - right_margin
            y_pos = int((new_height - 65) * 0.46) - 10  # 调整为中间位置
            self.ui.uninstall_container.setGeometry(x_pos, y_pos, btn_width, btn_height)
            
        if hasattr(self.ui, 'exit_container'):
            btn_width = 211  # 扩大后的容器宽度
            btn_height = 111  # 扩大后的容器高度
            x_pos = new_width - btn_width - right_margin
            y_pos = int((new_height - 65) * 0.64) - 10  # 调整为更靠下的位置
            self.ui.exit_container.setGeometry(x_pos, y_pos, btn_width, btn_height)
            
        # 更新圆角
        if hasattr(self, 'updateRoundedCorners') and self.updateRoundedCorners:
            path = QPainterPath()
            path.addRoundedRect(self.rect(), 20, 20)
            mask = QRegion(path.toFillPolygon().toPolygon())
            self.setMask(mask)
            
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
            
    def set_start_button_enabled(self, enabled):
        """设置开始安装按钮的启用状态和视觉效果
        
        Args:
            enabled: 是否启用按钮
        """
        self.ui.start_install_btn.setEnabled(True)  # 始终启用按钮，以便捕获点击事件
        
        # 根据状态修改文本内容，但不再修改颜色样式
        if enabled:
            self.ui.start_install_text.setText("开始安装")
        else:
            self.ui.start_install_text.setText("!无法安装!")
            
        # 记录当前按钮状态，用于点击事件处理
        self.install_button_enabled = enabled

    def fetch_cloud_config(self):
        """获取云端配置"""
        headers = {"User-Agent": UA}
        debug_mode = self.ui_manager.debug_action.isChecked() if self.ui_manager.debug_action else False
        self.config_fetch_thread = ConfigFetchThread(CONFIG_URL, headers, debug_mode, self)
        self.config_fetch_thread.finished.connect(self.on_config_fetched)
        self.config_fetch_thread.start()

    def on_config_fetched(self, data, error_message):
        """云端配置获取完成的回调处理
        
        Args:
            data: 获取到的配置数据
            error_message: 错误信息，如果有
        """
        # 定义debug_mode变量在方法开头
        debug_mode = self.ui_manager.debug_action.isChecked() if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action else False
        
        if error_message:
            # 标记配置无效
            self.config_valid = False
            
            # 记录错误信息，用于按钮点击时显示
            if error_message == "update_required":
                self.last_error_message = "update_required"
                msg_box = msgbox_frame(
                    f"更新提示 - {APP_NAME}",
                    "\n当前版本过低，请及时更新。\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                # 在浏览器中打开项目主页
                webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/")
                # 强制关闭程序
                self.shutdown_app(force_exit=True)
                return
            elif "missing_keys" in error_message:
                self.last_error_message = "missing_keys"
                missing_versions = error_message.split(":")[1]
                msg_box = msgbox_frame(
                    f"配置缺失 - {APP_NAME}",
                    f'\n云端缺失下载链接，可能云服务器正在维护，不影响其他版本下载。\n当前缺失版本:"{missing_versions}"\n',
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                # 对于部分缺失，仍然允许使用，因为可能只影响部分游戏版本
                self.config_valid = True
            else:
                # 设置网络错误标记
                self.last_error_message = "network_error"
                
                # 显示通用错误消息，只在debug模式下显示详细错误
                error_msg = "访问云端配置失败，请检查网络状况或稍后再试。"
                if debug_mode and "详细错误:" in error_message:
                    msg_box = msgbox_frame(
                        f"错误 - {APP_NAME}",
                        f"\n{error_message}\n",
                        QMessageBox.StandardButton.Ok,
                    )
                else:
                    msg_box = msgbox_frame(
                        f"错误 - {APP_NAME}",
                        f"\n{error_msg}\n",
                        QMessageBox.StandardButton.Ok,
                    )
                msg_box.exec()
                # 在无法连接到云端时禁用开始安装按钮
                self.set_start_button_enabled(False)
        else:
            self.cloud_config = data
            # 标记配置有效
            self.config_valid = True
            # 清除错误信息
            self.last_error_message = ""
            
            if debug_mode:
                print("--- Cloud config fetched successfully ---")
                print(json.dumps(data, indent=2))
            # 确保按钮在成功获取配置时启用
            self.set_start_button_enabled(True)

    def toggle_debug_mode(self, checked):
        """切换调试模式
        
        Args:
            checked: 是否启用调试模式
        """
        self.debug_manager.toggle_debug_mode(checked)
    
    def save_config(self, config):
        """保存配置的便捷方法"""
        save_config(config)
        
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
        
        debug_mode = self.ui_manager.debug_action.isChecked() if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action else False
        
        # 提示用户选择目录
        file_dialog_info = "选择游戏上级目录" if debug_mode else "选择游戏目录"
        selected_folder = QFileDialog.getExistingDirectory(self, file_dialog_info, "")
        
        if not selected_folder or selected_folder == "":
            return  # 用户取消了选择
        
        if debug_mode:
            print(f"DEBUG: 卸载功能 - 用户选择了目录: {selected_folder}")
        
        # 首先尝试将选择的目录视为上级目录，使用增强的目录识别功能
        game_dirs = self.identify_game_directories_improved(selected_folder)
        
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
                            success_count = 0
                            fail_count = 0
                            for version, path in game_dirs.items():
                                try:
                                    if self.uninstall_patch(path, version):
                                        success_count += 1
                                    else:
                                        fail_count += 1
                                except Exception as e:
                                    if debug_mode:
                                        print(f"DEBUG: 卸载 {version} 时出错: {str(e)}")
                                    fail_count += 1
                            
                            # 显示批量卸载结果
                            QMessageBox.information(
                                self,
                                f"批量卸载完成 - {APP_NAME}",
                                f"\n批量卸载完成！\n成功: {success_count} 个\n失败: {fail_count} 个\n",
                                QMessageBox.StandardButton.Ok,
                            )
                    else:
                        # 卸载选中的单个游戏
                        game_version = selected_game
                        game_dir = game_dirs[game_version]
                        self._confirm_and_uninstall(game_dir, game_version)
        else:
            # 未找到游戏目录，尝试将选择的目录作为游戏目录
            if debug_mode:
                print(f"DEBUG: 卸载功能 - 未在上级目录找到游戏，尝试将选择的目录视为游戏目录")
                
            game_version = self.identify_game_version(selected_folder)
            
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
        debug_mode = self.ui_manager.debug_action.isChecked() if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action else False
        
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
        self.uninstall_patch(game_dir, game_version)
        
    def identify_game_version(self, game_dir):
        """识别游戏版本
        
        Args:
            game_dir: 游戏目录路径
            
        Returns:
            str: 游戏版本名称，如果不是有效的游戏目录则返回None
        """
        import os
        import re
        
        # 调试模式
        debug_mode = self.ui_manager.debug_action.isChecked() if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action else False
        
        if debug_mode:
            print(f"DEBUG: 尝试识别游戏版本: {game_dir}")
            
        # 先通过目录名称进行初步推测（这将作为递归搜索的提示）
        dir_name = os.path.basename(game_dir).lower()
        potential_version = None
        vol_num = None
        
        # 提取卷号或判断是否是After
        if "vol" in dir_name or "vol." in dir_name:
            vol_match = re.search(r"vol(?:\.|\s*)?(\d+)", dir_name)
            if vol_match:
                vol_num = vol_match.group(1)
                potential_version = f"NEKOPARA Vol.{vol_num}"
                if debug_mode:
                    print(f"DEBUG: 从目录名推测游戏版本: {potential_version}, 卷号: {vol_num}")
        elif "after" in dir_name:
            potential_version = "NEKOPARA After"
            if debug_mode:
                print(f"DEBUG: 从目录名推测游戏版本: NEKOPARA After")
        
        # 检查是否为NEKOPARA游戏目录
        # 通过检查游戏可执行文件来识别游戏版本
        for game_version, info in GAME_INFO.items():
            # 尝试多种可能的可执行文件名变体
            exe_variants = [
                info["exe"],                         # 标准文件名
                info["exe"] + ".nocrack",            # Steam加密版本
                info["exe"].replace(".exe", ""),     # 无扩展名版本
                info["exe"].replace("NEKOPARA", "nekopara").lower(),  # 全小写变体
                info["exe"].lower(),                 # 小写变体
                info["exe"].lower() + ".nocrack",    # 小写变体的Steam加密版本
            ]
            
            # 对于Vol.3可能有特殊名称
            if "Vol.3" in game_version:
                # 增加可能的卷3特定的变体
                exe_variants.extend([
                    "NEKOPARAVol3.exe", 
                    "NEKOPARAVol3.exe.nocrack",
                    "nekoparavol3.exe",
                    "nekoparavol3.exe.nocrack",
                    "nekopara_vol3.exe",
                    "nekopara_vol3.exe.nocrack",
                    "vol3.exe",
                    "vol3.exe.nocrack"
                ])
            
            for exe_variant in exe_variants:
                exe_path = os.path.join(game_dir, exe_variant)
                if os.path.exists(exe_path):
                    if debug_mode:
                        print(f"DEBUG: 通过可执行文件确认游戏版本: {game_version}, 文件: {exe_variant}")
                    return game_version
        
        # 如果没有直接匹配，尝试递归搜索
        if potential_version:
            # 从预测的版本中获取卷号或确认是否是After
            is_after = "After" in potential_version
            if not vol_num and not is_after:
                vol_match = re.search(r"Vol\.(\d+)", potential_version)
                if vol_match:
                    vol_num = vol_match.group(1)
            
            # 递归搜索可执行文件
            for root, dirs, files in os.walk(game_dir):
                for file in files:
                    file_lower = file.lower()
                    if file.endswith('.exe') or file.endswith('.exe.nocrack'):
                        # 检查文件名中是否包含卷号或关键词
                        if ((vol_num and (f"vol{vol_num}" in file_lower or 
                                         f"vol.{vol_num}" in file_lower or 
                                         f"vol {vol_num}" in file_lower)) or
                            (is_after and "after" in file_lower)):
                            if debug_mode:
                                print(f"DEBUG: 通过递归搜索确认游戏版本: {potential_version}, 文件: {file}")
                            return potential_version
        
        # 如果仍然没有找到，基于目录名的推测返回结果
        if potential_version:
            if debug_mode:
                print(f"DEBUG: 基于目录名返回推测的游戏版本: {potential_version}")
            return potential_version
            
        if debug_mode:
            print(f"DEBUG: 无法识别游戏版本: {game_dir}")
            
        return None
        
    def identify_game_directories_improved(self, selected_folder):
        """改进的游戏目录识别，支持大小写不敏感和特殊字符处理
        
        Args:
            selected_folder: 选择的上级目录
            
        Returns:
            dict: 游戏版本到游戏目录的映射
        """
        import os
        import re
        
        # 添加debug日志
        debug_mode = self.ui_manager.debug_action.isChecked() if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action else False
        
        if debug_mode:
            print(f"--- 开始识别目录: {selected_folder} ---")
            
        game_paths = {}
        
        # 获取上级目录中的所有文件夹
        try:
            all_dirs = [d for d in os.listdir(selected_folder) if os.path.isdir(os.path.join(selected_folder, d))]
            if debug_mode:
                print(f"DEBUG: 找到以下子目录: {all_dirs}")
        except Exception as e:
            if debug_mode:
                print(f"DEBUG: 无法读取目录 {selected_folder}: {str(e)}")
            return {}
        
        for game, info in GAME_INFO.items():
            expected_dir = info["install_path"].split("/")[0]  # 例如 "NEKOPARA Vol. 1"
            expected_exe = info["exe"]  # 标准可执行文件名
            
            if debug_mode:
                print(f"DEBUG: 搜索游戏 {game}, 预期目录: {expected_dir}, 预期可执行文件: {expected_exe}")
            
            # 尝试不同的匹配方法
            found_dir = None
            
            # 1. 精确匹配
            if expected_dir in all_dirs:
                found_dir = expected_dir
                if debug_mode:
                    print(f"DEBUG: 精确匹配成功: {expected_dir}")
            
            # 2. 大小写不敏感匹配
            if not found_dir:
                for dir_name in all_dirs:
                    if expected_dir.lower() == dir_name.lower():
                        found_dir = dir_name
                        if debug_mode:
                            print(f"DEBUG: 大小写不敏感匹配成功: {dir_name}")
                        break
            
            # 3. 更模糊的匹配（允许特殊字符差异）
            if not found_dir:
                # 准备用于模糊匹配的正则表达式模式
                # 替换空格为可选空格或连字符，替换点为可选点
                pattern_text = expected_dir.replace(" ", "[ -]?").replace(".", "\\.?")
                pattern = re.compile(f"^{pattern_text}$", re.IGNORECASE)
                
                for dir_name in all_dirs:
                    if pattern.match(dir_name):
                        found_dir = dir_name
                        if debug_mode:
                            print(f"DEBUG: 模糊匹配成功: {dir_name} 匹配模式 {pattern_text}")
                        break
            
            # 4. 如果还是没找到，尝试更宽松的匹配
            if not found_dir:
                vol_match = re.search(r"vol(?:\.|\s*)?(\d+)", expected_dir, re.IGNORECASE)
                vol_num = None
                if vol_match:
                    vol_num = vol_match.group(1)
                    if debug_mode:
                        print(f"DEBUG: 提取卷号: {vol_num}")
                
                is_after = "after" in expected_dir.lower()
                
                for dir_name in all_dirs:
                    dir_lower = dir_name.lower()
                    
                    # 对于After特殊处理
                    if is_after and "after" in dir_lower:
                        found_dir = dir_name
                        if debug_mode:
                            print(f"DEBUG: After特殊匹配成功: {dir_name}")
                        break
                        
                    # 对于Vol特殊处理
                    if vol_num:
                        # 查找目录名中的卷号
                        dir_vol_match = re.search(r"vol(?:\.|\s*)?(\d+)", dir_lower)
                        if dir_vol_match and dir_vol_match.group(1) == vol_num:
                            found_dir = dir_name
                            if debug_mode:
                                print(f"DEBUG: 卷号匹配成功: {dir_name} 卷号 {vol_num}")
                            break
            
            # 如果找到匹配的目录，验证exe文件是否存在
            if found_dir:
                potential_path = os.path.join(selected_folder, found_dir)
                
                # 尝试多种可能的可执行文件名变体
                # 包括Steam加密版本和其他可能的变体
                exe_variants = [
                    expected_exe,                    # 标准文件名
                    expected_exe + ".nocrack",       # Steam加密版本
                    expected_exe.replace(".exe", ""),# 无扩展名版本
                    # Vol.3的特殊变体，因为它的文件名可能不一样
                    expected_exe.replace("NEKOPARA", "nekopara").lower(),  # 全小写变体
                    expected_exe.lower(),            # 小写变体
                    expected_exe.lower() + ".nocrack", # 小写变体的Steam加密版本
                ]
                
                # 对于Vol.3可能有特殊名称
                if "Vol.3" in game:
                    # 增加可能的卷3特定的变体
                    exe_variants.extend([
                        "NEKOPARAVol3.exe", 
                        "NEKOPARAVol3.exe.nocrack",
                        "nekoparavol3.exe",
                        "nekoparavol3.exe.nocrack",
                        "nekopara_vol3.exe",
                        "nekopara_vol3.exe.nocrack",
                        "vol3.exe",
                        "vol3.exe.nocrack"
                    ])
                
                exe_exists = False
                found_exe = None
                
                # 尝试所有可能的变体
                for exe_variant in exe_variants:
                    exe_path = os.path.join(potential_path, exe_variant)
                    if os.path.exists(exe_path):
                        exe_exists = True
                        found_exe = exe_variant
                        if debug_mode:
                            print(f"DEBUG: 验证成功，找到游戏可执行文件: {exe_variant}")
                        break
                
                # 如果没有直接找到，尝试递归搜索当前目录下的所有可执行文件
                if not exe_exists:
                    # 遍历当前目录下的所有文件和文件夹
                    for root, dirs, files in os.walk(potential_path):
                        for file in files:
                            file_lower = file.lower()
                            # 检查是否是游戏可执行文件（根据关键字）
                            if file.endswith('.exe') or file.endswith('.exe.nocrack'):
                                # 检查文件名中是否包含卷号或关键词
                                if (f"vol{vol_num}" in file_lower or 
                                    f"vol.{vol_num}" in file_lower or 
                                    f"vol {vol_num}" in file_lower or
                                    (is_after and "after" in file_lower)):
                                    exe_path = os.path.join(root, file)
                                    exe_exists = True
                                    found_exe = os.path.relpath(exe_path, potential_path)
                                    if debug_mode:
                                        print(f"DEBUG: 通过递归搜索找到游戏可执行文件: {found_exe}")
                                    break
                        if exe_exists:
                            break
                
                # 如果找到了可执行文件，将该目录添加到游戏目录列表
                if exe_exists:
                    game_paths[game] = potential_path
                    if debug_mode:
                        print(f"DEBUG: 验证成功，将 {potential_path} 添加为 {game} 的目录")
                else:
                    if debug_mode:
                        print(f"DEBUG: 未找到任何可执行文件变体，游戏 {game} 在 {potential_path} 未找到")
        
        if debug_mode:
            print(f"DEBUG: 最终识别的游戏目录: {game_paths}")
            print(f"--- 目录识别结束 ---")
            
        return game_paths
    
    def uninstall_patch(self, game_dir, game_version):
        """卸载补丁
        
        Args:
            game_dir: 游戏目录路径
            game_version: 游戏版本
            
        Returns:
            bool: 卸载成功返回True，失败返回False
        """
        import os
        import shutil
        
        debug_mode = self.ui_manager.debug_action.isChecked() if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action else False
        
        if game_version not in GAME_INFO:
            QMessageBox.critical(
                self,
                f"错误 - {APP_NAME}",
                f"\n无法识别游戏版本: {game_version}\n",
                QMessageBox.StandardButton.Ok,
            )
            return False
        
        if debug_mode:
            print(f"DEBUG: 开始卸载 {game_version} 补丁，目录: {game_dir}")
            
        try:
            files_removed = 0
            
            # 获取可能的补丁文件路径
            install_path_base = os.path.basename(GAME_INFO[game_version]["install_path"])
            patch_file_path = os.path.join(game_dir, install_path_base)
            
            # 尝试查找补丁文件，支持不同大小写
            patch_files_to_check = [
                patch_file_path,
                patch_file_path.lower(),
                patch_file_path.upper(),
                patch_file_path.replace("_", ""),
                patch_file_path.replace("_", "-"),
            ]
            
            # 查找并删除补丁文件
            patch_file_found = False
            for patch_path in patch_files_to_check:
                if os.path.exists(patch_path):
                    patch_file_found = True
                    os.remove(patch_path)
                    files_removed += 1
                    if debug_mode:
                        print(f"DEBUG: 已删除补丁文件: {patch_path}")
            
            if not patch_file_found and debug_mode:
                print(f"DEBUG: 未找到补丁文件，检查了以下路径: {patch_files_to_check}")
                
            # 检查是否有额外的签名文件 (.sig)
            if game_version == "NEKOPARA After":
                for patch_path in patch_files_to_check:
                    sig_file_path = f"{patch_path}.sig"
                    if os.path.exists(sig_file_path):
                        os.remove(sig_file_path)
                        files_removed += 1
                        if debug_mode:
                            print(f"DEBUG: 已删除签名文件: {sig_file_path}")
            
            # 删除patch文件夹
            patch_folders_to_check = [
                os.path.join(game_dir, "patch"),
                os.path.join(game_dir, "Patch"),
                os.path.join(game_dir, "PATCH"),
            ]
            
            for patch_folder in patch_folders_to_check:
                if os.path.exists(patch_folder):
                    shutil.rmtree(patch_folder)
                    files_removed += 1
                    if debug_mode:
                        print(f"DEBUG: 已删除补丁文件夹: {patch_folder}")
            
            # 删除game/patch文件夹
            game_folders = ["game", "Game", "GAME"]
            patch_folders = ["patch", "Patch", "PATCH"]
            
            for game_folder in game_folders:
                for patch_folder in patch_folders:
                    game_patch_folder = os.path.join(game_dir, game_folder, patch_folder)
                    if os.path.exists(game_patch_folder):
                        shutil.rmtree(game_patch_folder)
                        files_removed += 1
                        if debug_mode:
                            print(f"DEBUG: 已删除game/patch文件夹: {game_patch_folder}")
            
            # 删除配置文件
            config_files = ["config.json", "Config.json", "CONFIG.JSON"]
            script_files = ["scripts.json", "Scripts.json", "SCRIPTS.JSON"]
            
            for game_folder in game_folders:
                game_path = os.path.join(game_dir, game_folder)
                if os.path.exists(game_path):
                    # 删除配置文件
                    for config_file in config_files:
                        config_path = os.path.join(game_path, config_file)
                        if os.path.exists(config_path):
                            os.remove(config_path)
                            files_removed += 1
                            if debug_mode:
                                print(f"DEBUG: 已删除配置文件: {config_path}")
                    
                    # 删除脚本文件
                    for script_file in script_files:
                        script_path = os.path.join(game_path, script_file)
                        if os.path.exists(script_path):
                            os.remove(script_path)
                            files_removed += 1
                            if debug_mode:
                                print(f"DEBUG: 已删除脚本文件: {script_path}")
            
            # 更新安装状态
            self.installed_status[game_version] = False
            
            # 在非批量卸载模式下显示卸载成功消息
            if game_version != "all":
                # 显示卸载成功消息
                if files_removed > 0:
                    QMessageBox.information(
                        self,
                        f"卸载完成 - {APP_NAME}",
                        f"\n{game_version} 补丁卸载成功！\n共删除 {files_removed} 个文件/文件夹。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                else:
                    QMessageBox.warning(
                        self,
                        f"警告 - {APP_NAME}",
                        f"\n未找到 {game_version} 的补丁文件，可能未安装补丁或已被移除。\n",
                        QMessageBox.StandardButton.Ok,
                    )
            
            # 卸载成功
            return True
            
        except Exception as e:
            # 在非批量卸载模式下显示卸载失败消息
            if game_version != "all":
                # 显示卸载失败消息
                error_message = f"\n卸载 {game_version} 补丁时出错：\n\n{str(e)}\n"
                if debug_mode:
                    print(f"DEBUG: 卸载错误 - {str(e)}")
                    
                QMessageBox.critical(
                    self,
                    f"卸载失败 - {APP_NAME}",
                    error_message,
                    QMessageBox.StandardButton.Ok,
                )
            
            # 卸载失败
            return False 

 