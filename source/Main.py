import os
import py7zr
import requests
import shutil
import hashlib
import sys
import base64
import psutil
import ctypes
import concurrent.futures
import webbrowser
from PySide6.QtGui import QIcon, QAction
from collections import deque
from pic_data import img_data

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (Qt, Signal, QThread, QTimer)
from PySide6.QtGui import (QIcon, QPixmap, )
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow,
    QProgressBar, QVBoxLayout, QFileDialog, QDialog)

from Ui_install import Ui_MainWindows
from animations import MultiStageAnimations
import sys
import os

def load_base64_image(base64_str):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(base64_str))
    return pixmap

# 配置信息
app_data = {
    "APP_VERSION": "4.10.0.17496",
    "APP_NAME": "@FRAISEMOE2 Addons Installer",
    "TEMP": "TEMP",
    "CACHE": "FRAISEMOE",
    "PLUGIN": "PLUGIN",
    "CONFIG_URL": "aHR0cHM6Ly9hcmNoaXZlLm92b2Zpc2guY29tL2FwaS93aWRnZXQvbmVrb3BhcmEvZG93bmxvYWRfdXJsLmpzb24=",
    "UA": "TW96aWxsYS81LjAgKExpbnV4IGRlYmlhbjEyIEZyYWlzZU1vZS1BY2NlcHQpIEdlY2tvLzIwMTAwMTAxIEZpcmVmb3gvMTE0LjA=",
    "game_info": {
        "NEKOPARA Vol.1": {
            "exe": "nekopara_vol1.exe",
            "hash": "04b48b231a7f34431431e5027fcc7b27affaa951b8169c541709156acf754f3e",
            "install_path": "NEKOPARA Vol. 1/adultsonly.xp3",
            "plugin_path": "vol.1/adultsonly.xp3",
        },
        "NEKOPARA Vol.2": {
            "exe": "nekopara_vol2.exe",
            "hash": "b9c00a2b113a1e768bf78400e4f9075ceb7b35349cdeca09be62eb014f0d4b42",
            "install_path": "NEKOPARA Vol. 2/adultsonly.xp3",
            "plugin_path": "vol.2/adultsonly.xp3",
        },
        "NEKOPARA Vol.3": {
            "exe": "NEKOPARAvol3.exe",
            "hash": "2ce7b223c84592e1ebc3b72079dee1e5e8d064ade15723328a64dee58833b9d5",
            "install_path": "NEKOPARA Vol. 3/update00.int",
            "plugin_path": "vol.3/update00.int",
        },
        "NEKOPARA Vol.4": {
            "exe": "nekopara_vol4.exe",
            "hash": "4a4a9ae5a75a18aacbe3ab0774d7f93f99c046afe3a777ee0363e8932b90f36a",
            "install_path": "NEKOPARA Vol. 4/vol4adult.xp3",
            "plugin_path": "vol.4/vol4adult.xp3",
        },
        "NEKOPARA After": {
            "exe": "nekopara_after.exe",
            "hash": "eb26ff6850096a240af8340ba21c5c3232e90f29fb8191e24b6ce701acae0aa9",
            "install_path": "NEKOPARA After/afteradult.xp3",
            "plugin_path": "after/afteradult.xp3",
            "sig_path": "after/afteradult.xp3.sig"
        },
    },
}

# Base64解码
def decode_base64(encoded_str):
    return base64.b64decode(encoded_str).decode("utf-8")

# 全局变量
APP_VERSION = app_data["APP_VERSION"]
APP_NAME = app_data["APP_NAME"]
TEMP = os.getenv(app_data["TEMP"]) or app_data["TEMP"]
CACHE = os.path.join(TEMP, app_data["CACHE"])
PLUGIN = os.path.join(CACHE, app_data["PLUGIN"])
CONFIG_URL = decode_base64(app_data["CONFIG_URL"])
UA = decode_base64(app_data["UA"]) + f" FraiseMoe/{APP_VERSION}"
GAME_INFO = app_data["game_info"]
BLOCK_SIZE = 67108864
HASH_SIZE = 134217728
PLUGIN_HASH = {game: info["hash"] for game, info in GAME_INFO.items()}
PROCESS_INFO = {info["exe"]: game for game, info in GAME_INFO.items()}

