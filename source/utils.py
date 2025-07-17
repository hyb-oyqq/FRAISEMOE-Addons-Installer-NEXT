import os
import sys
import base64
import hashlib
import concurrent.futures
import ctypes
import json
import psutil
from PySide6 import QtCore, QtWidgets
import re
from PySide6.QtGui import QIcon, QPixmap
from pic_data import img_data
from config import APP_NAME, CONFIG_FILE

def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包环境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller创建的临时文件夹，并将路径存储在_MEIPASS中
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # 在开发环境中运行
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
            msg_box.setIconPixmap(pixmap.scaled(64, 64, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
    else:
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        
    msg_box.setText(text)
    msg_box.setStandardButtons(buttons)
    return msg_box

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        print(f"Error saving config: {e}")


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
                    results[file_path] = None # Mark as failed
                    print(f"Error calculating hash for {file_path}: {e}")
        return results

    def hash_pop_window(self):
        msg_box = msgbox_frame(f"通知 - {APP_NAME}", "\n正在检验文件状态...\n")
        msg_box.open()
        QtWidgets.QApplication.processEvents()
        return msg_box

    def cfg_pre_hash_compare(self, install_paths, plugin_hash, installed_status):
        status_copy = installed_status.copy()
        
        for game_version, install_path in install_paths.items():
            if not os.path.exists(install_path):
                status_copy[game_version] = False
                continue

            try:
                file_hash = self.hash_calculate(install_path)
                if file_hash == plugin_hash.get(game_version):
                    status_copy[game_version] = True
                else:
                    status_copy[game_version] = False
            except Exception:
                status_copy[game_version] = False
        
        return status_copy

    def cfg_after_hash_compare(self, install_paths, plugin_hash, installed_status):
        file_paths = [
            install_paths[game] for game in plugin_hash if installed_status.get(game)
        ]
        hash_results = self.calculate_hashes_in_parallel(file_paths)

        for game, hash_value in plugin_hash.items():
            if installed_status.get(game):
                file_path = install_paths[game]
                file_hash = hash_results.get(file_path)
                
                if file_hash is None:
                    installed_status[game] = False
                    return {
                        "passed": False,
                        "game": game,
                        "message": f"\n无法计算 {game} 的文件哈希值，文件可能已损坏或被占用。\n"
                    }

                if file_hash != hash_value:
                    installed_status[game] = False
                    return {
                        "passed": False,
                        "game": game,
                        "message": f"\n检测到 {game} 的文件哈希值不匹配。\n"
                    }
        return {"passed": True}

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

class HostsManager:
    def __init__(self):
        self.hosts_path = os.path.join(os.environ['SystemRoot'], 'System32', 'drivers', 'etc', 'hosts')
        self.backup_path = os.path.join(os.path.dirname(self.hosts_path), f'hosts.bak.{APP_NAME}')
        self.original_content = None
        self.modified = False

    def backup(self):
        if not AdminPrivileges().is_admin():
            print("需要管理员权限来备份hosts文件。")
            return False
        try:
            with open(self.hosts_path, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                f.write(self.original_content)
            print(f"Hosts文件已备份到: {self.backup_path}")
            return True
        except IOError as e:
            print(f"备份hosts文件失败: {e}")
            msg_box = msgbox_frame(f"错误 - {APP_NAME}", f"\n无法备份hosts文件，请检查权限。\n\n【错误信息】：{e}\n", QtWidgets.QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return False

    def apply_ip(self, hostname, ip_address):
        if not self.original_content:
            if not self.backup():
                return False
        
        if not self.original_content: # 再次检查，确保backup成功
            print("无法读取hosts文件内容，操作中止。")
            return False

        if not AdminPrivileges().is_admin():
            print("需要管理员权限来修改hosts文件。")
            return False
        
        try:
            lines = self.original_content.splitlines()
            new_lines = [line for line in lines if not (hostname in line and line.strip().startswith(ip_address))]
            
            new_entry = f"{ip_address}\t{hostname}"
            new_lines.append(f"\n# Added by {APP_NAME}")
            new_lines.append(new_entry)
            
            with open(self.hosts_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            self.modified = True
            print(f"Hosts文件已更新: {new_entry}")
            return True
        except IOError as e:
            print(f"修改hosts文件失败: {e}")
            msg_box = msgbox_frame(f"错误 - {APP_NAME}", f"\n无法修改hosts文件，请检查权限。\n\n【错误信息】：{e}\n", QtWidgets.QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return False

    def restore(self):
        if not self.modified:
            if os.path.exists(self.backup_path):
                try:
                    os.remove(self.backup_path)
                except OSError:
                    pass
            return True

        if not AdminPrivileges().is_admin():
            print("需要管理员权限来恢复hosts文件。")
            return False
            
        if self.original_content:
            try:
                with open(self.hosts_path, 'w', encoding='utf-8') as f:
                    f.write(self.original_content)
                self.modified = False
                print("Hosts文件已从内存恢复。")
                if os.path.exists(self.backup_path):
                    try:
                        os.remove(self.backup_path)
                    except OSError:
                        pass
                return True
            except IOError as e:
                print(f"从内存恢复hosts文件失败: {e}")
                return self.restore_from_backup_file()
        else:
            return self.restore_from_backup_file()

    def restore_from_backup_file(self):
        if not os.path.exists(self.backup_path):
            print("未找到hosts备份文件，无法恢复。")
            return False
        try:
            with open(self.backup_path, 'r', encoding='utf-8') as bf:
                backup_content = bf.read()
            with open(self.hosts_path, 'w', encoding='utf-8') as hf:
                hf.write(backup_content)
            os.remove(self.backup_path)
            self.modified = False
            print("Hosts文件已从备份文件恢复。")
            return True
        except (IOError, OSError) as e:
            print(f"从备份文件恢复hosts失败: {e}")
            msg_box = msgbox_frame(f"警告 - {APP_NAME}", f"\n自动恢复hosts文件失败，请手动从 {self.backup_path} 恢复。\n\n【错误信息】：{e}\n", QtWidgets.QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return False

def censor_url(text):
    """Censors URLs in a given text string."""
    if not isinstance(text, str):
        text = str(text)
    url_pattern = re.compile(r'https?://[^\s/$.?#].[^\s]*')
    return url_pattern.sub('***URL HIDDEN***', text)