import os
import sys
import shutil
import json
import webbrowser

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox

from ui.Ui_install import Ui_MainWindows
from data.config import (
    APP_NAME, PLUGIN, GAME_INFO, BLOCK_SIZE,
    PLUGIN_HASH, UA, CONFIG_URL, LOG_FILE
)
from utils import (
    load_config, save_config, HashManager, AdminPrivileges, msgbox_frame
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
        
        # 初始化UI (从Ui_install.py导入)
        self.ui = Ui_MainWindows()
        self.ui.setupUi(self)
        
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
        self.ui.start_install_btn.clicked.connect(self.download_manager.file_dialog)
        self.ui.exit_btn.clicked.connect(self.shutdown_app)
        
        # 根据初始配置决定是否开启Debug模式
        if hasattr(self.ui_manager, 'debug_action') and self.ui_manager.debug_action:
            if self.ui_manager.debug_action.isChecked():
                self.debug_manager.start_logging()
        
        # 在窗口显示前设置初始状态
        self.animator.initialize()
        
        # 窗口显示后延迟100ms启动动画
        QTimer.singleShot(100, self.start_animations)
    
    def start_animations(self):
        """开始启动动画"""
        # 不再禁用退出按钮的交互性，只通过样式表控制外观
        # 但仍然需要跟踪动画状态，防止用户在动画播放过程中退出
        self.animation_in_progress = True
        
        # 按钮容器初始是隐藏的，无需在这里禁用
        # 但确保开始安装按钮仍然处于禁用状态
        self.ui.start_install_btn.setEnabled(False)
        
        self.animator.animation_finished.connect(self.on_animations_finished)
        self.animator.start_animations()
        self.fetch_cloud_config()

    def on_animations_finished(self):
        """动画完成后启用按钮"""
        self.animation_in_progress = False
        
        # 只有在配置有效时才启用开始安装按钮
        if self.config_valid:
            self.ui.start_install_btn.setEnabled(True)
        else:
            self.ui.start_install_btn.setEnabled(False)

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
        if error_message:
            # 标记配置无效
            self.config_valid = False
            
            if error_message == "update_required":
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
                # 显示通用错误消息，只在debug模式下显示详细错误
                debug_mode = self.ui_manager.debug_action.isChecked() if self.ui_manager.debug_action else False
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
                self.ui.start_install_btn.setEnabled(False)
        else:
            self.cloud_config = data
            # 标记配置有效
            self.config_valid = True
            
            debug_mode = self.ui_manager.debug_action.isChecked() if self.ui_manager.debug_action else False
            if debug_mode:
                print("--- Cloud config fetched successfully ---")
                print(json.dumps(data, indent=2))
            # 确保按钮在成功获取配置时启用
            self.ui.start_install_btn.setEnabled(True)

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
        self.ui.start_install_btn.setEnabled(True)
        
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

 