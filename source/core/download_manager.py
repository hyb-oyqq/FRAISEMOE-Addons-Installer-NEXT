import os
import requests
import json
from collections import deque
from urllib.parse import urlparse
import re # Added for recursive search

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

from utils import msgbox_frame, HostsManager, resource_path
from data.config import APP_NAME, PLUGIN, GAME_INFO, UA, CONFIG_URL
from workers import IpOptimizerThread

class DownloadManager:
    def __init__(self, main_window):
        """初始化下载管理器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
        """
        self.main_window = main_window
        self.selected_folder = ""
        self.download_queue = deque()
        self.current_download_thread = None
        self.hosts_manager = HostsManager()
        self.optimized_ip = None
        self.optimization_done = False # 标记是否已执行过优选
        self.optimizing_msg_box = None
    
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
        # 将按钮设置为"正在安装"状态
        self.main_window.set_start_button_enabled(False, installing=True)
        self.download_action()

    def get_install_paths(self):
        """获取所有游戏版本的安装路径"""
        # 使用改进的目录识别功能
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        install_paths = {}
        
        debug_mode = self.is_debug_mode()
        
        for game, info in GAME_INFO.items():
            if game in game_dirs:
                # 如果找到了游戏目录，使用它
                game_dir = game_dirs[game]
                install_path = os.path.join(game_dir, os.path.basename(info["install_path"]))
                install_paths[game] = install_path
                if debug_mode:
                    print(f"DEBUG: 使用识别到的游戏目录 {game}: {game_dir}")
                    print(f"DEBUG: 安装路径设置为: {install_path}")
            else:
                # 回退到原始路径计算方式
                install_path = os.path.join(self.selected_folder, info["install_path"])
                install_paths[game] = install_path
                if debug_mode:
                    print(f"DEBUG: 未识别到游戏目录 {game}, 使用默认路径: {install_path}")
                    
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
                # 如果没有预加载的配置，则同步获取
                headers = {"User-Agent": UA}
                response = requests.get(CONFIG_URL, headers=headers, timeout=10)
                response.raise_for_status()
                config_data = response.json()

            if not config_data:
                raise ValueError("未能获取或解析配置数据")

            if self.is_debug_mode():
                print(f"DEBUG: Parsed JSON data: {json.dumps(config_data, indent=2)}")

            # 统一处理URL提取，确保返回扁平化的字典
            urls = {}
            for i in range(4):
                key = f"vol.{i+1}.data"
                if key in config_data and "url" in config_data[key]:
                    urls[f"vol{i+1}"] = config_data[key]["url"]
            
            if "after.data" in config_data and "url" in config_data["after.data"]:
                urls["after"] = config_data["after.data"]["url"]

            # 检查是否成功提取了所有URL
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
        # 按钮在file_dialog中已设置为"正在安装"状态
        
        # 清空下载历史记录
        self.main_window.download_queue_history = []
        
        # 使用改进的目录识别功能
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            print(f"DEBUG: 开始下载流程, 识别到 {len(game_dirs)} 个游戏目录")
        
        # 检查是否找到任何游戏目录
        if not game_dirs:
            if debug_mode:
                print("DEBUG: 未识别到任何游戏目录，设置目录未找到错误")
            # 设置特定的错误类型，以便在按钮点击处理中区分处理
            self.main_window.last_error_message = "directory_not_found"
            QtWidgets.QMessageBox.warning(
                self.main_window, 
                f"目录错误 - {APP_NAME}", 
                "\n未能识别到任何游戏目录。\n\n请确认您选择的是游戏的上级目录，并且该目录中包含NEKOPARA系列游戏文件夹。\n"
            )
            # 恢复按钮为"无法安装"状态
            self.main_window.set_start_button_enabled(False)
            return
        
        # 显示哈希检查窗口
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="pre")

        # 执行预检查
        install_paths = self.get_install_paths()
        
        self.main_window.hash_thread = self.main_window.create_hash_thread("pre", install_paths)
        self.main_window.hash_thread.pre_finished.connect(self.on_pre_hash_finished)
        self.main_window.hash_thread.start()
    
    def on_pre_hash_finished(self, updated_status):
        """哈希预检查完成后的处理
        
        Args:
            updated_status: 更新后的安装状态
        """
        self.main_window.installed_status = updated_status
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.accept()
            self.main_window.hash_msg_box = None

        # 获取下载配置
        config = self.get_download_url()
        if not config:
            QtWidgets.QMessageBox.critical(
                self.main_window, f"错误 - {APP_NAME}", "\n网络状态异常或服务器故障，请重试\n"
            )
            # 网络故障时，使用"无法安装"状态
            self.main_window.set_start_button_enabled(False)
            return

        # 填充下载队列
        self._fill_download_queue(config)

        # 如果没有需要下载的内容，直接进行最终校验
        if not self.download_queue:
            self.main_window.after_hash_compare()
            return
        
        # 只有当有需要下载内容时才询问是否使用Cloudflare加速
        # 询问用户是否使用Cloudflare加速
        msg_box = QtWidgets.QMessageBox(self.main_window)
        msg_box.setWindowTitle(f"下载优化 - {APP_NAME}")
        msg_box.setText("是否愿意通过Cloudflare加速来优化下载速度？\n\n这将临时修改系统的hosts文件，并需要管理员权限。\n如您的杀毒软件提醒有软件正在修改hosts文件，请注意放行。")
        
        # 设置Cloudflare图标
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
        
        msg_box.exec()
        
        use_optimization = msg_box.clickedButton() == yes_button

        if use_optimization and not self.optimization_done:
            first_url = self.download_queue[0][0]
            self._start_ip_optimization(first_url)
        else:
            # 如果用户选择不优化，或已经优化过，直接开始下载
            self.next_download_task()
    
    def _fill_download_queue(self, config):
        """填充下载队列
        
        Args:
            config: 包含下载URL的配置字典
        """
        # 清空现有队列
        self.download_queue.clear()
        
        # 创建下载历史记录列表，用于跟踪本次安装的游戏
        if not hasattr(self.main_window, 'download_queue_history'):
            self.main_window.download_queue_history = []
            
        # 获取所有识别到的游戏目录
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            print(f"DEBUG: 填充下载队列, 识别到的游戏目录: {game_dirs}")
        
        # 添加nekopara 1-4
        for i in range(1, 5):
            game_version = f"NEKOPARA Vol.{i}"
            if not self.main_window.installed_status.get(game_version, False):
                url = config.get(f"vol{i}")
                if not url: continue
                
                # 确定游戏文件夹路径
                if game_version in game_dirs:
                    game_folder = game_dirs[game_version]
                    if debug_mode:
                        print(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                else:
                    # 回退到传统方式
                    game_folder = os.path.join(self.selected_folder, f"NEKOPARA Vol. {i}")
                    if debug_mode:
                        print(f"DEBUG: 使用默认游戏目录 {game_version}: {game_folder}")
                
                _7z_path = os.path.join(PLUGIN, f"vol.{i}.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))
                # 记录到下载历史
                self.main_window.download_queue_history.append(game_version)

        # 添加nekopara after
        game_version = "NEKOPARA After"
        if not self.main_window.installed_status.get(game_version, False):
            url = config.get("after")
            if url:
                # 确定After的游戏文件夹路径
                if game_version in game_dirs:
                    game_folder = game_dirs[game_version]
                    if debug_mode:
                        print(f"DEBUG: 使用识别到的游戏目录 {game_version}: {game_folder}")
                else:
                    game_folder = os.path.join(self.selected_folder, "NEKOPARA After")
                    if debug_mode:
                        print(f"DEBUG: 使用默认游戏目录 {game_version}: {game_folder}")
                
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))
                # 记录到下载历史
                self.main_window.download_queue_history.append(game_version)
    
    def _start_ip_optimization(self, url):
        """开始IP优化过程
        
        Args:
            url: 用于优化的URL
        """
        # 禁用退出按钮
        self.main_window.ui.exit_btn.setEnabled(False)
        
        # 使用Cloudflare图标创建消息框
        
        self.optimizing_msg_box = msgbox_frame(
            f"通知 - {APP_NAME}",
            "\n正在优选Cloudflare IP，请稍候...\n\n这可能需要5-10分钟，请耐心等待喵~"
        )
        # 设置Cloudflare图标
        cf_icon_path = resource_path("IMG/ICO/cloudflare_logo_icon.ico")
        if os.path.exists(cf_icon_path):
            cf_pixmap = QPixmap(cf_icon_path)
            if not cf_pixmap.isNull():
                self.optimizing_msg_box.setWindowIcon(QIcon(cf_pixmap))
                self.optimizing_msg_box.setIconPixmap(cf_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, 
                                                                 Qt.TransformationMode.SmoothTransformation))
        
        # 我们不再提供"跳过"按钮
        self.optimizing_msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.NoButton)
        self.optimizing_msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.optimizing_msg_box.open()

        # 创建并启动优化线程
        self.ip_optimizer_thread = IpOptimizerThread(url)
        self.ip_optimizer_thread.finished.connect(self.on_optimization_finished)
        self.ip_optimizer_thread.start()
    
    def on_optimization_finished(self, ip):
        """IP优化完成后的处理
        
        Args:
            ip: 优选的IP地址，如果失败则为空字符串
        """
        self.optimized_ip = ip
        self.optimization_done = True
        
        # 关闭提示框
        if hasattr(self, 'optimizing_msg_box') and self.optimizing_msg_box:
            if self.optimizing_msg_box.isVisible():
                self.optimizing_msg_box.accept()
            self.optimizing_msg_box = None

        # 显示优选结果
        if not ip:
            msg_box = QtWidgets.QMessageBox(self.main_window)
            msg_box.setWindowTitle(f"优选失败 - {APP_NAME}")
            msg_box.setText("\n未能找到合适的Cloudflare IP，将使用默认网络进行下载。\n\n10秒后自动继续...")
            msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            ok_button = msg_box.addButton("确定 (10)", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            
            # 创建计时器实现倒计时
            countdown = 10
            timer = QtCore.QTimer(self.main_window)
            
            def update_countdown():
                nonlocal countdown
                countdown -= 1
                ok_button.setText(f"确定 ({countdown})")
                if countdown <= 0:
                    timer.stop()
                    if msg_box.isVisible():
                        msg_box.accept()
            
            timer.timeout.connect(update_countdown)
            timer.start(1000)  # 每秒更新一次
            
            # 显示对话框，但不阻塞主线程
            msg_box.open()
            
            # 连接关闭信号以停止计时器
            msg_box.finished.connect(timer.stop)
        else:
            # 应用优选IP到hosts文件
            if self.download_queue:
                first_url = self.download_queue[0][0]
                hostname = urlparse(first_url).hostname
                
                # 先清理可能存在的旧记录
                self.hosts_manager.clean_hostname_entries(hostname)
                
                if self.hosts_manager.apply_ip(hostname, ip):
                    msg_box = QtWidgets.QMessageBox(self.main_window)
                    msg_box.setWindowTitle(f"成功 - {APP_NAME}")
                    msg_box.setText(f"\n已将优选IP ({ip}) 应用到hosts文件。\n\n10秒后自动继续...")
                    msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
                    ok_button = msg_box.addButton("确定 (10)", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                    
                    # 创建计时器实现倒计时
                    countdown = 10
                    timer = QtCore.QTimer(self.main_window)
                    
                    def update_countdown():
                        nonlocal countdown
                        countdown -= 1
                        ok_button.setText(f"确定 ({countdown})")
                        if countdown <= 0:
                            timer.stop()
                            if msg_box.isVisible():
                                msg_box.accept()
                    
                    timer.timeout.connect(update_countdown)
                    timer.start(1000)  # 每秒更新一次
                    
                    # 显示对话框，但不阻塞主线程
                    msg_box.open()
                    
                    # 连接关闭信号以停止计时器
                    msg_box.finished.connect(timer.stop)
                else:
                    QtWidgets.QMessageBox.critical(
                        self.main_window, 
                        f"错误 - {APP_NAME}", 
                        "\n修改hosts文件失败，请检查程序是否以管理员权限运行。\n"
                    )
        
        # 计时器结束或用户点击确定时，继续下载
        QtCore.QTimer.singleShot(10000, self.next_download_task)

    def next_download_task(self):
        """处理下载队列中的下一个任务"""
        if not self.download_queue:
            self.main_window.after_hash_compare()
            return
            
        # 检查下载线程是否仍在运行，以避免在手动停止后立即开始下一个任务
        if self.current_download_thread and self.current_download_thread.isRunning():
            return
        
        # 获取下一个下载任务并开始
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
        # 使用改进的目录识别获取安装路径
        install_paths = self.get_install_paths()
        
        debug_mode = self.is_debug_mode()
        if debug_mode:
            print(f"DEBUG: 准备下载游戏 {game_version}")
            print(f"DEBUG: 游戏文件夹: {game_folder}")
            
        # 获取游戏可执行文件路径
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(self.selected_folder)
        game_exe_exists = False
        
        if game_version in game_dirs:
            game_dir = game_dirs[game_version]
            # 游戏目录已经通过可执行文件验证了，可以直接认为存在
            game_exe_exists = True
            if debug_mode:
                print(f"DEBUG: 游戏目录已验证: {game_dir}")
                print(f"DEBUG: 游戏可执行文件存在: {game_exe_exists}")
        else:
            # 回退到传统方法检查游戏是否存在
            # 尝试多种可能的文件名格式
            expected_exe = GAME_INFO[game_version]["exe"]
            traditional_folder = os.path.join(
                self.selected_folder, 
                GAME_INFO[game_version]["install_path"].split("/")[0]
            )
            
            # 定义多种可能的可执行文件变体
            exe_variants = [
                expected_exe,                        # 标准文件名
                expected_exe + ".nocrack",           # Steam加密版本
                expected_exe.replace(".exe", ""),    # 无扩展名版本
                expected_exe.replace("NEKOPARA", "nekopara").lower(),  # 全小写变体
                expected_exe.lower(),                # 小写变体
                expected_exe.lower() + ".nocrack",   # 小写变体的Steam加密版本
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
            
            # 检查所有可能的文件名
            for exe_variant in exe_variants:
                exe_path = os.path.join(traditional_folder, exe_variant)
                if os.path.exists(exe_path):
                    game_exe_exists = True
                    if debug_mode:
                        print(f"DEBUG: 找到游戏可执行文件: {exe_path}")
                    break
            
            # 如果仍未找到，尝试递归搜索
            if not game_exe_exists and os.path.exists(traditional_folder):
                # 提取卷号或检查是否是After
                vol_match = re.search(r"Vol\.(\d+)", game_version)
                vol_num = None
                if vol_match:
                    vol_num = vol_match.group(1)
                
                is_after = "After" in game_version
                
                # 遍历游戏目录及其子目录
                for root, dirs, files in os.walk(traditional_folder):
                    for file in files:
                        file_lower = file.lower()
                        if file.endswith('.exe') or file.endswith('.exe.nocrack'):
                            # 检查文件名中是否包含卷号或关键词
                            if ((vol_num and (f"vol{vol_num}" in file_lower or 
                                             f"vol.{vol_num}" in file_lower or 
                                             f"vol {vol_num}" in file_lower)) or
                                (is_after and "after" in file_lower)):
                                game_exe_exists = True
                                if debug_mode:
                                    print(f"DEBUG: 通过递归搜索找到游戏可执行文件: {os.path.join(root, file)}")
                                break
                    if game_exe_exists:
                        break
            
            if debug_mode:
                print(f"DEBUG: 使用传统方法检查游戏目录: {traditional_folder}")
                print(f"DEBUG: 游戏可执行文件存在: {game_exe_exists}")
        
        # 检查游戏是否已安装
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
        
        # 创建进度窗口并开始下载
        self.main_window.progress_window = self.main_window.create_progress_window()
        self.start_download(url, _7z_path, game_version, game_folder, plugin_path)

    def start_download(self, url, _7z_path, game_version, game_folder, plugin_path):
        """启动下载线程
        
        Args:
            url: 下载URL
            _7z_path: 7z文件保存路径
            game_version: 游戏版本名称
            game_folder: 游戏文件夹路径
            plugin_path: 插件路径
        """
        # 禁用退出按钮
        self.main_window.ui.exit_btn.setEnabled(False)
        
        if self.optimized_ip:
            print(f"已为 {game_version} 获取到优选IP: {self.optimized_ip}")
        else:
            print(f"未能为 {game_version} 获取优选IP，将使用默认线路。")

        # 创建并连接下载线程
        self.current_download_thread = self.main_window.create_download_thread(url, _7z_path, game_version)
        self.current_download_thread.progress.connect(self.main_window.progress_window.update_progress)
        self.current_download_thread.finished.connect(
            lambda success, error: self.on_download_finished(
                success,
                error,
                url,
                game_folder,
                game_version,
                _7z_path,
                plugin_path,
            )
        )
        
        # 连接停止按钮
        self.main_window.progress_window.stop_button.clicked.connect(self.current_download_thread.stop)
        
        # 启动线程和显示进度窗口
        self.current_download_thread.start()
        self.main_window.progress_window.exec()

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
        # 关闭进度窗口
        if self.main_window.progress_window.isVisible():
            self.main_window.progress_window.reject()

        # 处理下载失败
        if not success:
            print(f"--- Download Failed: {game_version} ---")
            print(error)
            print("------------------------------------")
            msg_box = QtWidgets.QMessageBox(self.main_window)
            msg_box.setWindowTitle(f"下载失败 - {APP_NAME}")
            msg_box.setText(f"\n文件获取失败: {game_version}\n错误: {error}\n\n是否重试？")
            
            retry_button = msg_box.addButton("重试", QtWidgets.QMessageBox.ButtonRole.YesRole)
            next_button = msg_box.addButton("下一个", QtWidgets.QMessageBox.ButtonRole.NoRole)
            end_button = msg_box.addButton("结束", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            clicked_button = msg_box.clickedButton()

            # 处理用户选择
            if clicked_button == retry_button:
                self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)
            elif clicked_button == next_button:
                self.next_download_task()
            else:
                self.on_download_stopped()
            return

        # 下载成功，开始解压缩
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

        # 处理解压结果
        if not success:
            QtWidgets.QMessageBox.critical(self.main_window, f"错误 - {APP_NAME}", error_message)
            self.main_window.installed_status[game_version] = False
        else:
            self.main_window.installed_status[game_version] = True
        
        # 继续下一个下载任务
        self.next_download_task()

    def on_download_stopped(self):
        """当用户点击停止按钮或选择结束时调用的函数"""
        # 停止IP优化线程
        if hasattr(self, 'ip_optimizer_thread') and self.ip_optimizer_thread and self.ip_optimizer_thread.isRunning():
            self.ip_optimizer_thread.stop()
            self.ip_optimizer_thread.wait()
            if hasattr(self, 'optimizing_msg_box') and self.optimizing_msg_box:
                if self.optimizing_msg_box.isVisible():
                    self.optimizing_msg_box.accept()
                self.optimizing_msg_box = None

        # 停止当前可能仍在运行的下载线程
        if self.current_download_thread and self.current_download_thread.isRunning():
            self.current_download_thread.stop()
            self.current_download_thread.wait() # 等待线程完全终止
            
        # 清空下载队列，因为用户决定停止
        self.download_queue.clear()
        
        # 确保进度窗口已关闭
        if hasattr(self.main_window, 'progress_window') and self.main_window.progress_window.isVisible():
            self.main_window.progress_window.reject()

        # 可以在这里决定是否立即进行哈希比较或显示结果
        print("下载已全部停止。")
        self.main_window.setEnabled(True) # 恢复主窗口交互
        
        # 重新启用退出按钮和开始安装按钮
        self.main_window.ui.exit_btn.setEnabled(True)
        self.main_window.set_start_button_enabled(True)
        
        self.main_window.show_result() 