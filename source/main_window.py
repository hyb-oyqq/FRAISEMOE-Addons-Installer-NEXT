import os
import sys
import shutil
import webbrowser
import requests
import py7zr
import json
from urllib.parse import urlparse
from collections import deque
from PySide6 import QtWidgets
from PySide6.QtCore import QTimer, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMainWindow, QFileDialog, QApplication, QMessageBox, QPushButton

from Ui_install import Ui_MainWindows
from animations import MultiStageAnimations
from config import (
    APP_NAME, APP_VERSION, PLUGIN, GAME_INFO, BLOCK_SIZE,
    PLUGIN_HASH, UA, CONFIG_URL, LOG_FILE
)
from utils import (
    load_base64_image, HashManager, AdminPrivileges, msgbox_frame,
    load_config, save_config, HostsManager, censor_url
)
from download import DownloadThread, ProgressWindow
from ip_optimizer import IpOptimizer
from pic_data import img_data


class Logger:
    def __init__(self, filename, stream):
        self.terminal = stream
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        censored_message = censor_url(message)
        self.terminal.write(censored_message)
        self.log.write(censored_message)
        self.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()

class IpOptimizerThread(QThread):
    finished = Signal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.optimizer = IpOptimizer()

    def run(self):
        optimal_ip = self.optimizer.get_optimal_ip(self.url)
        self.finished.emit(optimal_ip if optimal_ip else "")

    def stop(self):
        self.optimizer.stop()

