import os
import requests
import json
from collections import deque
from urllib.parse import urlparse
import re

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QFont

from utils import msgbox_frame, HostsManager, resource_path
from data.config import APP_NAME, PLUGIN, GAME_INFO, UA, CONFIG_URL, DOWNLOAD_THREADS, DEFAULT_DOWNLOAD_THREAD_LEVEL
from workers import IpOptimizerThread
from core.cloudflare_optimizer import CloudflareOptimizer
from core.download_task_manager import DownloadTaskManager
from core.extraction_handler import ExtractionHandler

class DownloadManager:
    def __init__(self, main_window):
        """初始化下载管理器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
        """
        self.main_window = main_window
        self.main_window.APP_NAME = APP_NAME
        self.selected_folder = ""
        self.download_queue = deque()
        self.current_download_thread = None
        self.hosts_manager = HostsManager()
        
        self.download_thread_level = DEFAULT_DOWNLOAD_THREAD_LEVEL
        
        self.cloudflare_optimizer = CloudflareOptimizer(main_window, self.hosts_manager)
        self.download_task_manager = DownloadTaskManager(main_window, self.download_thread_level)
        self.extraction_handler = ExtractionHandler(main_window)
        
    def file_dialog(self):
        """显示文件夹选择对话框，选择游戏安装目录"""
        self.selected_folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, f"选择游戏所在【上级目录】 {APP_NAME}"
        )
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(
                self.main_window, f"通知 - {APP_NAME}", "\n未选择任何目录,请重新选择\n"
            )
            return
        
        self.main_window.ui.start_install_text.setText("正在安装")
        
        self.main_window.setEnabled(False)
        
        self.download_action()

    def get_install_paths(self):
        """获取所有游戏版本的安装路径"""
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        install_paths = {}
        
        debug_mode = self.is_debug_mode()
        
        for game, info in GAME_INFO.items():
            if game in game_dirs:
                game_dir = game_dirs[game]
                install_path = os.path.join(game_dir, os.path.basename(info["install_path"]))
                install_paths[game] = install_path
                if debug_mode:
                    print(f"DEBUG: 使用识别到的游戏目录 {game}: {game_dir}")
                    print(f"DEBUG: 安装路径设置为: {install_path}")
                    
        return install_paths

    def is_debug_mode(self):
        """检查是否处于调试模式"""
        if hasattr(self.main_window, 'ui_manager') and self.main_window.ui_manager:
            if hasattr(self.main_window.ui_manager, 'debug_action') and self.main_window.ui_manager.debug_action:
                return self.main_window.ui_manager.debug_action.isChecked()
        return False

    def get_download_url(self) -> dict:
        """获取所有游戏版本的下载链接
        
        Returns:
            dict: 包含游戏版本和下载URL的字典
        """
        try:
            if self.main_window.cloud_config:
                if self.is_debug_mode():
                    print("--- Using pre-fetched cloud config ---")
                config_data = self.main_window.cloud_config
            else:
                headers = {"User-Agent": UA}
                response = requests.get(CONFIG_URL, headers=headers, timeout=10)
                response.raise_for_status()
                config_data = response.json()

            if not config_data:
                raise ValueError("未能获取或解析配置数据")

            if self.is_debug_mode():
                print(f"DEBUG: Parsed JSON data: {json.dumps(config_data, indent=2)}")

            urls = {}
            for i in range(4):
                key = f"vol.{i+1}.data"
                if key in config_data and "url" in config_data[key]:
                    urls[f"vol{i+1}"] = config_data[key]["url"]
            
            if "after.data" in config_data and "url" in config_data["after.data"]:
                urls["after"] = config_data["after.data"]["url"]

            if len(urls) != 5:
                missing_keys_map = {
                    f"vol{i+1}": f"vol.{i+1}.data" for i in range(4)
                }
                missing_keys_map["after"] = "after.data"
                
                extracted_keys = set(urls.keys())
                all_keys = set(missing_keys_map.keys())
                missing_simple_keys = all_keys - extracted_keys
                
                missing_original_keys = [missing_keys_map[k] for k in missing_simple_keys]
                raise ValueError(f"配置文件缺少必要的键: {', '.join(missing_original_keys)}")

            if self.is_debug_mode():
                print(f"DEBUG: Extracted URLs: {urls}")
                print("--- Finished getting download URL successfully ---")
            return urls

        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else "未知"
            try:
                error_response = e.response.json() if e.response else {}
                json_title = error_response.get("title", "无错误类型")
                json_message = error_response.get("message", "无附加错误信息")
            except (ValueError, AttributeError):
                json_title = "配置文件异常，无法解析错误类型"
                json_message = "配置文件异常，无法解析错误信息"

            if self.is_debug_mode():
                print(f"ERROR: Failed to get download config due to RequestException: {e}")
            
            QtWidgets.QMessageBox.critical(
                self.main_window,
                f"错误 - {APP_NAME}",
                f"\n下载配置获取失败\n\n【HTTP状态】：{status_code}\n【错误类型】：{json_title}\n【错误信息】：{json_message}\n",
            )
            return {}
        except ValueError as e:
            if self.is_debug_mode():
                print(f"ERROR: Failed to parse download config due to ValueError: {e}")

            QtWidgets.QMessageBox.critical(
                self.main_window,
                f"错误 - {APP_NAME}",
                f"\n配置文件格式异常\n\n【错误信息】：{e}\n",
            )
            return {}

    def download_action(self):
        """开始下载流程"""
        self.main_window.download_queue_history = []
        
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            print(f"DEBUG: 开始下载流程, 识别到 {len(game_dirs)} 个游戏目录")
        
        if not game_dirs:
            if debug_mode:
                print("DEBUG: 未识别到任何游戏目录，设置目录未找到错误")
            self.main_window.last_error_message = "directory_not_found"
            QtWidgets.QMessageBox.warning(
                self.main_window, 
                f"目录错误 - {APP_NAME}", 
                "\n未能识别到任何游戏目录。\n\n请确认您选择的是游戏的上级目录，并且该目录中包含NEKOPARA系列游戏文件夹。\n"
            )
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            return
            
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="pre")

        install_paths = self.get_install_paths()
        
        self.main_window.hash_thread = self.main_window.create_hash_thread("pre", install_paths)
        self.main_window.hash_thread.pre_finished.connect(
            lambda updated_status: self.on_pre_hash_finished_with_dirs(updated_status, game_dirs)
        )
        self.main_window.hash_thread.start()
        
    def on_pre_hash_finished_with_dirs(self, updated_status, game_dirs):
        """优化的哈希预检查完成处理，带有游戏目录信息
        
        Args:
            updated_status: 更新后的安装状态
            game_dirs: 识别到的游戏目录
        """
        self.main_window.installed_status = updated_status
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.accept()
            self.main_window.hash_msg_box = None
            
        debug_mode = self.is_debug_mode()
        
        self.main_window.setEnabled(True)
        
        installable_games = []
        already_installed_games = []
        for game_version, game_dir in game_dirs.items():
            if self.main_window.installed_status.get(game_version, False):
                if debug_mode:
                    print(f"DEBUG: {game_version} 已安装补丁，不需要再次安装")
                already_installed_games.append(game_version)
            else:
                if debug_mode:
                    print(f"DEBUG: {game_version} 未安装补丁，可以安装")
                installable_games.append(game_version)
        
        status_message = ""
        if already_installed_games:
            status_message += f"已安装补丁的游戏：\n{chr(10).join(already_installed_games)}\n\n"
            
        if not installable_games:
            QtWidgets.QMessageBox.information(
                self.main_window, 
                f"信息 - {APP_NAME}", 
                f"\n所有检测到的游戏都已安装补丁。\n\n{status_message}"
            )
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            return
            
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("选择要安装的游戏")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        if already_installed_games:
            already_installed_label = QLabel("已安装补丁的游戏:", dialog)
            already_installed_label.setFont(QFont(already_installed_label.font().family(), already_installed_label.font().pointSize(), QFont.Bold))
            layout.addWidget(already_installed_label)
            
            already_installed_list = QLabel(chr(10).join(already_installed_games), dialog)
            layout.addWidget(already_installed_list)
            
            layout.addSpacing(10)
        
        info_label = QLabel("请选择你需要安装补丁的游戏:", dialog)
        info_label.setFont(QFont(info_label.font().family(), info_label.font().pointSize(), QFont.Bold))
        layout.addWidget(info_label)
        
        list_widget = QListWidget(dialog)
        list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for game in installable_games:
            list_widget.addItem(game)
        layout.addWidget(list_widget)
        
        select_all_btn = QPushButton("全选", dialog)
        select_all_btn.clicked.connect(lambda: list_widget.selectAll())
        layout.addWidget(select_all_btn)
        
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("确定", dialog)
        cancel_button = QPushButton("取消", dialog)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        result = dialog.exec()
        
        if result != QDialog.DialogCode.Accepted or list_widget.selectedItems() == []:
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            return
            
        selected_games = [item.text() for item in list_widget.selectedItems()]
        if debug_mode:
            print(f"DEBUG: 用户选择了以下游戏进行安装: {selected_games}")
            
        selected_game_dirs = {game: game_dirs[game] for game in selected_games if game in game_dirs}
        
        self.main_window.setEnabled(False)

        config = self.get_download_url()
        if not config:
            QtWidgets.QMessageBox.critical(
                self.main_window, f"错误 - {APP_NAME}", "\n网络状态异常或服务器故障，请重试\n"
            )
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            return

        self._fill_download_queue(config, selected_game_dirs)

        if not self.download_queue:
            self.main_window.after_hash_compare()
            return
        
        self._show_cloudflare_option()

    def _fill_download_queue(self, config, game_dirs):
        """填充下载队列
        
        Args:
            config: 包含下载URL的配置字典
            game_dirs: 包含游戏文件夹路径的字典
        """
        self.download_queue.clear()
        
        if not hasattr(self.main_window, 'download_queue_history'):
            self.main_window.download_queue_history = []
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            print(f"DEBUG: 填充下载队列, 游戏目录: {game_dirs}")
        
        for i in range(1, 5):
            game_version = f"NEKOPARA Vol.{i}"
            if game_version in game_dirs and not self.main_window.installed_status.get(game_version, False):
                url = config.get(f"vol{i}")
                if not url: continue
                
                game_folder = game_dirs[game_version]
                if debug_mode:
                    print(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                
                _7z_path = os.path.join(PLUGIN, f"vol.{i}.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))
                self.main_window.download_queue_history.append(game_version)

        game_version = "NEKOPARA After"
        if game_version in game_dirs and not self.main_window.installed_status.get(game_version, False):
            url = config.get("after")
            if url:
                game_folder = game_dirs[game_version]
                if debug_mode:
                    print(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))
                self.main_window.download_queue_history.append(game_version)
                
    def _show_cloudflare_option(self):
        """显示Cloudflare加速选择对话框"""
        if self.download_queue:
            first_url = self.download_queue[0][0]
            hostname = urlparse(first_url).hostname
            
            if hostname:
                existing_ips = self.cloudflare_optimizer.hosts_manager.get_hostname_entries(hostname)
                
                if existing_ips:
                    print(f"发现hosts文件中已有域名 {hostname} 的优选IP记录，跳过询问直接使用")
                    
                    self.cloudflare_optimizer.optimization_done = True
                    self.cloudflare_optimizer.countdown_finished = True
                    
                    ipv4_entries = [ip for ip in existing_ips if ':' not in ip]
                    ipv6_entries = [ip for ip in existing_ips if ':' in ip]
                    
                    if ipv4_entries:
                        self.cloudflare_optimizer.optimized_ip = ipv4_entries[0]
                    if ipv6_entries:
                        self.cloudflare_optimizer.optimized_ipv6 = ipv6_entries[0]
                    
                    self.main_window.current_url = first_url
                    
                    self.next_download_task()
                    return
                    
        self.main_window.setEnabled(True)
        
        msg_box = QtWidgets.QMessageBox(self.main_window)
        msg_box.setWindowTitle(f"下载优化 - {APP_NAME}")
        msg_box.setText("是否愿意通过Cloudflare加速来优化下载速度？\n\n这将临时修改系统的hosts文件，并需要管理员权限。\n如您的杀毒软件提醒有软件正在修改hosts文件，请注意放行。")
        
        cf_icon_path = resource_path("IMG/ICO/cloudflare_logo_icon.ico")
        if os.path.exists(cf_icon_path):
            cf_pixmap = QPixmap(cf_icon_path)
            if not cf_pixmap.isNull():
                msg_box.setWindowIcon(QIcon(cf_pixmap))
                msg_box.setIconPixmap(cf_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, 
                                                    Qt.TransformationMode.SmoothTransformation))
        else:
            msg_box.setIcon(QtWidgets.QMessageBox.Icon.Question)
        
        yes_button = msg_box.addButton("是，开启加速", QtWidgets.QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("否，直接下载", QtWidgets.QMessageBox.ButtonRole.NoRole)
        cancel_button = msg_box.addButton("取消安装", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        if clicked_button == cancel_button:
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            self.download_queue.clear()
            return
        
        self.main_window.setEnabled(False)
        
        use_optimization = clicked_button == yes_button
        
        if use_optimization and not self.cloudflare_optimizer.is_optimization_done():
            first_url = self.download_queue[0][0]
            self.main_window.current_url = first_url
            self.cloudflare_optimizer.start_ip_optimization(first_url)
            QtCore.QTimer.singleShot(100, self.check_optimization_status)
        else:
            self.next_download_task()
    
    def check_optimization_status(self):
        """检查IP优化状态并继续下载流程"""
        if self.cloudflare_optimizer.is_optimization_done() and self.cloudflare_optimizer.is_countdown_finished():
            self.next_download_task()
        else:
            QtCore.QTimer.singleShot(100, self.check_optimization_status)
                        
    def next_download_task(self):
        """处理下载队列中的下一个任务"""
        if not self.download_queue:
            self.main_window.after_hash_compare()
            return
            
        if self.download_task_manager.current_download_thread and self.download_task_manager.current_download_thread.isRunning():
            return
        
        url, game_folder, game_version, _7z_path, plugin_path = self.download_queue.popleft()
        self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)

    def download_setting(self, url, game_folder, game_version, _7z_path, plugin_path):
        """准备下载特定游戏版本
        
        Args:
            url: 下载URL
            game_folder: 游戏文件夹路径
            game_version: 游戏版本名称
            _7z_path: 7z文件保存路径
            plugin_path: 插件路径
        """
        install_paths = self.get_install_paths()
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            print(f"DEBUG: 准备下载游戏 {game_version}")
            print(f"DEBUG: 游戏文件夹: {game_folder}")
            
        game_exe_exists = True
        
        if (
            not game_exe_exists
            or self.main_window.installed_status[game_version]
        ):
            if debug_mode:
                print(f"DEBUG: 跳过下载游戏 {game_version}")
                print(f"DEBUG: 游戏存在: {game_exe_exists}")
                print(f"DEBUG: 已安装补丁: {self.main_window.installed_status[game_version]}")
            self.main_window.installed_status[game_version] = False if not game_exe_exists else True
            self.next_download_task()
            return
        
        self.main_window.progress_window = self.main_window.create_progress_window()
        
        self.optimized_ip = self.cloudflare_optimizer.get_optimized_ip()
        if self.optimized_ip:
            print(f"已为 {game_version} 获取到优选IP: {self.optimized_ip}")
        else:
            print(f"未能为 {game_version} 获取优选IP，将使用默认线路。")

        self.download_task_manager.start_download(url, _7z_path, game_version, game_folder, plugin_path)

    def on_download_finished(self, success, error, url, game_folder, game_version, _7z_path, plugin_path):
        """下载完成后的处理
        
        Args:
            success: 是否下载成功
            error: 错误信息
            url: 下载URL
            game_folder: 游戏文件夹路径
            game_version: 游戏版本名称
            _7z_path: 7z文件保存路径
            plugin_path: 插件路径
        """
        if self.main_window.progress_window and self.main_window.progress_window.isVisible():
            self.main_window.progress_window.reject()
            self.main_window.progress_window = None

        if not success:
            print(f"--- Download Failed: {game_version} ---")
            print(error)
            print("------------------------------------")
            
            self.main_window.setEnabled(True)
            
            msg_box = QtWidgets.QMessageBox(self.main_window)
            msg_box.setWindowTitle(f"下载失败 - {APP_NAME}")
            msg_box.setText(f"\n文件获取失败: {game_version}\n错误: {error}\n\n是否重试？")
            
            retry_button = msg_box.addButton("重试", QtWidgets.QMessageBox.ButtonRole.YesRole)
            next_button = msg_box.addButton("下一个", QtWidgets.QMessageBox.ButtonRole.NoRole)
            end_button = msg_box.addButton("结束", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            clicked_button = msg_box.clickedButton()

            if clicked_button == retry_button:
                self.main_window.setEnabled(False)
                self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)
            elif clicked_button == next_button:
                self.main_window.setEnabled(False)
                self.next_download_task()
            else:
                self.on_download_stopped()
            return

        self.extraction_handler.start_extraction(_7z_path, game_folder, plugin_path, game_version)
        self.extraction_handler.extraction_finished.connect(self.on_extraction_finished)

    def on_extraction_finished(self, continue_download):
        """解压完成后的回调，决定是否继续下载队列
        
        Args:
            continue_download: 是否继续下载队列中的下一个任务
        """
        if continue_download:
            self.next_download_task()
        else:
            self.download_queue.clear()
            self.main_window.show_result()

    def on_download_stopped(self):
        """当用户点击停止按钮或选择结束时调用的函数"""
        self.cloudflare_optimizer.stop_optimization()

        self.download_task_manager.stop_download()
            
        self.download_queue.clear()
        
        if hasattr(self.main_window, 'progress_window') and self.main_window.progress_window:
            if self.main_window.progress_window.isVisible():
                self.main_window.progress_window.reject()
            self.main_window.progress_window = None

        print("下载已全部停止。")
        
        self.main_window.setEnabled(True)
        self.main_window.ui.start_install_text.setText("开始安装")
        
        QtWidgets.QMessageBox.information(
            self.main_window,
            f"已取消 - {APP_NAME}",
            "\n已成功取消安装进程。\n"
        )

    def get_download_thread_count(self):
        """获取当前下载线程设置对应的线程数"""
        return self.download_task_manager.get_download_thread_count()
        
    def set_download_thread_level(self, level):
        """设置下载线程级别"""
        return self.download_task_manager.set_download_thread_level(level)
    
    def show_download_thread_settings(self):
        """显示下载线程设置对话框"""
        return self.download_task_manager.show_download_thread_settings() 