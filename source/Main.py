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

def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包环境"""
    try:
        # PyInstaller创建的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def load_base64_image(base64_str):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(base64_str))
    return pixmap

# 配置信息
app_data = {
    "APP_VERSION": "1.0.0",
    "APP_NAME": "FRAISEMOE Addons Installer NEXT",
    "TEMP": "TEMP",
    "CACHE": "FRAISEMOE",
    "PLUGIN": "PLUGIN",
    "CONFIG_URL": "aHR0cHM6Ly9hcmNoaXZlLm92b2Zpc2guY29tL2FwaS93aWRnZXQvbmVrb3BhcmEvZG93bmxvYWRfdXJsX2RlYnVnLmpzb24=",
    "UA": "TW96aWxsYS81LjAgKExpbnV4IGRlYmlhbjEyIEZyYWlzZU1vZTItQWNjZXB0KSBHZWNrby8yMDEwMDEwMSBGaXJlZm94LzExNC4wIEZyYWlzZU1vZTIvMS4wLjA=",
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
UA = decode_base64(app_data["UA"])
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
    progress = Signal(dict)
    finished = Signal(bool, str)

    def __init__(self, url, _7z_path, game_version, parent=None):
        super().__init__(parent)
        self.url = url
        self._7z_path = _7z_path
        self.game_version = game_version
        self.process = None
        self.is_running = True

    def stop(self):
        if self.process and self.process.poll() is None:
            self.is_running = False
            # 使用 taskkill 强制终止进程及其子进程
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], check=True)
            self.finished.emit(False, "下载已手动停止。")

    def run(self):
        import subprocess
        import re
        from urllib.parse import urlparse
        
        try:
            aria2c_path = resource_path("aria2c.exe")
            download_dir = os.path.dirname(self._7z_path)
            file_name = os.path.basename(self._7z_path)
            
            parsed_url = urlparse(self.url)
            referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            
            command = [
                aria2c_path,
                '--dir', download_dir,
                '--out', file_name,
                '--user-agent', UA,
                '--referer', referer,
                '--header', f'Origin: {referer.rstrip("/")}',
                '--header', 'Accept: */*',
                '--header', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
                '--header', 'Accept-Encoding: gzip, deflate, br',
                '--header', 'Cache-Control: no-cache',
                '--header', 'Pragma: no-cache',
                '--header', 'DNT: 1',
                '--header', 'Sec-Fetch-Dest: empty',
                '--header', 'Sec-Fetch-Mode: cors',
                '--header', 'Sec-Fetch-Site: same-origin',
                '--http-accept-gzip=true',
                '--min-tls-version=TLSv1.2',
                '--console-log-level=info',
                '--summary-interval=1',
                '--log-level=info',
                '--allow-overwrite=true',
                '--max-tries=3',
                '--retry-wait=2',
                '--connect-timeout=60',
                '--timeout=60',
                '--auto-file-renaming=false',
                self.url
            ]
            
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=creation_flags)

            # 正则表达式用于解析aria2c的输出
            # 例如: #1 GID[...](  5%) CN:1 DL:10.5MiB/s ETA:1m30s
            progress_pattern = re.compile(r'\((\d+)%\).*?CN:(\d+).*?DL:([\d\.]+[KMG]?i?B/s).*?ETA:([\w\d]+)')

            full_output = []
            while self.is_running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                full_output.append(line)
                print(line.strip()) # 在控制台输出实时日志

                match = progress_pattern.search(line)
                if match:
                    percent = int(match.group(1))
                    threads = match.group(2)
                    speed = match.group(3)
                    eta = match.group(4)
                    self.progress.emit({
                        "game": self.game_version,
                        "percent": percent,
                        "threads": threads,
                        "speed": speed,
                        "eta": eta
                    })

            return_code = self.process.wait()
            
            if not self.is_running: # 如果是手动停止的
                return

            if return_code == 0:
                self.progress.emit({
                    "game": self.game_version,
                    "percent": 100,
                    "threads": "N/A",
                    "speed": "N/A",
                    "eta": "完成"
                })
                self.finished.emit(True, "")
            else:
                error_message = f"\nAria2c下载失败，退出码: {return_code}\n\n--- Aria2c 输出 ---\n{''.join(full_output)}\n---------------------\n"
                self.finished.emit(False, error_message)

        except Exception as e:
            if self.is_running:
                self.finished.emit(False, f"\n下载时发生未知错误\n\n【错误信息】: {e}\n")

# 下载进度窗口类
class ProgressWindow(QDialog):
    # 添加一个信号，用于通知主窗口下载已停止
    download_stopped = Signal()

    def __init__(self, parent=None):
        super(ProgressWindow, self).__init__(parent)
        self.setWindowTitle(f"下载进度 {APP_NAME}")
        self.resize(450, 180)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowSystemMenuHint)

        layout = QVBoxLayout()
        self.game_label = QLabel("正在准备下载...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.stats_label = QLabel("速度: - | 线程: - | 剩余时间: -")
        self.stop_button = QtWidgets.QPushButton("停止下载")

        layout.addWidget(self.game_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.stats_label)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)

    def update_progress(self, data):
        game_version = data.get("game", "未知游戏")
        percent = data.get("percent", 0)
        speed = data.get("speed", "-")
        threads = data.get("threads", "-")
        eta = data.get("eta", "-")

        self.game_label.setText(f"正在下载: {game_version}")
        self.progress_bar.setValue(int(percent))
        self.stats_label.setText(f"速度: {speed} | 线程: {threads} | 剩余时间: {eta}")

        if percent == 100:
            self.stop_button.setEnabled(False)
            self.stop_button.setText("下载完成")
            QTimer.singleShot(1500, self.accept)

    def closeEvent(self, event):
        # 覆盖默认的关闭事件，防止用户通过其他方式关闭窗口
        # 如果需要，可以在这里添加逻辑，例如询问用户是否要停止下载
        event.ignore()

    def on_stop_clicked(self):
        self.stop_button.setEnabled(False)
        self.stop_button.setText("正在停止...")
        self.download_stopped.emit()
        self.reject() # 关闭窗口并返回一个QDialog.Rejected值

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
        self.setWindowTitle(f"{APP_NAME} vFraiseMoe2/1.0.0")
        
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
        # 连接窗口关闭信号，以处理用户手动停止的情况
        self.progress_window.download_stopped.connect(self.on_download_stopped)

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
        if not success and error == "下载已手动停止。":
            # 用户手动停止了下载，不需要进行后续操作
            return

        if self.progress_window.isVisible():
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
                    f"错误 {APP_NAME}",
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