class HashThread(QThread):
    pre_finished = Signal(dict)
    after_finished = Signal(dict)

    def __init__(self, mode, install_paths, plugin_hash, installed_status, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.install_paths = install_paths
        self.plugin_hash = plugin_hash
        self.installed_status = installed_status
        # 每个线程都应该有自己的HashManager实例
        self.hash_manager = HashManager(BLOCK_SIZE)

    def run(self):
        if self.mode == "pre":
            updated_status = self.hash_manager.cfg_pre_hash_compare(
                self.install_paths, self.plugin_hash, self.installed_status
            )
            self.pre_finished.emit(updated_status)
        elif self.mode == "after":
            result = self.hash_manager.cfg_after_hash_compare(
                self.install_paths, self.plugin_hash, self.installed_status
            )
            self.after_finished.emit(result)


class ExtractionThread(QThread):
    finished = Signal(bool, str, str)  # success, error_message, game_version

    def __init__(self, _7z_path, game_folder, plugin_path, game_version, parent=None):
        super().__init__(parent)
        self._7z_path = _7z_path
        self.game_folder = game_folder
        self.plugin_path = plugin_path
        self.game_version = game_version

    def run(self):
        try:
            with py7zr.SevenZipFile(self._7z_path, mode="r") as archive:
                archive.extractall(path=PLUGIN)
            
            os.makedirs(self.game_folder, exist_ok=True)
            shutil.copy(self.plugin_path, self.game_folder)
            
            if self.game_version == "NEKOPARA After":
                sig_path = os.path.join(PLUGIN, GAME_INFO[self.game_version]["sig_path"])
                shutil.copy(sig_path, self.game_folder)
                
            self.finished.emit(True, "", self.game_version)
        except (py7zr.Bad7zFile, FileNotFoundError, Exception) as e:
            self.finished.emit(False, f"\n文件操作失败，请重试\n\n【错误信息】：{e}\n", self.game_version)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化UI (从Ui_install.py导入)
        self.ui = Ui_MainWindows()
        self.ui.setupUi(self)

        icon_data = img_data.get("icon")
        if icon_data:
            pixmap = load_base64_image(icon_data)
        self.setWindowIcon(QIcon(pixmap))

        # 设置窗口标题为APP_NAME加版本号
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        
        # 初始化动画系统 (从animations.py导入)
        self.animator = MultiStageAnimations(self.ui)
        
        # 初始化功能变量
        self.selected_folder = ""
        self.installed_status = {f"NEKOPARA Vol.{i}": False for i in range(1, 5)}
        self.installed_status["NEKOPARA After"] = False  # 添加After的状态
        self.download_queue = deque()
        self.current_download_thread = None
        self.hash_manager = HashManager(BLOCK_SIZE)
        self.hash_thread = None
        self.extraction_thread = None
        self.hash_msg_box = None
        self.optimized_ip = None
        self.optimization_done = False # 标记是否已执行过优选
        self.logger = None
        self.hosts_manager = HostsManager() # 实例化HostsManager
        
        # 加载配置
        self.config = load_config()
        
        # 检查管理员权限和进程
        admin_privileges = AdminPrivileges()
        admin_privileges.request_admin_privileges()
        admin_privileges.check_and_terminate_processes()
        
        # 备份hosts文件
        self.hosts_manager.backup()
        
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
        
        # 连接信号 (使用Ui_install.py中的组件名称)
        self.ui.start_install_btn.clicked.connect(self.file_dialog)
        self.ui.exit_btn.clicked.connect(self.shutdown_app)

        # “帮助”菜单
        project_home_action = QAction("项目主页", self)
        project_home_action.triggered.connect(self.open_project_home_page)
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        self.ui.menu_2.addAction(project_home_action)
        self.ui.menu_2.addAction(about_action)

        # “设置”菜单
        self.debug_action = QAction("Debug模式", self, checkable=True)
        self.debug_action.setChecked(self.config.get("debug_mode", False))
        self.debug_action.triggered.connect(self.toggle_debug_mode)
        self.ui.menu.addAction(self.debug_action)

        # 根据初始配置决定是否开启Debug模式
        if self.debug_action.isChecked():
            self.start_logging()
        
        # 在窗口显示前设置初始状态
        self.animator.initialize()
        
        # 窗口显示后延迟100ms启动动画
        QTimer.singleShot(100, self.start_animations)
    
    def start_animations(self):
        self.animator.start_animations()

    def toggle_debug_mode(self, checked):
        self.config["debug_mode"] = checked
        save_config(self.config)
        if checked:
            self.start_logging()
        else:
            self.stop_logging()

    def start_logging(self):
        if self.logger is None:
            try:
                if os.path.exists(LOG_FILE):
                    os.remove(LOG_FILE)
                # 保存原始的 stdout 和 stderr
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr
                # 创建 Logger 实例
                self.logger = Logger(LOG_FILE, self.original_stdout)
                sys.stdout = self.logger
                sys.stderr = self.logger
                print("--- Debug mode enabled ---")
            except (IOError, OSError) as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"无法创建日志文件: {e}")
                self.logger = None

    def stop_logging(self):
        if self.logger:
            print("--- Debug mode disabled ---")
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.logger.close()
            self.logger = None
        
    def get_install_paths(self):
        return {
            game: os.path.join(self.selected_folder, info["install_path"])
            for game, info in GAME_INFO.items()
        }

    def file_dialog(self):
        self.selected_folder = QFileDialog.getExistingDirectory(
            self, f"选择游戏所在【上级目录】 {APP_NAME}"
        )
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(
                self, f"通知 - {APP_NAME}", "\n未选择任何目录,请重新选择\n"
            )
            return
        self.download_action()

    def get_download_url(self) -> dict:
        try:
            headers = {"User-Agent": UA}
            if self.debug_action.isChecked():
                print("--- Starting to get download URL ---")
                print(f"DEBUG: Requesting URL: {CONFIG_URL}")
                print(f"DEBUG: Using Headers: {headers}")

            response = requests.get(CONFIG_URL, headers=headers, timeout=10)

            if self.debug_action.isChecked():
                print(f"DEBUG: Response Status Code: {response.status_code}")
                print(f"DEBUG: Response Headers: {response.headers}")
                print(f"DEBUG: Response Text: {response.text}")

            response.raise_for_status()

            # 从响应文本中提取有效的 JSON 部分
            response_text = response.text
            json_start_index = response_text.find('{')
            if json_start_index == -1:
                raise ValueError("响应中未找到有效的 JSON 对象")

            json_text = response_text[json_start_index:]
            config_data = json.loads(json_text)
            
            if self.debug_action.isChecked():
                print(f"DEBUG: Parsed JSON data: {json.dumps(config_data, indent=2)}")

            # 修正键名检查，确保所有必需的键都存在
            required_keys = [f"vol.{i+1}.data" for i in range(4)] + ["after.data"]
            if not all(key in config_data for key in required_keys):
                missing_keys = [key for key in required_keys if key not in config_data]
                raise ValueError(f"配置文件缺少必要的键: {', '.join(missing_keys)}")
            
            # 修正提取URL的逻辑，确保使用正确的键
            urls = {
                f"vol{i+1}": config_data[f"vol.{i+1}.data"]["url"] for i in range(4)
            } | {
                "after": config_data["after.data"]["url"]
            }
            if self.debug_action.isChecked():
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

            if self.debug_action.isChecked():
                print(f"ERROR: Failed to get download config due to RequestException: {e}")
            
            QtWidgets.QMessageBox.critical(
                self,
                f"错误 - {APP_NAME}",
                f"\n下载配置获取失败\n\n【HTTP状态】：{status_code}\n【错误类型】：{json_title}\n【错误信息】：{json_message}\n",
            )
            return {}
        except ValueError as e:
            if self.debug_action.isChecked():
                print(f"ERROR: Failed to parse download config due to ValueError: {e}")

            QtWidgets.QMessageBox.critical(
                self,
                f"错误 - {APP_NAME}",
                f"\n配置文件格式异常\n\n【错误信息】：{e}\n",
            )
            return {}

    def download_setting(self, url, game_folder, game_version, _7z_path, plugin_path):
        game_exe = {
            game: os.path.join(
                self.selected_folder, info["install_path"].split("/")[0], info["exe"]
            )
            for game, info in GAME_INFO.items()
        }
        
        if (
            game_version not in game_exe
            or not os.path.exists(game_exe[game_version])
            or self.installed_status[game_version]
        ):
            self.installed_status[game_version] = False
            self.show_result()
            return
            
        self.progress_window = ProgressWindow(self)
        self.start_download_with_ip(self.optimized_ip, url, _7z_path, game_version, game_folder, plugin_path)


    def on_optimization_and_hosts_finished(self, ip):
        self.optimized_ip = ip
        self.optimization_done = True
        if hasattr(self, 'optimizing_msg_box') and self.optimizing_msg_box:
            if self.optimizing_msg_box.isVisible():
                self.optimizing_msg_box.accept()
            self.optimizing_msg_box = None

        if not ip:
            QtWidgets.QMessageBox.warning(self, f"优选失败 - {APP_NAME}", "\n未能找到合适的Cloudflare IP，将使用默认网络进行下载。\n")
        else:
            if self.download_queue:
                first_url = self.download_queue[0][0]
                hostname = urlparse(first_url).hostname
                if self.hosts_manager.apply_ip(hostname, ip):
                    QtWidgets.QMessageBox.information(self, f"成功 - {APP_NAME}", f"\n已将优选IP ({ip}) 应用到hosts文件。\n")
                else:
                    QtWidgets.QMessageBox.critical(self, f"错误 - {APP_NAME}", "\n修改hosts文件失败，请检查程序是否以管理员权限运行。\n")
        
        self.setEnabled(True)
        self.next_download_task()

    def start_download_with_ip(self, preferred_ip, url, _7z_path, game_version, game_folder, plugin_path):
        if preferred_ip:
            print(f"已为 {game_version} 获取到优选IP: {preferred_ip}")
        else:
            print(f"未能为 {game_version} 获取优选IP，将使用默认线路。")

        self.current_download_thread = DownloadThread(url, _7z_path, game_version, self)
        self.current_download_thread.progress.connect(self.progress_window.update_progress)
        self.current_download_thread.finished.connect(
            lambda success, error: self.install_setting(
                success,
                error,
                self.progress_window,
                url,
                game_folder,
                game_version,
                _7z_path,
                plugin_path,
            )
        )
        
        self.progress_window.stop_button.clicked.connect(self.current_download_thread.stop)
        self.current_download_thread.start()
        self.progress_window.exec()

    def install_setting(
        self,
        success,
        error,
        progress_window,
        url,
        game_folder,
        game_version,
        _7z_path,
        plugin_path,
    ):
        if progress_window.isVisible():
            progress_window.reject()

        if not success:
            print(f"--- Download Failed: {game_version} ---")
            print(error)
            print("------------------------------------")
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle(f"下载失败 - {APP_NAME}")
            msg_box.setText(f"\n文件获取失败: {game_version}\n错误: {error}\n\n是否重试？")
            
            retry_button = msg_box.addButton("重试", QtWidgets.QMessageBox.ButtonRole.YesRole)
            next_button = msg_box.addButton("下一个", QtWidgets.QMessageBox.ButtonRole.NoRole)
            end_button = msg_box.addButton("结束", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            clicked_button = msg_box.clickedButton()

            if clicked_button == retry_button:
                self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)
            elif clicked_button == next_button:
                self.next_download_task()
            else:
                self.on_download_stopped()
            return

        # --- Start Extraction in a new thread ---
        self.hash_msg_box = self.hash_manager.hash_pop_window()
        self.setEnabled(False)
        
        self.extraction_thread = ExtractionThread(_7z_path, game_folder, plugin_path, game_version, self)
        self.extraction_thread.finished.connect(self.on_extraction_finished)
        self.extraction_thread.start()

    def on_extraction_finished(self, success, error_message, game_version):
        if self.hash_msg_box and self.hash_msg_box.isVisible():
            self.hash_msg_box.close()
        self.setEnabled(True)

        if not success:
            QtWidgets.QMessageBox.critical(self, f"错误 - {APP_NAME}", error_message)
            self.installed_status[game_version] = False
        else:
            self.installed_status[game_version] = True
        
        self.next_download_task()

    def download_action(self):
        # 询问用户是否使用Cloudflare加速
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"下载优化 - {APP_NAME}")
        msg_box.setText("\n是否愿意通过Cloudflare加速来优化下载速度？\n\n这将临时修改系统的hosts文件，并需要管理员权限。")
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        yes_button = msg_box.addButton("是，开启加速", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("否，直接下载", QMessageBox.ButtonRole.NoRole)
        
        msg_box.exec()

        use_optimization = msg_box.clickedButton() == yes_button

        self.hash_msg_box = self.hash_manager.hash_pop_window()
        self.setEnabled(False)

        install_paths = self.get_install_paths()
        
        self.hash_thread = HashThread("pre", install_paths, PLUGIN_HASH, self.installed_status, self)
        # 将用户选择传递给哈希完成后的处理函数
        self.hash_thread.pre_finished.connect(lambda status: self.on_pre_hash_finished(status, use_optimization))
        self.hash_thread.start()

    def on_pre_hash_finished(self, updated_status, use_optimization):
        self.installed_status = updated_status
        if self.hash_msg_box and self.hash_msg_box.isVisible():
            self.hash_msg_box.accept()
            self.hash_msg_box = None

        config = self.get_download_url()
        if not config:
            QtWidgets.QMessageBox.critical(
                self, f"错误 - {APP_NAME}", "\n网络状态异常或服务器故障，请重试\n"
            )
            self.setEnabled(True)
            return

        # --- 填充下载队列 ---
        for i in range(1, 5):
            game_version = f"NEKOPARA Vol.{i}"
            if not self.installed_status.get(game_version, False):
                url = config.get(f"vol{i}")
                if not url: continue
                game_folder = os.path.join(self.selected_folder, f"NEKOPARA Vol. {i}")
                _7z_path = os.path.join(PLUGIN, f"vol.{i}.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))

        game_version = "NEKOPARA After"
        if not self.installed_status.get(game_version, False):
            url = config.get("after")
            if url:
                game_folder = os.path.join(self.selected_folder, "NEKOPARA After")
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
                self.download_queue.append((url, game_folder, game_version, _7z_path, plugin_path))

        if not self.download_queue:
            self.after_hash_compare(PLUGIN_HASH)
            return

        if use_optimization and not self.optimization_done:
            first_url = self.download_queue[0][0]
            self.optimizing_msg_box = msgbox_frame(
                f"通知 - {APP_NAME}",
                "\n正在优选Cloudflare IP，请稍候...\n\n这可能需要5-10分钟，请耐心等待喵~"
            )
            # 我们不再提供“跳过”按钮，因为用户已经做出了选择
            self.optimizing_msg_box.setStandardButtons(QMessageBox.StandardButton.NoButton)
            self.optimizing_msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.optimizing_msg_box.open()

            self.ip_optimizer_thread = IpOptimizerThread(first_url)
            # 优选完成后，需要修改hosts并开始下载
            self.ip_optimizer_thread.finished.connect(self.on_optimization_and_hosts_finished)
            self.ip_optimizer_thread.start()
        else:
            # 如果用户选择不优化，或已经优化过，直接开始下载
            self.setEnabled(True)
            self.next_download_task()

    def next_download_task(self):
        if not self.download_queue:
            self.after_hash_compare(PLUGIN_HASH)
            return
        # 检查下载线程是否仍在运行，以避免在手动停止后立即开始下一个任务
        if self.current_download_thread and self.current_download_thread.isRunning():
            return
        
        # 在开始下载前，确保hosts文件已修改（如果需要）
        # 这里的逻辑保持不变，因为hosts文件应该在队列开始前就被修改了
        url, game_folder, game_version, _7z_path, plugin_path = self.download_queue.popleft()
        self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)

    def on_download_stopped(self):
        """当用户点击停止按钮或选择结束时调用的槽函数"""
        # 停止IP优选线程
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
        if hasattr(self, 'progress_window') and self.progress_window.isVisible():
            self.progress_window.reject()

        # 可以在这里决定是否立即进行哈希比较或显示结果
        print("下载已全部停止。")
        self.setEnabled(True) # 恢复主窗口交互
        self.show_result()

    def after_hash_compare(self, plugin_hash):
        self.hash_msg_box = self.hash_manager.hash_pop_window()
        self.setEnabled(False)

        install_paths = self.get_install_paths()
        
        self.hash_thread = HashThread("after", install_paths, plugin_hash, self.installed_status, self)
        self.hash_thread.after_finished.connect(self.on_after_hash_finished)
        self.hash_thread.start()

    def on_after_hash_finished(self, result):
        if self.hash_msg_box and self.hash_msg_box.isVisible():
            self.hash_msg_box.close()
        self.setEnabled(True)

        if not result["passed"]:
            game = result.get("game", "未知游戏")
            message = result.get("message", "发生未知错误。")
            msg_box = msgbox_frame(
                f"文件校验失败 - {APP_NAME}",
                message,
                QtWidgets.QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()

        self.show_result()

    def show_result(self):
        installed_version = "\n".join(
            [i for i in self.installed_status if self.installed_status[i]]
        )
        failed_ver = "\n".join(
            [i for i in self.installed_status if not self.installed_status[i]]
        )
        QtWidgets.QMessageBox.information(
            self,
            f"完成 - {APP_NAME}",
            f"\n安装结果：\n安装成功数：{len(installed_version.splitlines())}      安装失败数：{len(failed_ver.splitlines())}\n"
            f"安装成功的版本：\n{installed_version}\n尚未持有或未使用本工具安装补丁的版本：\n{failed_ver}\n",
        )

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
            <p><b>{APP_NAME} v{APP_VERSION}</b></p>
            <p>原作: <a href="https://github.com/Yanam1Anna">Yanam1Anna</a></p>
            <p>此应用根据 <a href="https://github.com/hyb-oyqq/FRAISEMOE2-Installer/blob/master/LICENSE">GPL-3.0 许可证</a> 授权。</p>
        """
        msg_box = msgbox_frame(
            f"关于 - {APP_NAME}",
            about_text,
            QtWidgets.QMessageBox.StandardButton.Ok,
        )
        msg_box.setTextFormat(Qt.TextFormat.RichText)  # 启用富文本
        msg_box.exec()

    def open_project_home_page(self):
        """打开项目主页"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT")

    def closeEvent(self, event):
        self.shutdown_app(event)

    def shutdown_app(self, event=None):
        self.hosts_manager.restore() # 恢复hosts文件
        self.stop_logging()  # 确保在退出时停止日志记录
        reply = QtWidgets.QMessageBox.question(
            self,
            "退出程序",
            "\n是否确定退出?\n",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            if (
                self.current_download_thread
                and self.current_download_thread.isRunning()
            ):
                QtWidgets.QMessageBox.critical(
                    self,
                    f"错误 - {APP_NAME}",
                    "\n当前有下载任务正在进行，完成后再试\n",
                )
                if event:
                    event.ignore()
                return

            if os.path.exists(PLUGIN):
                for attempt in range(3):
                    try:
                        shutil.rmtree(PLUGIN)
                        break
                    except Exception as e:
                        if attempt == 2:
                            QtWidgets.QMessageBox.critical(
                                self,
                                f"错误 - {APP_NAME}",
                                f"\n清理缓存失败\n\n【错误信息】：{e}\n",
                            )
                            if event:
                                event.accept()
                            sys.exit(1)
            if event:
                event.accept()
            else:
                sys.exit(0)
        else:
            if event:
                event.ignore()