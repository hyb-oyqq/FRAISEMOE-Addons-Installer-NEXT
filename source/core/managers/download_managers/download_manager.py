import os
import requests
import json
from collections import deque
from urllib.parse import urlparse
import re

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtWidgets import QPushButton, QDialog, QHBoxLayout

from utils import msgbox_frame, HostsManager, resource_path
from config.config import APP_NAME, PLUGIN, GAME_INFO, UA, CONFIG_URL, DOWNLOAD_THREADS, DEFAULT_DOWNLOAD_THREAD_LEVEL
from workers import IpOptimizerThread
from core.managers.cloudflare_optimizer import CloudflareOptimizer
from .download_task_manager import DownloadTaskManager
from core.handlers.extraction_handler import ExtractionHandler
from utils.logger import setup_logger
from utils.url_censor import censor_url
from utils.helpers import (
    HashManager, AdminPrivileges, msgbox_frame, HostsManager
)
from workers.download import DownloadThread, ProgressWindow

# 初始化logger
logger = setup_logger("download_manager")

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
        
        self.extraction_thread = None
        self.progress_window = None
        
        # 调试管理器
        self.debug_manager = getattr(main_window, 'debug_manager', None)

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
        
        if hasattr(self.main_window, 'window_manager'):
            self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_INSTALLING)
        
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
                    logger.debug(f"DEBUG: 使用识别到的游戏目录 {game}: {game_dir}")
                    logger.debug(f"DEBUG: 安装路径设置为: {install_path}")
                    
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
                    logger.info("--- Using pre-fetched cloud config ---")
                config_data = self.main_window.cloud_config
            else:
                headers = {"User-Agent": UA}
                response = requests.get(CONFIG_URL, headers=headers, timeout=10)
                response.raise_for_status()
                config_data = response.json()

            if not config_data:
                raise ValueError("未能获取或解析配置数据")

            if self.is_debug_mode():
                # 创建安全版本的配置数据用于调试输出
                safe_config = self._create_safe_config_for_logging(config_data)
                logger.debug(f"DEBUG: Parsed JSON data: {json.dumps(safe_config, indent=2)}")

            urls = {}
            missing_urls = []
            
            # 检查每个游戏版本的URL
            for i in range(4):
                key = f"vol.{i+1}.data"
                if key in config_data and "url" in config_data[key]:
                    urls[f"vol{i+1}"] = config_data[key]["url"]
                else:
                    missing_urls.append(f"NEKOPARA Vol.{i+1}")
                    if self.is_debug_mode():
                        logger.warning(f"DEBUG: 未找到 NEKOPARA Vol.{i+1} 的下载URL")
            
            # 检查After的URL
            if "after.data" in config_data and "url" in config_data["after.data"]:
                urls["after"] = config_data["after.data"]["url"]
            else:
                missing_urls.append("NEKOPARA After")
                if self.is_debug_mode():
                    logger.warning(f"DEBUG: 未找到 NEKOPARA After 的下载URL")

            # 如果有缺失的URL，记录详细信息
            if missing_urls:
                if self.is_debug_mode():
                    logger.warning(f"DEBUG: 以下游戏版本缺少下载URL: {', '.join(missing_urls)}")
                    logger.warning(f"DEBUG: 当前云端配置中的键: {list(config_data.keys())}")
                    
                    # 检查每个游戏数据是否包含url键
                    for i in range(4):
                        key = f"vol.{i+1}.data"
                        if key in config_data:
                            logger.warning(f"DEBUG: {key} 内容: {list(config_data[key].keys())}")
                    
                    if "after.data" in config_data:
                        logger.warning(f"DEBUG: after.data 内容: {list(config_data['after.data'].keys())}")

            if len(urls) != 5:
                missing_keys_map = {
                    f"vol{i+1}": f"vol.{i+1}.data" for i in range(4)
                }
                missing_keys_map["after"] = "after.data"
                
                extracted_keys = set(urls.keys())
                all_keys = set(missing_keys_map.keys())
                missing_simple_keys = all_keys - extracted_keys
                
                missing_original_keys = [missing_keys_map[k] for k in missing_simple_keys]
                
                # 记录详细的缺失信息
                if self.is_debug_mode():
                    logger.warning(f"DEBUG: 缺失的URL键: {missing_original_keys}")
                    
                # 如果所有URL都缺失，可能是云端配置问题
                if len(urls) == 0:
                    raise ValueError(f"配置文件缺少所有下载URL键: {', '.join(missing_original_keys)}")
                    
                # 否则只是部分缺失，可以继续使用已有的URL
                logger.warning(f"配置文件缺少部分键: {', '.join(missing_original_keys)}")

            if self.is_debug_mode():
                # 创建安全版本的URL字典用于调试输出
                safe_urls = {}
                for key, url in urls.items():
                    # 保留域名部分，隐藏路径
                    import re
                    domain_match = re.match(r'(https?://[^/]+)/.*', url)
                    if domain_match:
                        domain = domain_match.group(1)
                        safe_urls[key] = f"{domain}/***隐藏URL路径***"
                    else:
                        safe_urls[key] = "***隐藏URL***"
                logger.debug(f"DEBUG: Extracted URLs: {safe_urls}")
                logger.info("--- Finished getting download URL successfully ---")
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
                logger.error(f"ERROR: Failed to get download config due to RequestException: {e}")
            
            QtWidgets.QMessageBox.critical(
                self.main_window,
                f"错误 - {APP_NAME}",
                f"\n下载配置获取失败\n\n【HTTP状态】：{status_code}\n【错误类型】：{json_title}\n【错误信息】：{json_message}\n",
            )
            return {}
        except ValueError as e:
            if self.is_debug_mode():
                logger.error(f"ERROR: Failed to parse download config due to ValueError: {e}")

            QtWidgets.QMessageBox.critical(
                self.main_window,
                f"错误 - {APP_NAME}",
                f"\n配置文件格式异常\n\n【错误信息】：{e}\n",
            )
            return {}
            
    def _create_safe_config_for_logging(self, config_data):
        """创建用于日志记录的安全配置副本，隐藏敏感URL
        
        Args:
            config_data: 原始配置数据
            
        Returns:
            dict: 安全的配置数据副本
        """
        if not config_data or not isinstance(config_data, dict):
            return config_data
            
        # 创建深拷贝，避免修改原始数据
        import copy
        safe_config = copy.deepcopy(config_data)
        
        # 隐藏敏感URL
        for key in safe_config:
            if isinstance(safe_config[key], dict) and "url" in safe_config[key]:
                # 完全隐藏URL
                safe_config[key]["url"] = "***URL protection***"
        
        return safe_config

    def download_action(self):
        """下载操作的主入口点"""
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(
                self.main_window, f"通知 - {APP_NAME}", "\n未选择任何目录,请重新选择\n"
            )
            return
            
        # 识别游戏目录
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        
        if not game_dirs:
            QtWidgets.QMessageBox.warning(
                self.main_window, f"通知 - {APP_NAME}", "\n未在选择的目录中找到支持的游戏\n"
            )
            self.main_window.setEnabled(True)
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            return
        
        # 检查是否禁用了安装前哈希预检查
        config = getattr(self.main_window, 'config', {})
        disable_pre_hash = False
        if isinstance(config, dict):
            disable_pre_hash = config.get("disable_pre_hash_check", False)
        
        debug_mode = self.is_debug_mode()
        
        if disable_pre_hash:
            if debug_mode:
                logger.debug("DEBUG: 哈希预检查已被用户禁用，跳过预检查")
            # 直接跳过哈希预检查，进入安装流程
            # 创建一个空的安装状态字典，所有游戏都标记为未安装
            updated_status = {}
            for game in game_dirs.keys():
                updated_status[game] = False
            
            # 直接调用预检查完成的处理方法
            self.on_pre_hash_finished_with_dirs(updated_status, game_dirs)
        else:
            # 关闭可能存在的哈希校验窗口
            self.main_window.close_hash_msg_box()
                
            # 显示文件检验窗口
            self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(
                check_type="pre",
                auto_close=True,  # 添加自动关闭参数
                close_delay=1000  # 1秒后自动关闭
            )
            
            # 获取安装路径
            install_paths = self.get_install_paths()
            
            # 创建并启动哈希线程进行预检查
            self.main_window.hash_thread = self.main_window.patch_detector.create_hash_thread("pre", install_paths)
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
        
        # 关闭哈希校验窗口
        self.main_window.close_hash_msg_box()
            
        debug_mode = self.is_debug_mode()
        
        self.main_window.setEnabled(True)
        
        # 使用patch_detector检测可安装的游戏
        already_installed_games, installable_games, disabled_patch_games = self.main_window.patch_detector.detect_installable_games(game_dirs)
        
        status_message = ""
        if already_installed_games:
            status_message += f"已安装补丁的游戏：\n{chr(10).join(already_installed_games)}\n\n"
            
        # 处理禁用补丁的情况
        if disabled_patch_games:
            # 构建提示消息
            disabled_msg = f"检测到以下游戏的补丁已被禁用：\n{chr(10).join(disabled_patch_games)}\n\n是否要启用这些补丁？"
            
            reply = QtWidgets.QMessageBox.question(
                self.main_window, 
                f"检测到禁用补丁 - {APP_NAME}", 
                disabled_msg,
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # 用户选择启用补丁
                if debug_mode:
                    logger.debug(f"DEBUG: 用户选择启用被禁用的补丁")
                
                # 为每个禁用的游戏创建目录映射
                disabled_game_dirs = {game: game_dirs[game] for game in disabled_patch_games}
                
                # 批量启用补丁
                success_count, fail_count, results = self.main_window.patch_manager.batch_toggle_patches(
                    disabled_game_dirs, 
                    operation="enable"
                )
                
                # 显示启用结果
                self.main_window.patch_manager.show_toggle_result(success_count, fail_count, results)
                
                # 更新安装状态
                for game_version in disabled_patch_games:
                    self.main_window.installed_status[game_version] = True
                    if game_version in installable_games:
                        installable_games.remove(game_version)
                    if game_version not in already_installed_games:
                        already_installed_games.append(game_version)
            else:
                if debug_mode:
                    logger.debug(f"用户选择不启用被禁用的补丁，这些游戏将被添加到可安装列表")
                # 用户选择不启用，将这些游戏视为可以安装补丁
                installable_games.extend(disabled_patch_games)
                
        # 如果有可安装的游戏，显示选择对话框
        if installable_games:
            # 创建游戏选择对话框
            dialog = QtWidgets.QDialog(self.main_window)
            dialog.setWindowTitle(f"选择要安装的游戏 - {APP_NAME}")
            dialog.setMinimumWidth(400)
            dialog.setMinimumHeight(300)
            
            layout = QtWidgets.QVBoxLayout()
            
            # 添加说明标签
            label = QtWidgets.QLabel("请选择要安装的游戏：")
            layout.addWidget(label)
            
            # 添加已安装游戏的状态提示
            if already_installed_games:
                installed_label = QtWidgets.QLabel(status_message)
                installed_label.setStyleSheet("color: green;")
                layout.addWidget(installed_label)
            
            # 创建列表控件
            list_widget = QtWidgets.QListWidget()
            list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
            
            # 添加可安装的游戏
            for game in installable_games:
                item = QtWidgets.QListWidgetItem(game)
                item.setSelected(True)  # 默认全选
                list_widget.addItem(item)
                
            layout.addWidget(list_widget)
            
            # 添加全选/取消全选按钮
            select_all_layout = QtWidgets.QHBoxLayout()
            select_all_button = QtWidgets.QPushButton("全选")
            deselect_all_button = QtWidgets.QPushButton("取消全选")
            select_all_layout.addWidget(select_all_button)
            select_all_layout.addWidget(deselect_all_button)
            select_all_layout.addStretch()  # 添加弹性空间，将按钮左对齐
            layout.addLayout(select_all_layout)
            
            # 添加主要操作按钮
            button_layout = QtWidgets.QHBoxLayout()
            ok_button = QtWidgets.QPushButton("确定")
            cancel_button = QtWidgets.QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # 全选功能的实现
            def select_all_items():
                """选择所有游戏项目"""
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    item.setSelected(True)
                    
            def deselect_all_items():
                """取消选择所有游戏项目"""
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    item.setSelected(False)
            
            # 连接按钮信号
            select_all_button.clicked.connect(select_all_items)
            deselect_all_button.clicked.connect(deselect_all_items)
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # 显示对话框
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                selected_games = [item.text() for item in list_widget.selectedItems()]
                if debug_mode:
                    logger.debug(f"DEBUG: 用户选择了以下游戏进行安装: {selected_games}")
                    
                selected_game_dirs = {game: game_dirs[game] for game in selected_games if game in game_dirs}
                
                self.main_window.setEnabled(False)

                # 检查是否处于离线模式
                is_offline_mode = False
                if hasattr(self.main_window, 'offline_mode_manager'):
                    is_offline_mode = self.main_window.offline_mode_manager.is_in_offline_mode()
                    
                if is_offline_mode:
                    if debug_mode:
                        logger.debug("使用离线模式，跳过网络配置获取")
                    self._fill_offline_download_queue(selected_game_dirs)
                else:
                    # 在线模式下，重新获取云端配置
                    if hasattr(self.main_window, 'fetch_cloud_config'):
                        if debug_mode:
                            logger.debug("重新获取云端配置以确保URL最新")
                        # 重新获取云端配置并继续下载流程
                        from workers.config_fetch_thread import ConfigFetchThread
                        self.main_window.config_manager.fetch_cloud_config(
                            ConfigFetchThread,
                            lambda data, error: self._continue_download_after_config_fetch(data, error, selected_game_dirs)
                        )
                    else:
                        # 如果无法重新获取配置，使用当前配置
                        config = self.get_download_url()
                        self._continue_download_with_config(config, selected_game_dirs)
            else:
                if debug_mode:
                    logger.debug("DEBUG: 用户取消了游戏选择")
                if hasattr(self.main_window, 'window_manager'):
                    self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
        else:
            # 如果没有可安装的游戏，显示提示
            if already_installed_games:
                msg = f"所有游戏已安装补丁，无需重复安装。\n\n已安装的游戏：\n{chr(10).join(already_installed_games)}"
            else:
                msg = "未检测到可安装的游戏。"
                
            QtWidgets.QMessageBox.information(
                self.main_window,
                f"通知 - {APP_NAME}",
                msg
            )
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            
    def _continue_download_after_config_fetch(self, data, error, selected_game_dirs):
        """云端配置获取完成后继续下载流程
        
        Args:
            data: 获取到的配置数据
            error: 错误信息
            selected_game_dirs: 选择的游戏目录
        """
        debug_mode = self.is_debug_mode()
        
        if error:
            if debug_mode:
                logger.error(f"DEBUG: 重新获取云端配置失败: {error}")
            # 使用当前配置
            config = self.get_download_url()
        else:
            # 使用新获取的配置
            self.main_window.cloud_config = data
            config = self.get_download_url()
            
        self._continue_download_with_config(config, selected_game_dirs)
        
    def _continue_download_with_config(self, config, selected_game_dirs):
        """使用配置继续下载流程
        
        Args:
            config: 下载配置
            selected_game_dirs: 选择的游戏目录
        """
        debug_mode = self.is_debug_mode()
        
        if not config:
            QtWidgets.QMessageBox.critical(
                self.main_window, f"错误 - {APP_NAME}", "\n网络状态异常或服务器故障，请重试\n"
            )
            self.main_window.setEnabled(True)
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            return

        self._fill_download_queue(config, selected_game_dirs)

        if not self.download_queue:
            # 所有下载任务都已完成，进行后检查
            if debug_mode:
                logger.debug("DEBUG: 所有下载任务完成，进行后检查")
            # 使用patch_detector进行安装后哈希比较
            self.main_window.patch_detector.after_hash_compare()
            return
        
        # 检查是否处于离线模式
        is_offline_mode = False
        if hasattr(self.main_window, 'offline_mode_manager'):
            is_offline_mode = self.main_window.offline_mode_manager.is_in_offline_mode()
            
        # 如果是离线模式，直接开始下一个下载任务
        if is_offline_mode:
            if debug_mode:
                logger.debug("离线模式，跳过Cloudflare优化")
            self.next_download_task()
        else:
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
            logger.debug(f"DEBUG: 填充下载队列, 游戏目录: {game_dirs}")
        
        for i in range(1, 5):
            game_version = f"NEKOPARA Vol.{i}"
            if game_version in game_dirs and not self.main_window.installed_status.get(game_version, False):
                url = config.get(f"vol{i}")
                if not url: continue
                
                game_folder = game_dirs[game_version]
                if debug_mode:
                    logger.debug(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                
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
                    logger.debug(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))
                self.main_window.download_queue_history.append(game_version)
                
    def _fill_offline_download_queue(self, game_dirs):
        """填充离线模式下的下载队列
        
        Args:
            game_dirs: 包含游戏文件夹路径的字典
        """
        self.download_queue.clear()
        
        if not hasattr(self.main_window, 'download_queue_history'):
            self.main_window.download_queue_history = []
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            logger.debug(f"DEBUG: 填充离线下载队列, 游戏目录: {game_dirs}")
        
        # 检查是否有离线模式管理器
        if not hasattr(self.main_window, 'offline_mode_manager'):
            if debug_mode:
                logger.warning("DEBUG: 离线模式管理器未初始化，无法使用离线模式")
            return
            
        for i in range(1, 5):
            game_version = f"NEKOPARA Vol.{i}"
            if game_version in game_dirs and not self.main_window.installed_status.get(game_version, False):
                # 获取离线补丁文件路径
                offline_patch_path = self.main_window.offline_mode_manager.get_offline_patch_path(game_version)
                if not offline_patch_path:
                    if debug_mode:
                        logger.warning(f"DEBUG: 未找到 {game_version} 的离线补丁文件，跳过")
                    continue
                    
                game_folder = game_dirs[game_version]
                if debug_mode:
                    logger.debug(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                    logger.debug(f"DEBUG: 使用离线补丁文件: {offline_patch_path}")
                
                _7z_path = os.path.join(PLUGIN, f"vol.{i}.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                
                # 将本地文件路径作为URL添加到下载队列
                self.download_queue.append((offline_patch_path, game_folder, game_version, _7z_path, plugin_path))
                self.main_window.download_queue_history.append(game_version)

        game_version = "NEKOPARA After"
        if game_version in game_dirs and not self.main_window.installed_status.get(game_version, False):
            # 获取离线补丁文件路径
            offline_patch_path = self.main_window.offline_mode_manager.get_offline_patch_path(game_version)
            if offline_patch_path:
                game_folder = game_dirs[game_version]
                if debug_mode:
                    logger.debug(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                    logger.debug(f"DEBUG: 使用离线补丁文件: {offline_patch_path}")
                
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                
                # 将本地文件路径作为URL添加到下载队列
                self.download_queue.append((offline_patch_path, game_folder, game_version, _7z_path, plugin_path))
                self.main_window.download_queue_history.append(game_version)
            elif debug_mode:
                logger.warning(f"DEBUG: 未找到 {game_version} 的离线补丁文件，跳过")

    def _show_cloudflare_option(self):
        """显示Cloudflare加速选择对话框"""
        if self.download_queue:
            first_url = self.download_queue[0][0]
            
            # 直接检查是否本次会话已执行过优选
            if self.cloudflare_optimizer.has_optimized_in_session:
                logger.info("本次会话已执行过优选，跳过询问直接使用")
                
                self.cloudflare_optimizer.optimization_done = True
                self.cloudflare_optimizer.countdown_finished = True
                
                self.main_window.current_url = first_url
                self.next_download_task()
                return
                
        self.main_window.setEnabled(True)
        
        msg_box = QtWidgets.QMessageBox(self.main_window)
        msg_box.setWindowTitle(f"下载优化 - {APP_NAME}")
        msg_box.setText("是否愿意通过Cloudflare加速来优化下载速度？\n\n这将临时修改系统的hosts文件，并需要管理员权限。\n如您的杀毒软件提醒有软件正在修改hosts文件，请注意放行。")
        
        cf_icon_path = resource_path("assets/images/ICO/cloudflare_logo_icon.ico")
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
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
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
            # 所有下载任务都已完成，进行后检查
            debug_mode = self.is_debug_mode()
            if debug_mode:
                logger.debug("DEBUG: 所有下载任务完成，进行后检查")
            # 使用patch_detector进行安装后哈希比较
            self.main_window.patch_detector.after_hash_compare()
            return
            
        if self.download_task_manager.current_download_thread and self.download_task_manager.current_download_thread.isRunning():
            return
        
        url, game_folder, game_version, _7z_path, plugin_path = self.download_queue.popleft()
        self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)

    def download_setting(self, url, game_folder, game_version, _7z_path, plugin_path):
        """准备下载特定游戏版本
        
        Args:
            url: 下载URL或本地文件路径
            game_folder: 游戏文件夹路径
            game_version: 游戏版本名称
            _7z_path: 7z文件保存路径
            plugin_path: 插件路径
        """
        install_paths = self.get_install_paths()
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            logger.debug(f"DEBUG: 准备下载游戏 {game_version}")
            logger.debug(f"DEBUG: 游戏文件夹: {game_folder}")
            
            # 隐藏敏感URL
            safe_url = "***URL protection***"  # 完全隐藏URL
            logger.debug(f"DEBUG: 下载URL: {safe_url}")
            
        game_exe_exists = True
        
        if (
            not game_exe_exists
            or self.main_window.installed_status[game_version]
        ):
            if debug_mode:
                logger.debug(f"DEBUG: 跳过下载游戏 {game_version}")
                logger.debug(f"DEBUG: 游戏存在: {game_exe_exists}")
                logger.debug(f"DEBUG: 已安装补丁: {self.main_window.installed_status[game_version]}")
            self.main_window.installed_status[game_version] = False if not game_exe_exists else True
            self.next_download_task()
            return
        
        # 检查是否处于离线模式
        is_offline_mode = False
        if hasattr(self.main_window, 'offline_mode_manager'):
            is_offline_mode = self.main_window.offline_mode_manager.is_in_offline_mode()
        
        # 如果是离线模式且URL是本地文件路径
        if is_offline_mode and os.path.isfile(url):
            if debug_mode:
                logger.debug(f"DEBUG: 离线模式，复制本地补丁文件 {url} 到 {_7z_path}")
            
            try:
                # 确保目标目录存在
                os.makedirs(os.path.dirname(_7z_path), exist_ok=True)
                
                # 复制文件
                import shutil
                shutil.copy2(url, _7z_path)
                
                # 验证文件哈希
                hash_valid = False
                if hasattr(self.main_window, 'offline_mode_manager'):
                    if debug_mode:
                        logger.debug(f"DEBUG: 开始验证补丁文件哈希: {_7z_path}")
                    hash_valid = self.main_window.offline_mode_manager.verify_patch_hash(game_version, _7z_path)
                    if debug_mode:
                        logger.debug(f"DEBUG: 补丁文件哈希验证结果: {'成功' if hash_valid else '失败'}")
                else:
                    if debug_mode:
                        logger.warning("DEBUG: 离线模式管理器不可用，跳过哈希验证")
                    hash_valid = True  # 如果没有离线模式管理器，假设验证成功
                
                if hash_valid:
                    if debug_mode:
                        logger.debug(f"成功复制并验证补丁文件 {_7z_path}")
                    # 直接进入解压阶段
                    self.extraction_handler.start_extraction(_7z_path, game_folder, plugin_path, game_version)
                else:
                    if debug_mode:
                        logger.warning(f"DEBUG: 补丁文件哈希验证失败")
                    # 显示错误消息
                    QtWidgets.QMessageBox.critical(
                        self.main_window,
                        f"错误 - {APP_NAME}",
                        f"\n补丁文件校验失败: {game_version}\n\n文件可能已损坏或被篡改，请重新获取补丁文件。\n"
                    )
                    # 继续下一个任务
                    self.next_download_task()
            except Exception as e:
                if debug_mode:
                    logger.error(f"DEBUG: 复制补丁文件失败: {e}")
                # 显示错误消息
                QtWidgets.QMessageBox.critical(
                    self.main_window,
                    f"错误 - {APP_NAME}",
                    f"\n复制补丁文件失败: {game_version}\n错误: {e}\n"
                )
                # 继续下一个任务
                self.next_download_task()
        else:
            # 在线模式，正常下载
            self.main_window.progress_window = self.main_window.create_progress_window()
            
            self.optimized_ip = self.cloudflare_optimizer.get_optimized_ip()
            if self.optimized_ip:
                logger.info(f"已为 {game_version} 获取到优选IP: {self.optimized_ip}")
            else:
                logger.info(f"未能为 {game_version} 获取优选IP，将使用默认线路。")

            self.download_task_manager.start_download(url, _7z_path, game_version, game_folder, plugin_path)

    def on_download_finished(self, success, error, url, game_folder, game_version, _7z_path, plugin_path):
        """下载完成后的回调函数
        
        Args:
            success: 是否下载成功
            error: 错误信息
            url: 下载URL
            game_folder: 游戏文件夹路径
            game_version: 游戏版本
            _7z_path: 7z文件保存路径
            plugin_path: 插件保存路径
        """
        # 如果下载失败，显示错误并询问是否重试
        if not success:
            logger.error(f"--- Download Failed: {game_version} ---")
            logger.error(error)
            logger.error("------------------------------------")
            
            self.main_window.setEnabled(True)
            
            # 分析错误类型
            error_type = "未知错误"
            suggestion = ""
            
            if "SSL/TLS handshake failure" in error:
                error_type = "SSL/TLS连接失败"
                suggestion = "可能是由于网络连接不稳定或证书问题，建议：\n1. 检查网络连接\n2. 尝试使用其他网络\n3. 确保系统时间和日期正确\n4. 可能需要使用代理或VPN"
            elif "Connection timed out" in error or "read timed out" in error:
                error_type = "连接超时"
                suggestion = "下载服务器响应时间过长，建议：\n1. 检查网络连接\n2. 稍后重试\n3. 使用优化网络选项"
            elif "404" in error:
                error_type = "文件不存在"
                suggestion = "请求的文件不存在或已移除，请联系开发者"
            elif "403" in error:
                error_type = "访问被拒绝"
                suggestion = "服务器拒绝请求，可能需要使用优化网络选项"
            elif "No space left on device" in error or "空间不足" in error:
                error_type = "存储空间不足"
                suggestion = "请确保有足够的磁盘空间用于下载和解压文件"
            
            msg_box = QtWidgets.QMessageBox(self.main_window)
            msg_box.setWindowTitle(f"下载失败 - {APP_NAME}")
            error_message = f"\n文件获取失败: {game_version}\n错误类型: {error_type}"
            
            if suggestion:
                error_message += f"\n\n可能的解决方案:\n{suggestion}"
            
            error_message += "\n\n是否重试？"
            msg_box.setText(error_message)
            
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
        
        # 下载成功后，直接进入解压阶段
        debug_mode = self.is_debug_mode()
        
        # 关闭进度窗口
        if hasattr(self.main_window, 'progress_window') and self.main_window.progress_window:
            if self.main_window.progress_window.isVisible():
                self.main_window.progress_window.accept()
            self.main_window.progress_window = None
        
        if debug_mode:
            logger.debug(f"DEBUG: 下载完成，直接进入解压阶段")
            
        # 直接进入解压阶段
        self.extraction_handler.start_extraction(_7z_path, game_folder, plugin_path, game_version)

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

        logger.info("下载已全部停止。")
        
        self.main_window.setEnabled(True)
        if hasattr(self.main_window, 'window_manager'):
            self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
        
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

    def direct_download_action(self, games_to_download):
        """直接下载指定游戏的补丁，绕过补丁判断，用于从离线模式转接过来的任务
        
        Args:
            games_to_download: 要下载的游戏列表
        """
        debug_mode = self.is_debug_mode()
        if debug_mode:
            logger.debug(f"DEBUG: 直接下载模式，绕过补丁判断，游戏列表: {games_to_download}")
            
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(
                self.main_window, f"通知 - {APP_NAME}", "\n未选择任何目录,请重新选择\n"
            )
            return
            
        # 识别游戏目录
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        
        if not game_dirs:
            QtWidgets.QMessageBox.warning(
                self.main_window, f"通知 - {APP_NAME}", "\n未在选择的目录中找到支持的游戏\n"
            )
            self.main_window.setEnabled(True)
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            return
            
        # 过滤出存在的游戏目录
        selected_game_dirs = {game: game_dirs[game] for game in games_to_download if game in game_dirs}
        
        if not selected_game_dirs:
            QtWidgets.QMessageBox.warning(
                self.main_window, f"通知 - {APP_NAME}", "\n未找到指定游戏的安装目录\n"
            )
            self.main_window.setEnabled(True)
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            return
            
        self.main_window.setEnabled(False)
        
        # 获取下载配置
        config = self.get_download_url()
        if not config:
            QtWidgets.QMessageBox.critical(
                self.main_window, f"错误 - {APP_NAME}", "\n网络状态异常或服务器故障，请重试\n"
            )
            self.main_window.setEnabled(True)
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            return
            
        # 填充下载队列
        self._fill_direct_download_queue(config, selected_game_dirs)
        
        if not self.download_queue:
            # 所有下载任务都已完成，进行后检查
            if debug_mode:
                logger.debug("DEBUG: 所有下载任务完成，进行后检查")
            # 使用patch_detector进行安装后哈希比较
            self.main_window.patch_detector.after_hash_compare()
            return
            
        # 显示Cloudflare优化选项
        self._show_cloudflare_option()
        
    def _fill_direct_download_queue(self, config, game_dirs):
        """直接填充下载队列，不检查补丁是否已安装
        
        兼容两种配置格式：
        1) 扁平格式: {"vol1": url, "vol2": url, ..., "after": url}
        2) 原始JSON格式: {"vol.1.data": {"url": url}, ..., "after.data": {"url": url}}
        
        Args:
            config: 包含下载URL的配置字典
            game_dirs: 包含游戏文件夹路径的字典
        """
        self.download_queue.clear()
        
        if not hasattr(self.main_window, 'download_queue_history'):
            self.main_window.download_queue_history = []
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            logger.debug(f"DEBUG: 直接填充下载队列, 游戏目录: {game_dirs}")
        
        # 记录要下载的游戏，用于历史记录
        games_to_download = list(game_dirs.keys())
        self.main_window.download_queue_history = games_to_download
        
        def _extract_url(cfg, simple_key, nested_key):
            """从配置中提取URL，优先扁平键，其次原始JSON嵌套键"""
            try:
                if isinstance(cfg, dict):
                    # 扁平格式: {"vol1": url} 或 {"after": url}
                    val = cfg.get(simple_key)
                    if isinstance(val, str) and val:
                        return val
                    # 原始格式: {"vol.1.data": {"url": url}} 或 {"after.data": {"url": url}}
                    nested = cfg.get(nested_key)
                    if isinstance(nested, dict) and isinstance(nested.get("url"), str) and nested.get("url"):
                        return nested.get("url")
            except Exception:
                pass
            return None
        
        # Vol.1-4
        for i in range(1, 5):
            game_version = f"NEKOPARA Vol.{i}"
            if game_version in game_dirs:
                url = _extract_url(config, f"vol{i}", f"vol.{i}.data")
                if url:
                    game_folder = game_dirs[game_version]
                    if debug_mode:
                        logger.debug(f"DEBUG: 添加下载任务 {game_version}: {game_folder}")
                    
                    _7z_path = os.path.join(PLUGIN, f"vol.{i}.7z")
                    plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                    self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))
                elif debug_mode:
                    logger.warning(f"DEBUG: 未找到 {game_version} 的下载URL")
        
        # After
        game_version = "NEKOPARA After"
        if game_version in game_dirs:
            url = _extract_url(config, "after", "after.data")
            if url:
                game_folder = game_dirs[game_version]
                if debug_mode:
                    logger.debug(f"DEBUG: 添加下载任务 {game_version}: {game_folder}")
                
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))
            elif debug_mode:
                logger.warning(f"DEBUG: 未找到 {game_version} 的下载URL") 

    def graceful_stop_threads(self, threads_dict, timeout_ms=2000):
        """优雅地停止一组线程.
        
        Args:
            threads_dict (dict): 线程名字和线程对象的字典.
            timeout_ms (int): 等待线程自然结束的超时时间.
        """
        for name, thread_obj in threads_dict.items():
            if not thread_obj or not hasattr(thread_obj, 'isRunning') or not thread_obj.isRunning():
                continue

            try:
                if hasattr(thread_obj, 'requestInterruption'):
                    thread_obj.requestInterruption()
                
                if thread_obj.wait(timeout_ms):
                    if self.debug_manager:
                        self.debug_manager.log_debug(f"线程 {name} 已优雅停止.")
                else:
                    if self.debug_manager:
                        self.debug_manager.log_warning(f"线程 {name} 超时，强制终止.")
                    thread_obj.terminate()
                    thread_obj.wait(1000) # a short wait after termination
            except Exception as e:
                if self.debug_manager:
                    self.debug_manager.log_error(f"停止线程 {name} 时发生错误: {e}")

    def on_game_directories_identified(self, game_dirs):
        """当游戏目录识别完成后的回调.
        
        Args:
            game_dirs: 识别到的游戏目录
        """
        self.main_window.ui_manager.hide_loading_dialog()

        if not game_dirs:
            self.main_window.setEnabled(True)
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            from PySide6.QtWidgets import QMessageBox
            from config.config import APP_NAME
            QMessageBox.warning(
                self.main_window, 
                f"目录错误 - {APP_NAME}", 
                "\n未能识别到任何游戏目录。\n\n请确认您选择的是游戏的上级目录，并且该目录中包含NEKOPARA系列游戏文件夹。\n"
            )
            return

        self.main_window.ui_manager.show_loading_dialog("正在检查补丁状态...")
        
        install_paths = self.get_install_paths()
        
        # 使用异步方式进行哈希预检查
        self.main_window.pre_hash_thread = self.main_window.patch_detector.create_hash_thread("pre", install_paths)
        self.main_window.pre_hash_thread.pre_finished.connect(
            lambda updated_status: self.on_pre_hash_finished_with_dirs(updated_status, game_dirs)
        )
        # 在线程自然结束时清理引用
        try:
            self.main_window.pre_hash_thread.finished.connect(lambda: setattr(self.main_window, 'pre_hash_thread', None))
        except Exception:
            pass
        self.main_window.pre_hash_thread.start() 