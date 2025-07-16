import os
import sys
import base64
import hashlib
import concurrent.futures
import ctypes
import psutil
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QIcon, QPixmap
from pic_data import img_data
from config import APP_NAME

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS  # type: ignore
        else:
            base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def load_base64_image(base64_str):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(base64_str))
    return pixmap

def msgbox_frame(title, text, buttons=QtWidgets.QMessageBox.StandardButton.NoButton):
    msg_box = QtWidgets.QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
    
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
                        f"错误 - {APP_NAME}",
                        f"\n文件哈希值计算失败\n\n【错误信息】：{e}\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
        return results

    def hash_pop_window(self):
        msg_box = msgbox_frame(f"通知 - {APP_NAME}", "\n正在检验文件状态...\n")
        msg_box.open()
        QtWidgets.QApplication.processEvents()
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
                f"文件校验 - {APP_NAME}",
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
                        f"文件校验 - {APP_NAME}",
                        f"\n检测到 {game} 的文件哈希值不匹配\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                    installed_status[game] = False
                    passed = False
                    break
        return passed

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
                f"权限检测 - {APP_NAME}",
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
                        f"错误 - {APP_NAME}",
                        f"\n请求管理员权限失败\n\n【错误信息】：{e}\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                sys.exit(1)
            else:
                msg_box = msgbox_frame(
                    f"权限检测 - {APP_NAME}",
                    "\n无法获取管理员权限，程序将退出\n",
                    QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                msg_box.exec()
                sys.exit(1)

    def check_and_terminate_processes(self):
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.info["name"] in self.required_exes:
                msg_box = msgbox_frame(
                    f"进程检测 - {APP_NAME}",
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
                            f"错误 - {APP_NAME}",
                            f"\n无法关闭游戏： {proc.info['name']} \n\n请手动关闭后重启应用\n",
                            QtWidgets.QMessageBox.StandardButton.Ok,
                        )
                        msg_box.exec()
                        sys.exit(1)
                else:
                    msg_box = msgbox_frame(
                        f"进程检测 - {APP_NAME}",
                        f"\n未关闭的游戏： {proc.info['name']} \n\n请手动关闭后重启应用\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                    sys.exit(1)