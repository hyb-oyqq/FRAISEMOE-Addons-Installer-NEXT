import os
import sys
import shutil
import webbrowser
import requests
import py7zr
from collections import deque
from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMainWindow, QFileDialog, QApplication

from Ui_install import Ui_MainWindows
from animations import MultiStageAnimations
from config import (
    APP_NAME, APP_VERSION, PLUGIN, GAME_INFO, BLOCK_SIZE, 
    PLUGIN_HASH, UA, CONFIG_URL
)
from utils import (
    load_base64_image, HashManager, AdminPrivileges, msgbox_frame
)
from download import DownloadThread, ProgressWindow
from pic_data import img_data

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
        
        # 检查管理员权限和进程
        admin_privileges = AdminPrivileges()
        admin_privileges.request_admin_privileges()
        admin_privileges.check_and_terminate_processes()
        
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

        # “关于”菜单
        about_action = QAction("项目主页", self)
        about_action.triggered.connect(self.open_about_page)
        version_action = QAction("版本信息", self)
        version_action.triggered.connect(self.show_version_info)
        self.ui.menu_2.addAction(version_action)
        self.ui.menu_2.addAction(about_action)
        
        # 在窗口显示前设置初始状态
        self.animator.initialize()
        
        # 窗口显示后延迟100ms启动动画
        QTimer.singleShot(100, self.start_animations)
    
    def start_animations(self):
        self.animator.start_animations()
        
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
            response = requests.get(CONFIG_URL, headers=headers, timeout=10)
            response.raise_for_status()
            config_data = response.json()
            # 修正键名检查，确保所有必需的键都存在
            required_keys = [f"vol.{i+1}.data" for i in range(4)] + ["after.data"]
            if not all(key in config_data for key in required_keys):
                missing_keys = [key for key in required_keys if key not in config_data]
                raise ValueError(f"配置文件缺少必要的键: {', '.join(missing_keys)}")
            
            # 修正提取URL的逻辑，确保使用正确的键
            return {
                f"vol{i+1}": config_data[f"vol.{i+1}.data"]["url"] for i in range(4)
            } | {
                "after": config_data["after.data"]["url"]
            }
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else "未知"
            try:
                error_response = e.response.json() if e.response else {}
                json_title = error_response.get("title", "无错误类型")
                json_message = error_response.get("message", "无附加错误信息")
            except (ValueError, AttributeError):
                json_title = "配置文件异常，无法解析错误类型"
                json_message = "配置文件异常，无法解析错误信息"

            print(f"获取下载配置时出错: {e}") # 添加详细错误日志
            QtWidgets.QMessageBox.critical(
                self,
                f"错误 - {APP_NAME}",
                f"\n下载配置获取失败\n\n【HTTP状态】：{status_code}\n【错误类型】：{json_title}\n【错误信息】：{json_message}\n",
            )
            return {}
        except ValueError as e:
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
        
        # 连接停止按钮的信号
        self.progress_window.stop_button.clicked.connect(self.current_download_thread.stop)
        self.current_download_thread.start()
        self.progress_window.exec() # 使用exec()以模态方式显示对话框

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

        if not success: # 处理所有失败情况，包括手动停止
            print(f"--- Download Failed: {game_version} ---")
            print(error)
            print("------------------------------------")
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle(f"下载失败 - {APP_NAME}")
            # 如果是手动停止，显示特定信息
            if error == "下载已手动停止。":
                msg_box.setText(f"\n下载已手动终止: {game_version}\n\n是否重试？")
            else:
                msg_box.setText(f"\n文件获取失败: {game_version}\n\n是否重试？")
            
            retry_button = msg_box.addButton("重试", QtWidgets.QMessageBox.ButtonRole.YesRole)
            next_button = msg_box.addButton("下一个", QtWidgets.QMessageBox.ButtonRole.NoRole)
            end_button = msg_box.addButton("结束", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            icon_data = img_data.get("icon")
            if icon_data:
                pixmap = load_base64_image(icon_data)
                if not pixmap.isNull():
                    msg_box.setWindowIcon(QIcon(pixmap))

            msg_box.exec()
            clicked_button = msg_box.clickedButton()

            if clicked_button == retry_button:
                self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)
            elif clicked_button == next_button:
                self.next_download_task()
            else: # End button or closed dialog
                self.download_queue.clear()
                self.after_hash_compare(PLUGIN_HASH)
            return # 确保失败后不再执行成功逻辑

        if success:
            try:
                msg_box = self.hash_manager.hash_pop_window()
                QApplication.processEvents()
                with py7zr.SevenZipFile(_7z_path, mode="r") as archive:
                    archive.extractall(path=PLUGIN)
                
                # 创建游戏目录(如果不存在)
                os.makedirs(game_folder, exist_ok=True)
                
                # 复制主文件
                shutil.copy(plugin_path, game_folder)
                
                # 如果是After版本，还需要复制签名文件
                if game_version == "NEKOPARA After":
                    sig_path = os.path.join(PLUGIN, GAME_INFO[game_version]["sig_path"])
                    shutil.copy(sig_path, game_folder)
                    
                self.installed_status[game_version] = True
            except (py7zr.Bad7zFile, FileNotFoundError, Exception) as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    f"错误 - {APP_NAME}",
                    f"\n文件操作失败，请重试\n\n【错误信息】：{e}\n",
                )
            finally:
                msg_box.close()
            self.next_download_task()
            self.progress_window.close()
            
        if success:
            try:
                msg_box = self.hash_manager.hash_pop_window()
                QApplication.processEvents()
                with py7zr.SevenZipFile(_7z_path, mode="r") as archive:
                    archive.extractall(path=PLUGIN)
                
                # 创建游戏目录(如果不存在)
                os.makedirs(game_folder, exist_ok=True)
                
                # 复制主文件
                shutil.copy(plugin_path, game_folder)
                
                # 如果是After版本，还需要复制签名文件
                if game_version == "NEKOPARA After":
                    sig_path = os.path.join(PLUGIN, GAME_INFO[game_version]["sig_path"])
                    shutil.copy(sig_path, game_folder)
                    
                self.installed_status[game_version] = True
            except (py7zr.Bad7zFile, FileNotFoundError, Exception) as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    f"错误 - {APP_NAME}",
                    f"\n文件操作失败，请重试\n\n【错误信息】：{e}\n",
                )
            finally:
                msg_box.close()
            self.next_download_task()
        else:
            print(f"--- Download Failed: {game_version} ---")
            print(error)
            print("------------------------------------")
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle(f"下载失败 {APP_NAME}")
            msg_box.setText(f"\n文件获取失败: {game_version}\n\n是否重试？")
            
            retry_button = msg_box.addButton("重试", QtWidgets.QMessageBox.ButtonRole.YesRole)
            next_button = msg_box.addButton("下一个", QtWidgets.QMessageBox.ButtonRole.NoRole)
            end_button = msg_box.addButton("结束", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            icon_data = img_data.get("icon")
            if icon_data:
                pixmap = load_base64_image(icon_data)
                if not pixmap.isNull():
                    msg_box.setWindowIcon(QIcon(pixmap))

            msg_box.exec()
            clicked_button = msg_box.clickedButton()

            if clicked_button == retry_button:
                self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)
            elif clicked_button == next_button:
                self.next_download_task()
            else: # End button or closed dialog
                self.download_queue.clear()
                self.after_hash_compare(PLUGIN_HASH)

    def pre_hash_compare(self, install_path, game_version, plugin_hash):
        msg_box = self.hash_manager.hash_pop_window()
        self.hash_manager.cfg_pre_hash_compare(
            install_path, game_version, plugin_hash, self.installed_status
        )
        msg_box.close()

    def download_action(self):
        install_paths = self.get_install_paths()
        for game_version, install_path in install_paths.items():
            self.pre_hash_compare(install_path, game_version, PLUGIN_HASH)

        config = self.get_download_url()
        if not config:
            QtWidgets.QMessageBox.critical(
                self, f"错误 - {APP_NAME}", "\n网络状态异常或服务器故障，请重试\n"
            )
            return

        # 处理1-4卷
        for i in range(1, 5):
            game_version = f"NEKOPARA Vol.{i}"
            if not self.installed_status[game_version]:
                url = config[f"vol{i}"]
                game_folder = os.path.join(self.selected_folder, f"NEKOPARA Vol. {i}")
                _7z_path = os.path.join(PLUGIN, f"vol.{i}.7z")
                plugin_path = os.path.join(
                    PLUGIN, GAME_INFO[game_version]["plugin_path"]
                )
                self.download_queue.append(
                    (url, game_folder, game_version, _7z_path, plugin_path)
                )
        
        # 处理After
        game_version = "NEKOPARA After"
        if not self.installed_status[game_version]:
            url = config["after"]
            game_folder = os.path.join(self.selected_folder, "NEKOPARA After")
            _7z_path = os.path.join(PLUGIN, "after.7z")
            plugin_path = os.path.join(
                PLUGIN, GAME_INFO[game_version]["plugin_path"]
            )
            self.download_queue.append(
                (url, game_folder, game_version, _7z_path, plugin_path)
            )

        self.next_download_task()

    def next_download_task(self):
        if not self.download_queue:
            self.after_hash_compare(PLUGIN_HASH)
            return
        # 检查下载线程是否仍在运行，以避免在手动停止后立即开始下一个任务
        if self.current_download_thread and self.current_download_thread.isRunning():
            return
        url, game_folder, game_version, _7z_path, plugin_path = self.download_queue.popleft()
        self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)

    def on_download_stopped(self):
        """当用户点击停止按钮时调用的槽函数"""
        # 清空下载队列，因为用户决定停止
        self.download_queue.clear()
        # 可以在这里决定是否立即进行哈希比较或显示结果
        self.after_hash_compare(PLUGIN_HASH)

    def after_hash_compare(self, plugin_hash):
        msg_box = self.hash_manager.hash_pop_window()
        result = self.hash_manager.cfg_after_hash_compare(
            self.get_install_paths(), plugin_hash, self.installed_status
        )
        msg_box.close()
        self.show_result()
        return result

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

    def show_version_info(self):
        """显示版本信息对话框"""
        msg_box = msgbox_frame(
            f"版本信息 - {APP_NAME}",
            f"\n{APP_NAME}\n\n版本: {APP_VERSION}\n",
            QtWidgets.QMessageBox.StandardButton.Ok,
        )
        msg_box.exec()

    def open_about_page(self):
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT")

    def closeEvent(self, event):
        self.shutdown_app(event)

    def shutdown_app(self, event=None):
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