def msgbox_frame(title, text, buttons=QtWidgets.QMessageBox.StandardButton.NoButton):
    msg_box = QtWidgets.QMessageBox()
    msg_box.setWindowTitle(title)
    
    # 设置弹窗图标
    icon_data = img_data.get("icon")
    if icon_data:
        pixmap = load_base64_image(icon_data)
        if not pixmap.isNull():
            msg_box.setWindowIcon(QIcon(pixmap))
            msg_box.setIconPixmap(pixmap.scaled(64, 64, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
    else:
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        
    msg_box.setText(text)
    msg_box.setStandardButtons(buttons)
    return msg_box

# 哈希值计算类
class HashManager:
    def __init__(self, HASH_SIZE):
        self.HASH_SIZE = HASH_SIZE

    def hash_calculate(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(self.HASH_SIZE), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def calculate_hashes_in_parallel(self, file_paths):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_file = {
                executor.submit(self.hash_calculate, path): path for path in file_paths
            }
            results = {}
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    results[file_path] = future.result()
                except Exception as e:
                    results[file_path] = None
                    msg_box = msgbox_frame(
                        f"错误 {APP_NAME}",
                        f"\n文件哈希值计算失败\n\n【错误信息】：{e}\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
        return results

    def hash_pop_window(self):
        msg_box = msgbox_frame(f"通知 {APP_NAME}", "\n正在检验文件状态...\n")
        msg_box.show()
        QApplication.processEvents()
        return msg_box

    def cfg_pre_hash_compare(self, install_path, game_version, plugin_hash, installed_status):
        if not os.path.exists(install_path):
            installed_status[game_version] = False
            return
        file_hash = self.hash_calculate(install_path)
        if file_hash == plugin_hash[game_version]:
            installed_status[game_version] = True
        else:
            reply = msgbox_frame(
                f"文件校验 {APP_NAME}",
                f"\n检测到 {game_version} 的文件哈希值不匹配，是否重新安装？\n",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            ).exec()
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                installed_status[game_version] = False
            else:
                installed_status[game_version] = True

    def cfg_after_hash_compare(self, install_paths, plugin_hash, installed_status):
        passed = True
        file_paths = [
            install_paths[game] for game in plugin_hash if installed_status.get(game)
        ]
        hash_results = self.calculate_hashes_in_parallel(file_paths)

        for game, hash_value in plugin_hash.items():
            if installed_status.get(game):
                file_hash = hash_results.get(install_paths[game])
                if file_hash != hash_value:
                    msg_box = msgbox_frame(
                        f"文件校验 {APP_NAME}",
                        f"\n检测到 {game} 的文件哈希值不匹配\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                    installed_status[game] = False
                    passed = False
                    break
        return passed

# 管理员权限检查类
class AdminPrivileges:
    def __init__(self):
        self.required_exes = [
            "nekopara_vol1.exe",
            "nekopara_vol2.exe",
            "NEKOPARAvol3.exe",
            "nekopara_vol4.exe",
            "nekopara_after.exe",
        ]

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def request_admin_privileges(self):
        if not self.is_admin():
            msg_box = msgbox_frame(
                f"权限检测 {APP_NAME}",
                "\n需要管理员权限运行此程序\n",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            )
            reply = msg_box.exec()
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                try:
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, " ".join(sys.argv), None, 1
                    )
                except Exception as e:
                    msg_box = msgbox_frame(
                        f"错误 {APP_NAME}",
                        f"\n请求管理员权限失败\n\n【错误信息】：{e}\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                sys.exit(1)
            else:
                msg_box = msgbox_frame(
                    f"权限检测 {APP_NAME}",
                    "\n无法获取管理员权限，程序将退出\n",
                    QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                msg_box.exec()
                sys.exit(1)

    def check_and_terminate_processes(self):
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.info["name"] in self.required_exes:
                msg_box = msgbox_frame(
                    f"进程检测 {APP_NAME}",
                    f"\n检测到游戏正在运行： {proc.info['name']} \n\n是否终止？\n",
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                )
                reply = msg_box.exec()
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                    except psutil.AccessDenied:
                        msg_box = msgbox_frame(
                            f"错误 {APP_NAME}",
                            f"\n无法关闭游戏： {proc.info['name']} \n\n请手动关闭后重启应用\n",
                            QtWidgets.QMessageBox.StandardButton.Ok,
                        )
                        msg_box.exec()
                        sys.exit(1)
                else:
                    msg_box = msgbox_frame(
                        f"进程检测 {APP_NAME}",
                        f"\n未关闭的游戏： {proc.info['name']} \n\n请手动关闭后重启应用\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                    sys.exit(1)

# 下载线程类
class DownloadThread(QThread):
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, url, _7z_path, parent=None):
        super().__init__(parent)
        self.url = url
        self._7z_path = _7z_path

    def run(self):
        try:
            headers = {"User-Agent": UA}
            r = requests.get(self.url, headers=headers, stream=True, timeout=10)
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            with open(self._7z_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=BLOCK_SIZE):
                    f.write(chunk)
                    self.progress.emit(f.tell() * 100 // total_size)
            self.finished.emit(True, "")
        except requests.exceptions.RequestException as e:
            self.finished.emit(False, f"\n网络请求错误\n\n【错误信息】: {e}\n")
        except Exception as e:
            self.finished.emit(False, f"\n未知错误\n\n【错误信息】: {e}\n")

# 下载进度窗口类
class ProgressWindow(QDialog):
    def __init__(self, parent=None):
        super(ProgressWindow, self).__init__(parent)
        self.setWindowTitle(f"下载进度 {APP_NAME}")
        self.resize(400, 100)
        self.progress_bar_max = 100
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowSystemMenuHint)

        layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.label = QLabel("\n正在下载...\n")
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def setmaxvalue(self, value):
        self.progress_bar_max = value
        self.progress_bar.setMaximum(value)

    def setprogressbarval(self, value):
        self.progress_bar.setValue(value)
        if value == self.progress_bar_max:
            QTimer.singleShot(2000, self.close)

# 主窗口类
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
                    f"错误 {APP_NAME}",
                    f"\n无法创建缓存位置\n\n使用管理员身份运行或检查文件读写权限\n\n【错误信息】：{e}\n",
                )
                sys.exit(1)
        
        # 连接信号 (使用Ui_install.py中的组件名称)
        self.ui.start_install_btn.clicked.connect(self.file_dialog)
        self.ui.exit_btn.clicked.connect(self.shutdown_app)

        # “关于”菜单
        about_action = QAction("项目主页", self)
        about_action.triggered.connect(self.open_about_page)
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
                self, f"通知 {APP_NAME}", "\n未选择任何目录,请重新选择\n"
            )
            return
        self.download_action()

    def get_download_url(self) -> dict:
        try:
            headers = {"User-Agent": UA}
            response = requests.get(CONFIG_URL, headers=headers, timeout=10)
            response.raise_for_status()
            config_data = response.json()
            if not all(f"vol.{i+1}.data" in config_data for i in range(4)) or "after.data" not in config_data:
                raise ValueError("配置文件数据异常")
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

            QtWidgets.QMessageBox.critical(
                self,
                f"错误 {APP_NAME}",
                f"\n下载配置获取失败\n\n【HTTP状态】：{status_code}\n【错误类型】：{json_title}\n【错误信息】：{json_message}\n",
            )
            return {}
        except ValueError as e:
            QtWidgets.QMessageBox.critical(
                self,
                f"错误 {APP_NAME}",
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
            
        progress_window = ProgressWindow(self)
        progress_window.show()
        
        self.current_download_thread = DownloadThread(url, _7z_path, self)
        self.current_download_thread.progress.connect(progress_window.setprogressbarval)
        self.current_download_thread.finished.connect(
            lambda success, error: self.install_setting(
                success,
                error,
                progress_window,
                game_folder,
                game_version,
                _7z_path,
                plugin_path,
            )
        )
        self.current_download_thread.start()

    def install_setting(
        self,
        success,
        error,
        progress_window,
        game_folder,
        game_version,
        _7z_path,
        plugin_path,
    ):
        progress_window.close()
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
                QtWidgets.QMessageBox.information(
                    self, f"通知 {APP_NAME}", f"\n{game_version} 补丁已安装\n"
                )
            except (py7zr.Bad7zFile, FileNotFoundError, Exception) as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    f"错误 {APP_NAME}",
                    f"\n文件操作失败，请重试\n\n【错误信息】：{e}\n",
                )
            finally:
                msg_box.close()
        else:
            QtWidgets.QMessageBox.critical(
                self,
                f"错误 {APP_NAME}",
                f"\n文件获取失败\n网络状态异常或服务器故障\n\n【错误信息】：{error}\n",
            )
        self.next_download_task()

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
                self, f"错误 {APP_NAME}", "\n网络状态异常或服务器故障，请重试\n"
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
        url, game_folder, game_version, _7z_path, plugin_path = self.download_queue.popleft()
        self.download_setting(url, game_folder, game_version, _7z_path, plugin_path)

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
            f"完成 {APP_NAME}",
            f"\n安装结果：\n安装成功数：{len(installed_version.splitlines())}      安装失败数：{len(failed_ver.splitlines())}\n"
            f"安装成功的版本：\n{installed_version}\n尚未持有或未使用本工具安装补丁的版本：\n{failed_ver}\n",
        )

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
                    f"错误 {APP_NAME}",
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
                                f"错误 {APP_NAME}",
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

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())